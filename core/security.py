"""
Utilitários de segurança compartilhados pelos apps.

- limitar_taxa: limita quantas vezes uma ação POST pode ser feita (por usuário ou IP).
- evitar_envio_duplicado: impede que o mesmo usuário dispare a mesma ação duas vezes
  ao mesmo tempo (duplo clique, reenvio de formulário, abas simultâneas).

Os contadores ficam no cache do Django (settings.CACHES). Com o LocMemCache padrão eles
valem por processo; em produção com vários workers use um cache compartilhado
(Redis/Memcached/DatabaseCache) para que o limite seja global.
"""
import functools
import hashlib

from django.contrib import messages
from django.core.cache import cache
from django.http import HttpResponse
from django.shortcuts import redirect, resolve_url


def ip_do_cliente(request):
    """
    IP de quem conectou. Usa só REMOTE_ADDR de propósito: X-Forwarded-For vem do cliente
    e é falsificável, então não é confiável sem um proxy configurado para sobrescrevê-lo.
    """
    return request.META.get('REMOTE_ADDR', '0.0.0.0')


def _chave(escopo, identificador):
    digest = hashlib.sha256(str(identificador).encode('utf-8')).hexdigest()[:32]
    return f'seg:{escopo}:{digest}'


def estourou_limite(escopo, identificador, limite, janela):
    """Registra uma tentativa (janela fixa de `janela` segundos). True se passou de `limite`."""
    chave = _chave(escopo, identificador)
    if cache.add(chave, 1, timeout=janela):
        return False
    try:
        total = cache.incr(chave)
    except ValueError:  # a chave expirou entre o add e o incr
        cache.add(chave, 1, timeout=janela)
        return False
    return total > limite


def _identificador(request, por):
    if por == 'usuario' and request.user.is_authenticated:
        return f'u{request.user.pk}'
    return f'ip{ip_do_cliente(request)}'


def _negar(request, mensagem, destino, redirecionar, status):
    if redirecionar:
        messages.error(request, mensagem)
        return redirect(resolve_url(destino) if destino else request.path)
    resposta = HttpResponse(mensagem, status=status, content_type='text/plain; charset=utf-8')
    resposta['Retry-After'] = '60'
    return resposta


def limitar_taxa(escopo, limite, janela, por='usuario', destino=None, redirecionar=True):
    """
    Limita requisições POST: no máximo `limite` a cada `janela` segundos.
    `destino`: nome de URL para onde voltar quando bloqueado (padrão: a própria página).
    `redirecionar=False` devolve um 429 simples (útil para endpoints sem tela, como o login do admin).
    """
    def decorador(view):
        @functools.wraps(view)
        def envoltorio(request, *args, **kwargs):
            if request.method == 'POST' and estourou_limite(
                escopo, _identificador(request, por), limite, janela
            ):
                return _negar(
                    request,
                    'Muitas tentativas em pouco tempo. Aguarde alguns minutos e tente novamente.',
                    destino, redirecionar, 429,
                )
            return view(request, *args, **kwargs)
        return envoltorio
    return decorador


def evitar_envio_duplicado(escopo, ttl=8, liberar_ao_fim=False, destino=None):
    """
    Só deixa uma requisição POST por usuário por vez para esta ação.
    - ttl: segundos que o "trinco" dura.
    - liberar_ao_fim: solta o trinco sempre que a view termina (use em ações longas, como a IA).
    Sem liberar_ao_fim, o trinco só continua preso quando o envio deu certo (a view respondeu com
    redirect), o que barra o reenvio/duplo clique logo em seguida. Se a resposta foi a página do
    formulário com erros, o trinco é solto na hora para o usuário corrigir e reenviar.
    """
    def decorador(view):
        @functools.wraps(view)
        def envoltorio(request, *args, **kwargs):
            if request.method != 'POST' or not request.user.is_authenticated:
                return view(request, *args, **kwargs)

            chave = _chave(f'trinco:{escopo}', request.user.pk)
            if not cache.add(chave, 1, timeout=ttl):
                messages.warning(
                    request, 'Seu envio anterior ainda está sendo processado. Aguarde um instante.'
                )
                return redirect(resolve_url(destino) if destino else request.path)
            soltar = True
            try:
                resposta = view(request, *args, **kwargs)
                soltar = liberar_ao_fim or resposta.status_code not in (301, 302, 303, 307, 308)
                return resposta
            finally:
                if soltar:
                    cache.delete(chave)
        return envoltorio
    return decorador
