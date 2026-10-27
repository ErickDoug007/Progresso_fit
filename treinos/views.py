import json
import logging
from contextlib import contextmanager

import requests
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.cache import cache
from django.views.decorators.http import require_POST

from core.security import estourou_limite, evitar_envio_duplicado, limitar_taxa
from .models import FichaAnamnese, PlanoTreino
from .forms import FichaAnamneseForm, FotoTreinoForm
from .services import gerar_plano_treino

logger = logging.getLogger(__name__)


@login_required
def treino_view(request):
    ultima_ficha = FichaAnamnese.objects.filter(usuario=request.user).first()

    if not ultima_ficha:
        return redirect('treinos:formulario')

    if ultima_ficha.precisa_reavaliacao:
        return render(request, 'treinos/reavaliacao.html', {'ficha': ultima_ficha})

    plano = ultima_ficha.planos.first()
    if not plano:
        # Ficha sem plano (a geração falhou antes): tenta gerar de novo — com limite,
        # porque aqui um simples F5 dispararia chamadas pagas à API de IA.
        if estourou_limite('ia_regerar', request.user.pk, 3, 3600):
            messages.error(request, 'Muitas tentativas de gerar o treino. Aguarde alguns minutos.')
            return render(request, 'treinos/formulario_treino.html', {
                'form': FichaAnamneseForm(instance=ultima_ficha),
            })
        with _trinco_ia(request.user.pk) as obtido:
            if not obtido:
                messages.warning(request, 'Seu treino já está sendo gerado. Aguarde um instante.')
                return render(request, 'treinos/formulario_treino.html', {
                    'form': FichaAnamneseForm(instance=ultima_ficha),
                })
            plano, erro = _gerar_e_salvar_plano(ultima_ficha)
        if plano is None:
            messages.error(request, f'Não foi possível gerar o treino agora: {erro}')
            return render(request, 'treinos/formulario_treino.html', {
                'form': FichaAnamneseForm(instance=ultima_ficha),
            })

    return render(request, 'treinos/treino.html', {'plano': plano, 'ficha': ultima_ficha})


@login_required
@limitar_taxa('ia_formulario', 8, 3600)
@evitar_envio_duplicado('ia_formulario', ttl=150, liberar_ao_fim=True)
def formulario_view(request):
    if request.method == 'POST':
        form = FichaAnamneseForm(request.POST)
        if form.is_valid():
            # Ficha anterior = a última que realmente gerou um plano
            ficha_anterior = (
                FichaAnamnese.objects
                .filter(usuario=request.user, planos__isnull=False)
                .first()
            )

            ficha = form.save(commit=False)
            ficha.usuario = request.user
            ficha.save()

            plano, erro = _gerar_e_salvar_plano(ficha, ficha_anterior)
            if plano is None:
                ficha.delete()  # não deixa ficha órfã no banco
                messages.error(request, f'Não foi possível gerar o treino agora: {erro}')
                # Renderiza (sem redirect) pra manter o que o usuário preencheu
                return render(request, 'treinos/formulario_treino.html', {'form': form})

            return redirect('treinos:treino')
    else:
        form = FichaAnamneseForm()

    return render(request, 'treinos/formulario_treino.html', {'form': form})


@login_required
def continuar_treino_anterior_view(request):
    """Usuário com ficha vencida escolhe continuar com o treino de antes, sem reavaliar."""
    ultima_ficha = FichaAnamnese.objects.filter(usuario=request.user).first()
    plano = ultima_ficha.planos.first() if ultima_ficha else None

    if not plano:
        return redirect('treinos:formulario')

    return render(request, 'treinos/treino.html', {'plano': plano, 'ficha': ultima_ficha, 'vencida': True})


@login_required
@require_POST
@limitar_taxa('foto_treino', 20, 3600, destino='contas:perfil')
@evitar_envio_duplicado('foto_treino', destino='contas:perfil')
def enviar_foto_view(request):
    form = FotoTreinoForm(request.POST, request.FILES)
    if form.is_valid():
        form.instance.usuario = request.user
        form.save()
        messages.success(request, 'Foto adicionada!')
    else:
        messages.error(request, 'Envie uma imagem válida.')
    return redirect('contas:perfil')


@contextmanager
def _trinco_ia(usuario_id):
    """Garante uma geração de treino por vez por usuário (a chamada à IA pode levar dezenas de segundos)."""
    chave = f'seg:trinco:ia_geracao:{usuario_id}'
    obtido = cache.add(chave, 1, timeout=150)
    try:
        yield obtido
    finally:
        if obtido:
            cache.delete(chave)


def _gerar_e_salvar_plano(ficha, ficha_anterior=None):
    """Retorna (plano, None) se der certo, ou (None, mensagem_de_erro) se falhar."""
    try:
        resultado = gerar_plano_treino(ficha, ficha_anterior)
        plano = PlanoTreino.objects.create(
            usuario=ficha.usuario,
            ficha=ficha,
            resumo=resultado.get('resumo', ''),
            conteudo=resultado.get('dias', {}),
            orientacoes=resultado.get('orientacoes', ''),
        )
        return plano, None

    except requests.HTTPError as e:
        status = e.response.status_code if e.response is not None else '?'
        try:
            body = e.response.json() if e.response is not None else {}
        except ValueError:
            body = {}
        api_error = body.get('error', {}) if isinstance(body, dict) else {}
        detail = api_error.get('message') if isinstance(api_error, dict) else None
        # O detalhe técnico (chave, projeto, modelo...) fica só no log do servidor.
        logger.exception(
            'Erro HTTP na API de IA (status %s): %s',
            status,
            detail or 'a API não forneceu detalhes',
        )

        if status == 429:
            return None, 'o limite de uso do serviço de IA foi atingido, tente novamente em instantes'
        if status in (401, 403, 404):
            return None, 'o serviço de IA está indisponível no momento, tente novamente mais tarde'
        return None, 'o serviço de IA não conseguiu responder agora, tente novamente'

    except requests.RequestException:
        logger.exception('Falha de conexão com a API de IA')
        return None, 'falha de conexão com a API (internet ou tempo esgotado)'

    except (json.JSONDecodeError, KeyError, TypeError):
        logger.exception('Resposta da IA fora do formato esperado')
        return None, 'a IA devolveu uma resposta fora do formato esperado, tente novamente'

    except Exception:
        logger.exception('Erro inesperado ao gerar treino')
        return None, 'ocorreu um erro inesperado, tente novamente mais tarde'