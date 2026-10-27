from django import forms

from core.validators import limitar_texto
from .models import Duvida


class DuvidaForm(forms.ModelForm):
    class Meta:
        model = Duvida
        fields = ['area', 'pergunta']
        labels = {'area': 'Sobre o quê?', 'pergunta': 'Sua dúvida'}
        widgets = {'pergunta': forms.Textarea(attrs={'rows': 4})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        limitar_texto(self, pergunta=1000)


class RespostaForm(forms.Form):
    resposta = forms.CharField(label='Sua resposta', widget=forms.Textarea(attrs={'rows': 6}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        limitar_texto(self, resposta=2000)


class RevisaoPlanoForm(forms.Form):
    ACOES = [
        ('aprovado', 'Aprovar'),
        ('ajustado', 'Aprovar com ajustes'),
        ('rejeitado', 'Rejeitar'),
    ]
    acao = forms.ChoiceField(label='Decisão', choices=ACOES, widget=forms.RadioSelect)
    observacoes = forms.CharField(
        label='Parecer para o aluno', required=False, widget=forms.Textarea(attrs={'rows': 5})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        limitar_texto(self, observacoes=1500)

    def clean(self):
        dados = super().clean()
        if dados.get('acao') in ('ajustado', 'rejeitado') and not dados.get('observacoes'):
            self.add_error('observacoes', 'Explique o ajuste ou o motivo da rejeição.')
        return dados