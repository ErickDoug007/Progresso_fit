from django import forms

from core.validators import limitar_numero, limitar_texto, validar_imagem_upload
from .models import FichaAnamnese, FotoTreino


class FichaAnamneseForm(forms.ModelForm):
    dias = forms.MultipleChoiceField(
        choices=FichaAnamnese.DIA_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        label='Dias disponíveis para treinar'
    )

    class Meta:
        model = FichaAnamnese
        fields = [
            'status', 'objetivo', 'tempo_minutos', 'dias',
            'exercicios_atuais', 'cargas_atuais', 'series_repeticoes_atual', 'observacoes',
        ]
        labels = {
            'status': 'Seu nível de experiência',
            'objetivo': 'Objetivo principal',
            'tempo_minutos': 'Tempo disponível por sessão (minutos)',
            'exercicios_atuais': 'Exercícios que você já pratica ou prefere',
            'cargas_atuais': 'Cargas atuais nos exercícios principais (kg)',
            'series_repeticoes_atual': 'Volume habitual (ex: 3x10, 4x12...)',
            'observacoes': 'Lesões, limitações, dores ou preferências',
        }
        widgets = {
            'exercicios_atuais': forms.Textarea(attrs={'rows': 2}),
            'cargas_atuais': forms.Textarea(attrs={'rows': 2}),
            'series_repeticoes_atual': forms.Textarea(attrs={'rows': 2}),
            'observacoes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Esses textos são enviados à IA: sem limite, dá para gastar a cota/dinheiro da API.
        limitar_texto(
            self,
            exercicios_atuais=600, cargas_atuais=600,
            series_repeticoes_atual=400, observacoes=800,
        )
        limitar_numero(self, 10, 300, 'tempo_minutos')


class FotoTreinoForm(forms.ModelForm):
    class Meta:
        model = FotoTreino
        fields = ['imagem']

    def clean_imagem(self):
        return validar_imagem_upload(self.cleaned_data.get('imagem'))
