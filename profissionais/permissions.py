import functools

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def profissional_verificado(*profissoes):
    """
    Só deixa passar quem está logado, tem cadastro profissional VERIFICADO (marcado no admin)
    e exerce uma das profissões indicadas. Quem muda o cadastro perde a verificação
    (veja contas.views.configuracoes_perfil_view), então a checagem vale a cada requisição.
    """
    def decorador(view):
        @functools.wraps(view)
        @login_required
        def envoltorio(request, *args, **kwargs):
            perfil = getattr(request.user, 'perfil', None)  # sem Perfil -> None
            if not (perfil and perfil.profissional_verificado and perfil.profissao in profissoes):
                messages.error(request, 'Esta área é restrita a profissionais verificados.')
                return redirect('contas:perfil')
            return view(request, *args, **kwargs)
        return envoltorio
    return decorador