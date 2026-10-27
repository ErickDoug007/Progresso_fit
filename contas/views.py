from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from allauth.account.models import EmailAddress

from core.security import evitar_envio_duplicado, limitar_taxa
from .models import Perfil
from .forms import EditarUsuarioForm, EditarPerfilForm, ProfissionalForm


def calcular_tempo_membro(inicio):
    hoje = timezone.now().date()
    meses = max(0, (hoje.year - inicio.year) * 12 + hoje.month - inicio.month - (hoje.day < inicio.day))
    n, (um, varios) = (meses // 12, ('ano', 'anos')) if meses >= 12 else (meses, ('mês', 'meses'))
    return n, f"{um if n == 1 else varios} na plataforma"


def _montar_contexto_perfil(usuario_alvo, request):
    """
    Monta o contexto de exibição de um perfil, respeitando a regra de privacidade.
    Reaproveitado tanto por quem vê o próprio perfil quanto por quem vê o de outra pessoa.
    """
    eh_dono = (usuario_alvo == request.user)
    if eh_dono:
        perfil, _ = Perfil.objects.get_or_create(usuario=usuario_alvo)
    else:
        # Ver o perfil de outra pessoa não deve gravar nada no banco (e o padrão é privado).
        try:
            perfil = usuario_alvo.perfil
        except Perfil.DoesNotExist:
            perfil = Perfil(usuario=usuario_alvo)
    pode_ver_completo = eh_dono or perfil.publico

    ultima_medicao = usuario_alvo.metricas.first()
    numero_tempo, texto_tempo = calcular_tempo_membro(usuario_alvo.date_joined.date())

    contexto = {
        'usuario_alvo': usuario_alvo,
        'perfil': perfil,
        'eh_dono': eh_dono,
        'pode_ver_completo': pode_ver_completo,

        # Sempre visíveis, mesmo com perfil privado:
        'qtd_treinos_concluidos': 32,    
        'numero_tempo': numero_tempo,
        'texto_tempo': texto_tempo,
        'nivel': ultima_medicao.get_nivel_display() if ultima_medicao else None,
    }

    # Dados sensíveis só entram no contexto se houver permissão de fato
    if pode_ver_completo:
        contexto['historico'] = usuario_alvo.metricas.all()[:5]
        plano_treino = usuario_alvo.planos_treino.first()
        contexto['treino_hoje'] = plano_treino.treino_do_dia() if plano_treino else None

    # Plano alimentar é dado de saúde: só o próprio dono vê (e o parecer do profissional).
    if eh_dono:
        contexto['plano_alimentar'] = usuario_alvo.planos_alimentares.select_related('especialista').first()

    return contexto


@login_required
def perfil_view(request):
    """Exibe o PRÓPRIO perfil de quem está logado."""
    contexto = _montar_contexto_perfil(request.user, request)
    return render(request, 'contas/perfil.html', contexto)


@login_required
def ver_perfil_view(request, username):
    """Exibe o perfil de QUALQUER usuário pelo username, respeitando privacidade."""
    usuario_alvo = get_object_or_404(User, username=username)
    contexto = _montar_contexto_perfil(usuario_alvo, request)
    return render(request, 'contas/perfil.html', contexto)



@login_required
@limitar_taxa('editar_perfil', 20, 3600)
@evitar_envio_duplicado('editar_perfil')
def editar_perfil_view(request):
    perfil, created = Perfil.objects.get_or_create(usuario=request.user)

    if request.method == 'POST':
        form_usuario = EditarUsuarioForm(request.POST, instance=request.user)
        form_perfil = EditarPerfilForm(request.POST, request.FILES, instance=perfil)

        if form_usuario.is_valid() and form_perfil.is_valid():
            form_usuario.save()
            
            # Instancia o perfil sem salvar no banco imediatamente
            perfil_obj = form_perfil.save(commit=False)

            # Verifica se o botão/input JS ativou a remoção da foto
            if request.POST.get('remover_foto') == 'true':
                if perfil_obj.foto_perfil:
                    perfil_obj.foto_perfil.delete(save=False)  # Remove o arquivo físico do storage
                perfil_obj.foto_perfil = None                 # Remove a referência no banco de dados

            perfil_obj.save()
            messages.success(request, 'Perfil atualizado com sucesso!')
            return redirect('contas:perfil')
    else:
        form_usuario = EditarUsuarioForm(instance=request.user)
        form_perfil = EditarPerfilForm(instance=perfil)

    return render(request, 'contas/editar_perfil.html', {
        'form_usuario': form_usuario,
        'form_perfil': form_perfil,
    })


@login_required
@limitar_taxa('config_profissional', 10, 3600)
@evitar_envio_duplicado('config_profissional')
def configuracoes_perfil_view(request):
    perfil, _ = Perfil.objects.get_or_create(usuario=request.user)
    form = ProfissionalForm(request.POST or None, request.FILES or None, instance=perfil)

    if form.is_valid():
        if form.has_changed():
            form.instance.profissional_verificado = False  # mudou o cadastro, precisa verificar de novo
        form.save()
        messages.success(request, 'Cadastro profissional enviado para verificação.')
        return redirect('contas:configuracoes_perfil')

    email_conta = request.user.email or (
        EmailAddress.objects
        .filter(user=request.user)
        .order_by('-primary', '-verified')
        .values_list('email', flat=True)
        .first()
    )
    return render(request, 'contas/configuracoes_perfil.html', {
        'form': form,
        'perfil': perfil,
        'email_conta': email_conta,
    })



@login_required
@require_POST
def alternar_privacidade_view(request):
    """Inverte perfil.publico do usuário logado e devolve o novo estado em JSON."""
    perfil, _ = Perfil.objects.get_or_create(usuario=request.user)
    perfil.publico = not perfil.publico
    perfil.save(update_fields=['publico'])
    return JsonResponse({'publico': perfil.publico})