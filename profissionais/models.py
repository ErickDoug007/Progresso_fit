from django.contrib.auth.models import User
from django.db import models

# Profissão (contas.Perfil.profissao) -> área das dúvidas que ela responde.
AREA_POR_PROFISSAO = {'personal': 'treino', 'nutricionista': 'nutricao'}


class Duvida(models.Model):
    """Pergunta de um aluno para um profissional (educador físico ou nutricionista)."""
    AREA_CHOICES = [
        ('treino', 'Treino (educador físico)'),
        ('nutricao', 'Alimentação (nutricionista)'),
    ]

    aluno = models.ForeignKey(User, on_delete=models.CASCADE, related_name='duvidas')
    area = models.CharField(max_length=10, choices=AREA_CHOICES)
    pergunta = models.TextField()
    criada_em = models.DateTimeField(auto_now_add=True)

    resposta = models.TextField(blank=True)
    respondida_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='duvidas_respondidas'
    )
    respondida_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-criada_em']

    @property
    def respondida(self):
        return bool(self.resposta)

    def __str__(self):
        return f'Dúvida de {self.aluno.username} ({self.get_area_display()})'