from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from core.security import evitar_envio_duplicado, limitar_taxa
from .models import FichaNutricional, PlanoAlimentar
from .forms import FichaNutricionalForm


@login_required
def nutricao_view(request):
    """Página base: mostra o status do plano alimentar atual, ou manda preencher a ficha."""
    ficha = FichaNutricional.objects.filter(usuario=request.user).first()

    if not ficha:
        return redirect('nutricao:formulario')

    plano = ficha.planos.first()

    return render(request, 'nutricao/nutricao.html', {
        'ficha': ficha,
        'plano': plano,
    })


@login_required
@limitar_taxa('nutricao_ficha', 10, 3600)
@evitar_envio_duplicado('nutricao_ficha')
def formulario_view(request):
    if request.method == 'POST':
        form = FichaNutricionalForm(request.POST)
        if form.is_valid():
            ficha = form.save(commit=False)
            ficha.usuario = request.user
            ficha.save()

            # Cria o plano com status pendente — a geração de verdade por IA
            # e o fluxo de aprovação pelo especialista entram numa próxima etapa
            PlanoAlimentar.objects.create(usuario=request.user, ficha=ficha)

            messages.success(request, 'Ficha enviada! Seu plano alimentar está sendo preparado.')
            return redirect('nutricao:nutricao')
    else:
        form = FichaNutricionalForm()

    return render(request, 'nutricao/nutricao_form.html', {'form': form})
