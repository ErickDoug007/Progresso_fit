from django import forms

from core.validators import limitar_numero, validar_imagem_upload
from .models import MetricaCorporal, RegistroRanking

# Campos de medidas em centímetros (todos exceto peso, altura, % gordura etc.)
CAMPOS_MEDIDAS_CM = [
    'deltoide', 'torax',
    'braco_esq_relaxado', 'braco_esq_contraido', 'braco_dir_relaxado', 'braco_dir_contraido',
    'antebraco_esq', 'antebraco_dir',
    'cintura', 'abdomen', 'quadril',
    'coxa_esq_alta', 'coxa_esq_baixa', 'coxa_dir_alta', 'coxa_dir_baixa',
    'panturrilha_esq', 'panturrilha_dir',
]


class MetricaCorporalForm(forms.ModelForm):
    class Meta:
        model = MetricaCorporal
        exclude = ['usuario', 'data_medicao']  # esses dois a view preenche sozinha

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Faixas realistas: barram valores absurdos/negativos (no servidor e no navegador).
        limitar_numero(self, 20, 500, 'peso')
        limitar_numero(self, 50, 272, 'altura')
        limitar_numero(self, 1, 80, 'percentual_gordura')
        limitar_numero(self, 0, 60, 'gordura_visceral')
        limitar_numero(self, 300, 10000, 'metabolismo_basal')
        limitar_numero(self, 5, 300, *CAMPOS_MEDIDAS_CM)


class RegistroRankingForm(forms.ModelForm):
    class Meta:
        model = RegistroRanking
        fields = ['categoria', 'valor', 'foto_comprovante']
        labels = {
            'categoria': 'Categoria',
            'valor': 'Medida (cm)',
            'foto_comprovante': 'Foto comprovando a medida',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        limitar_numero(self, 5, 300, 'valor')

    def clean_foto_comprovante(self):
        return validar_imagem_upload(self.cleaned_data.get('foto_comprovante'))
