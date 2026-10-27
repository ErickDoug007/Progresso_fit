import os

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import SuspiciousFileOperation
from django.http import FileResponse, Http404
from django.shortcuts import redirect, render
from django.utils._os import safe_join


def index_view(request):
    if request.user.is_authenticated:
        return redirect('contas:perfil')

    return render(request, 'core/index.html')


# Tipos que podem ser exibidos direto no navegador. Todo o resto (inclusive PDF) vai como download.
_IMAGENS_INLINE = {
    '.jpg': 'image/jpeg',
    '.jpeg': 'image/jpeg',
    '.png': 'image/png',
    '.webp': 'image/webp',
}


def _pode_ver(usuario, caminho):
    """
    Regra de acesso por pasta. O arquivo precisa estar referenciado no banco; assim
    nada "solto" na pasta media/ (nem por adivinhação de nome) é entregue.
    """
    from contas.models import Perfil
    from metricas.models import RegistroRanking
    from treinos.models import FotoTreino

    pasta = caminho.split('/', 1)[0]

    if pasta == 'fotos_perfil':
        # Mesma visibilidade do avatar nas páginas (qualquer usuário logado).
        return Perfil.objects.filter(foto_perfil=caminho).exists()

    if pasta == 'fotos_treino':
        dono = FotoTreino.objects.filter(imagem=caminho).values_list('usuario_id', flat=True).first()
        return dono is not None and (usuario.is_staff or dono == usuario.id)

    if pasta == 'comprovantes_ranking':
        registro = (
            RegistroRanking.objects
            .filter(foto_comprovante=caminho)
            .values('usuario_id', 'verificado', 'usuario__perfil__publico')
            .first()
        )
        if registro is None:
            return False
        return (
            usuario.is_staff
            or registro['usuario_id'] == usuario.id
            or (registro['verificado'] and bool(registro['usuario__perfil__publico']))
        )

    if pasta == 'verificacao_profissional':
        # Documento do conselho profissional: só o dono e a equipe que verifica.
        dono = Perfil.objects.filter(documento_verificacao=caminho).values_list('usuario_id', flat=True).first()
        return dono is not None and (usuario.is_staff or dono == usuario.id)

    return False


@login_required
def media_protegida(request, caminho):
    """Entrega arquivos enviados por usuários somente a quem tem permissão (substitui o /media/ aberto)."""
    try:
        caminho_absoluto = safe_join(settings.MEDIA_ROOT, caminho)
    except (SuspiciousFileOperation, ValueError):
        raise Http404

    if not os.path.isfile(caminho_absoluto) or not _pode_ver(request.user, caminho):
        raise Http404

    extensao = os.path.splitext(caminho)[1].lower()
    tipo = _IMAGENS_INLINE.get(extensao)
    resposta = FileResponse(
        open(caminho_absoluto, 'rb'),
        as_attachment=tipo is None,
        filename=os.path.basename(caminho),
        content_type=tipo or 'application/octet-stream',
    )
    # Defesa em profundidade: mesmo que algo estranho passe, o navegador não executa nada daqui.
    resposta['Content-Security-Policy'] = "default-src 'none'; style-src 'unsafe-inline'; sandbox"
    resposta['Cache-Control'] = 'private, max-age=3600'
    return resposta
