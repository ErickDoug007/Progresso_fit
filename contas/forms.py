from django import forms
from django.contrib.auth.models import User
from allauth.account.forms import SignupForm

from core.validators import validar_documento_upload, validar_imagem_upload
from .models import Perfil

# Nomes que conflitam com rotas ou que serviriam para se passar pela equipe.
USERNAMES_RESERVADOS = {'privacidade', 'admin', 'administrador', 'suporte', 'moderador', 'progressofit'}


class CustomSignupForm(SignupForm):
    first_name = forms.CharField(
        max_length=150,
        label='Nome completo',
        widget=forms.TextInput(attrs={'placeholder': 'Seu nome'})
    )

    def save(self, request):
        user = super().save(request)
        user.first_name = self.cleaned_data['first_name']
        user.save()
        return user


class EditarUsuarioForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'first_name']
        labels = {
            'username': 'Nome de usuário',
            'first_name': 'Nome completo',
        }

    def clean_username(self):
        username = self.cleaned_data['username']
        if username.lower() in USERNAMES_RESERVADOS:
            raise forms.ValidationError('Esse nome de usuário não está disponível.')
        return username


class EditarPerfilForm(forms.ModelForm):
    class Meta:
        model = Perfil
        fields = ['foto_perfil', 'descricao', 'publico']
        labels = {
            'foto_perfil': 'Foto de perfil',
            'descricao': 'Descrição',
            'publico': 'Perfil público',
        }
        widgets = {
            'descricao': forms.Textarea(attrs={'maxlength': 150, 'rows': 3}),
        }

    def clean_foto_perfil(self):
        return validar_imagem_upload(self.cleaned_data.get('foto_perfil'))


class ProfissionalForm(forms.ModelForm):
    class Meta:
        model = Perfil
        fields = ['profissao', 'documento_verificacao']
        labels = {
            'profissao': 'Sou profissional',
            'documento_verificacao': 'Documento de verificação (registro no conselho)',
        }

    def clean_documento_verificacao(self):
        return validar_documento_upload(self.cleaned_data.get('documento_verificacao'))
