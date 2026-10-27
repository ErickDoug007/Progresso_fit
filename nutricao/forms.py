from django import forms

from core.validators import limitar_numero, limitar_texto
from .models import FichaNutricional


class FichaNutricionalForm(forms.ModelForm):
    class Meta:
        model = FichaNutricional
        fields = ['pode_comer', 'rotina_atual', 'orcamento_alimentar']
        labels = {
            'pode_comer': 'O que você pode comer',
            'rotina_atual': 'O que você come no dia a dia',
            'orcamento_alimentar': 'Dinheiro disponível para comida (opcional)',
        }
        widgets = {
            'pode_comer': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Alergias, intolerâncias, alimentos que evita...'}),
            'rotina_atual': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Café da manhã, almoço, jantar, lanches...'}),
            'orcamento_alimentar': forms.NumberInput(attrs={'placeholder': 'Ex: 600.00'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        limitar_texto(self, pode_comer=1500, rotina_atual=1500)
        limitar_numero(self, 0, 99999, 'orcamento_alimentar')
