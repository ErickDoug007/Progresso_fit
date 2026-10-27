from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import F, Window

from core.security import evitar_envio_duplicado, limitar_taxa
from .models import MetricaCorporal, RegistroRanking
from django.db.models.functions import RowNumber
from .forms import MetricaCorporalForm, RegistroRankingForm


def _montar_dados_grafico(usuario):
    historico = MetricaCorporal.objects.filter(usuario=usuario)
    historico_cronologico = historico.reverse()  # do mais antigo para o mais novo

    dados_grafico = {
        'labels': [m.data_medicao.strftime('%b/%Y') for m in historico_cronologico],
        'peso': [float(m.peso) for m in historico_cronologico],
        'gordura': [float(m.percentual_gordura) if m.percentual_gordura else None for m in historico_cronologico],
    }
    return historico, dados_grafico


@login_required
def evolucao_view(request):
    historico, dados_grafico = _montar_dados_grafico(request.user)

    return render(request, 'metricas/metricas_evolucao.html', {
        'historico': historico,
        'dados_grafico_json': dados_grafico,
    })


@login_required
@limitar_taxa('metricas', 30, 3600)
@evitar_envio_duplicado('metricas')
def painel_view(request):
    if request.method == 'POST':
        form = MetricaCorporalForm(request.POST)
        if form.is_valid():
            medicao = form.save(commit=False)
            medicao.usuario = request.user

            ultima_medicao = request.user.metricas.first()
            if ultima_medicao:
                # Herda da medição anterior o que não foi informado (peso e altura são obrigatórios)
                for campo in form.fields.keys() - {'peso', 'altura'}:
                    if getattr(medicao, campo) in (None, ''):
                        setattr(medicao, campo, getattr(ultima_medicao, campo))

            medicao.save()
            messages.success(request, 'Medição salva com sucesso!')
            return redirect('metricas:evolucao')
    else:
        form = MetricaCorporalForm()

    return render(request, 'metricas/metricas.html', {'form': form})


# Quantos envios aguardando verificação cada usuário pode ter ao mesmo tempo
# (evita encher o disco com fotos e a fila de moderação).
MAX_PENDENTES_RANKING = 10


@login_required
@limitar_taxa('ranking_envio', 5, 3600)
@evitar_envio_duplicado('ranking_envio')
def enviar_ranking_view(request):
    """Envia uma medida + foto pra concorrer no ranking."""
    if request.method == 'POST':
        if RegistroRanking.objects.filter(usuario=request.user, verificado=False).count() >= MAX_PENDENTES_RANKING:
            messages.error(request, 'Você já tem muitos envios aguardando verificação. Aguarde a análise.')
            return redirect('metricas:ranking')
        form = RegistroRankingForm(request.POST, request.FILES)
        if form.is_valid():
            registro = form.save(commit=False)
            registro.usuario = request.user
            registro.save()
            messages.success(request, 'Enviado! Assim que for verificado, aparece no ranking.')
            return redirect('metricas:ranking')
    else:
        form = RegistroRankingForm()

    return render(request, 'metricas/enviar_ranking.html', {'form': form})


def ranking_view(request):
    """
    Mostra o ranking por categoria com registros verificados por um admin.
    """
    categoria = request.GET.get('categoria')
    if categoria not in {valor for valor, _ in RegistroRanking.CATEGORIA_CHOICES}:
        categoria = None  # valor desconhecido/malicioso: cai na categoria padrão
    if not categoria:
        categoria = (
            RegistroRanking.objects
            .filter(verificado=True, usuario__perfil__publico=True)
            .order_by('-enviado_em')
            .values_list('categoria', flat=True)
            .first()
            or 'biceps'
        )

    # Mostra a submissão aprovada mais recente de cada usuário na categoria.
    melhores = (
        RegistroRanking.objects
        .filter(categoria=categoria, verificado=True, usuario__perfil__publico=True)
        .annotate(
            posicao_usuario=Window(
                expression=RowNumber(),
                partition_by=[F('usuario_id')],
                order_by=[F('enviado_em').desc(), F('pk').desc()],
            )
        )
        .filter(posicao_usuario=1)
        .select_related('usuario')
        .order_by('-valor')[:20]
    )

    return render(request, 'metricas/ranking.html', {
        'melhores': melhores,
        'categoria_atual': categoria,
        'categorias': RegistroRanking.CATEGORIA_CHOICES,
    })