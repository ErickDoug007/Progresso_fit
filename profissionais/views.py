from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from core.security import evitar_envio_duplicado, limitar_taxa
from nutricao.models import PlanoAlimentar
from .forms import DuvidaForm, RespostaForm, RevisaoPlanoForm
from .models import AREA_POR_PROFISSAO, Duvida
from .permissions import profissional_verificado

PROFISSOES_DO_PAINEL = tuple(AREA_POR_PROFISSAO)  # ('personal', 'nutricionista')


def _texto(valor):
    """Converte o conteúdo gerado pela IA (texto, lista ou dict) em texto simples para exibir."""
    if isinstance(valor, str):
        return valor
    if isinstance(valor, (list, tuple)):
        return '; '.join(str(item) for item in valor)
    if isinstance(valor, dict):
        return '; '.join(f'{k}: {v}' for k, v in valor.items())
    return str(valor)


def _refeicoes(conteudo):
    return [(str(nome), _texto(itens)) for nome, itens in conteudo.items()] if isinstance(conteudo, dict) else []


# ----------------------------------------------------------------------------- aluno
@login_required
@limitar_taxa('duvida', 10, 3600)
@evitar_envio_duplicado('duvida')
def minhas_duvidas_view(request):
    form = DuvidaForm(request.POST or None)
    if form.is_valid():
        duvida = form.save(commit=False)
        duvida.aluno = request.user
        duvida.save()
        messages.success(request, 'Dúvida enviada! Você verá a resposta aqui.')
        return redirect('profissionais:minhas_duvidas')
    duvidas = request.user.duvidas.select_related('respondida_por__perfil')
    return render(request, 'profissionais/minhas_duvidas.html', {'form': form, 'duvidas': duvidas})


# ------------------------------------------------------------------------ profissional
@profissional_verificado(*PROFISSOES_DO_PAINEL)
def painel_view(request):
    profissao = request.user.perfil.profissao
    area = AREA_POR_PROFISSAO[profissao]
    duvidas = Duvida.objects.filter(area=area, resposta='').exclude(aluno=request.user)
    contexto = {
        'profissao': request.user.perfil.get_profissao_display(),
        'eh_nutricionista': profissao == 'nutricionista',
        'duvidas_pendentes': duvidas.select_related('aluno').order_by('criada_em')[:50],
        'duvidas_respondidas': Duvida.objects.filter(respondida_por=request.user).select_related('aluno')[:10],
    }
    if profissao == 'nutricionista':
        pendentes = PlanoAlimentar.objects.filter(status='pendente').exclude(usuario=request.user)
        contexto['planos_pendentes'] = pendentes.select_related('usuario', 'ficha').order_by('gerado_em')[:50]
        contexto['planos_revisados'] = PlanoAlimentar.objects.filter(especialista=request.user).select_related('usuario')[:10]
    return render(request, 'profissionais/painel.html', contexto)


@profissional_verificado('nutricionista')
@limitar_taxa('revisar_plano', 60, 3600)
@evitar_envio_duplicado('revisar_plano')
def revisar_plano_view(request, pk):
    plano = get_object_or_404(PlanoAlimentar.objects.select_related('usuario', 'ficha'), pk=pk)
    if plano.usuario_id == request.user.id:
        raise Http404  # não revisa o próprio plano
    if plano.status != 'pendente':
        messages.info(request, 'Este plano já foi revisado.')
        return redirect('profissionais:painel')

    form = RevisaoPlanoForm(request.POST or None)
    if form.is_valid():
        acao = form.cleaned_data['acao']
        if acao in ('aprovado', 'ajustado') and not plano.conteudo:
            form.add_error('acao', 'Não dá para aprovar um plano que a IA ainda não gerou. Rejeite com um parecer.')
        else:
            # Só atualiza se ainda estiver pendente: se outro profissional decidiu antes, não sobrescreve.
            atualizados = PlanoAlimentar.objects.filter(pk=plano.pk, status='pendente').update(
                status=acao,
                especialista=request.user,
                observacoes_especialista=form.cleaned_data['observacoes'],
            )
            if atualizados:
                messages.success(request, 'Revisão registrada. O aluno já vê o resultado.')
            else:
                messages.info(request, 'Outro profissional revisou este plano antes de você.')
            return redirect('profissionais:painel')

    return render(request, 'profissionais/revisar_plano.html', {
        'plano': plano,
        'ficha': plano.ficha,
        'refeicoes': _refeicoes(plano.conteudo),
        'form': form,
    })


@profissional_verificado(*PROFISSOES_DO_PAINEL)
@limitar_taxa('responder_duvida', 60, 3600)
@evitar_envio_duplicado('responder_duvida')
def responder_duvida_view(request, pk):
    area = AREA_POR_PROFISSAO[request.user.perfil.profissao]
    duvida = get_object_or_404(Duvida.objects.select_related('aluno'), pk=pk, area=area)  # outra área -> 404
    if duvida.aluno_id == request.user.id:
        raise Http404
    if duvida.respondida:
        messages.info(request, 'Esta dúvida já foi respondida.')
        return redirect('profissionais:painel')

    form = RespostaForm(request.POST or None)
    if form.is_valid():
        atualizadas = Duvida.objects.filter(pk=duvida.pk, resposta='').update(
            resposta=form.cleaned_data['resposta'],
            respondida_por=request.user,
            respondida_em=timezone.now(),
        )
        messages.success(request, 'Resposta enviada.' if atualizadas else 'Outro profissional respondeu antes de você.')
        return redirect('profissionais:painel')
    return render(request, 'profissionais/responder_duvida.html', {'duvida': duvida, 'form': form})