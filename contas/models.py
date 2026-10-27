from django.db import models
from django.contrib.auth.models import User

from core.uploads import UploadAleatorio

# Create your models here.
class Perfil(models.Model):
    PROFISSAO_CHOICES = [
        ('nutricionista', 'Nutricionista'),
        ('personal', 'Personal trainer'),
        ('fisioterapeuta', 'Fisioterapeuta'),
        ('outro', 'Outro'),
    ]

    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')

    foto_perfil = models.ImageField(upload_to=UploadAleatorio('fotos_perfil'), blank=True, null=True)
    
    descricao = models.TextField(max_length=150, blank=True)
    
    publico = models.BooleanField(default=False)

    profissao = models.CharField(max_length=20, choices=PROFISSAO_CHOICES, blank=True)
    
    documento_verificacao = models.FileField(upload_to=UploadAleatorio('verificacao_profissional'), blank=True)
   
    profissional_verificado = models.BooleanField(default=False)  # marcado no admin
    
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Perfil de {self.usuario.username}'