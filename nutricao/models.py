from django.db import models
from django.contrib.auth.models import User


class FichaNutricional(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='fichas_nutricionais')
    data_submissao = models.DateTimeField(auto_now_add=True)

    pode_comer = models.TextField(
        help_text='Alimentos que pode comer sem restrição, alergias ou intolerâncias a evitar'
    )
    rotina_atual = models.TextField(
        help_text='O que costuma comer no dia a dia (café da manhã, almoço, jantar, lanches)'
    )
    orcamento_alimentar = models.DecimalField(
        max_digits=7, decimal_places=2, blank=True, null=True,
        help_text='Dinheiro disponível para comida por mês (opcional)'
    )

    class Meta:
        ordering = ['-data_submissao']

    def __str__(self):
        return f'Ficha nutricional de {self.usuario.username} em {self.data_submissao.strftime("%d/%m/%Y")}'


class PlanoAlimentar(models.Model):
    STATUS_CHOICES = [
        ('pendente', 'Aguardando aprovação'),
        ('aprovado', 'Aprovado'),
        ('ajustado', 'Ajustado pelo especialista'),
        ('rejeitado', 'Rejeitado'),
    ]

    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='planos_alimentares')
    ficha = models.ForeignKey(FichaNutricional, on_delete=models.CASCADE, related_name='planos')
    especialista = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='planos_revisados')

    gerado_em = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')
    conteudo = models.JSONField(blank=True, null=True, help_text='Refeições sugeridas pela IA')
    observacoes_especialista = models.TextField(blank=True)

    class Meta:
        ordering = ['-gerado_em']

    def __str__(self):
        return f'Plano de {self.usuario.username} ({self.get_status_display()})'