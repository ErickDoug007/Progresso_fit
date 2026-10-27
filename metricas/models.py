from django.db import models
from django.contrib.auth.models import User

from core.uploads import UploadAleatorio


class MetricaCorporal(models.Model):
    NIVEL_CHOICES = [
        ('iniciante', 'Iniciante'),
        ('intermediario', 'Intermediário'),
        ('avancado', 'Avançado'),
    ]

    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='metricas')
    data_medicao = models.DateTimeField(auto_now_add=True)

    # Nível agora mora aqui, não em Perfil — porque evolui junto com as medições
    nivel = models.CharField(max_length=20, choices=NIVEL_CHOICES, blank=True, null=True)

    # Composição corporal
    peso = models.DecimalField(max_digits=5, decimal_places=1, help_text='kg')
    altura = models.PositiveSmallIntegerField(help_text='cm')
    percentual_gordura = models.DecimalField(max_digits=4, decimal_places=1, blank=True, null=True)
    gordura_visceral = models.PositiveSmallIntegerField(blank=True, null=True)
    metabolismo_basal = models.PositiveIntegerField(blank=True, null=True, help_text='kcal')

    # Membros superiores
    deltoide = models.DecimalField(max_digits=5, decimal_places=1, blank=True, null=True)
    torax = models.DecimalField(max_digits=5, decimal_places=1, blank=True, null=True)
    braco_esq_relaxado = models.DecimalField(max_digits=5, decimal_places=1, blank=True, null=True)
    braco_esq_contraido = models.DecimalField(max_digits=5, decimal_places=1, blank=True, null=True)
    braco_dir_relaxado = models.DecimalField(max_digits=5, decimal_places=1, blank=True, null=True)
    braco_dir_contraido = models.DecimalField(max_digits=5, decimal_places=1, blank=True, null=True)
    antebraco_esq = models.DecimalField(max_digits=5, decimal_places=1, blank=True, null=True)
    antebraco_dir = models.DecimalField(max_digits=5, decimal_places=1, blank=True, null=True)

    # Tronco / cintura
   
    cintura = models.DecimalField(max_digits=5, decimal_places=1, blank=True, null=True)
    abdomen = models.DecimalField(max_digits=5, decimal_places=1, blank=True, null=True)
    quadril = models.DecimalField(max_digits=5, decimal_places=1, blank=True, null=True)

    # Membros inferiores
    coxa_esq_alta = models.DecimalField(max_digits=5, decimal_places=1, blank=True, null=True)
    coxa_esq_baixa = models.DecimalField(max_digits=5, decimal_places=1, blank=True, null=True)
    coxa_dir_alta = models.DecimalField(max_digits=5, decimal_places=1, blank=True, null=True)
    coxa_dir_baixa = models.DecimalField(max_digits=5, decimal_places=1, blank=True, null=True)
    panturrilha_esq = models.DecimalField(max_digits=5, decimal_places=1, blank=True, null=True)
    panturrilha_dir = models.DecimalField(max_digits=5, decimal_places=1, blank=True, null=True)

    class Meta:
        ordering = ['-data_medicao']  # mais recente primeiro, por padrão

    def __str__(self):
        # Proteção caso data_medicao seja nula
        data = self.data_medicao.strftime("%d/%m/%Y") if self.data_medicao else "Data não informada"
        # Proteção caso usuario seja nulo (menos comum, mas possível dependendo da modelagem)
        usuario = self.usuario.username if self.usuario else "Usuário Desconhecido"
        return f'{usuario} — {data}'

    @property
    def imc(self):
        # Valida se peso e altura existem antes de fazer qualquer conta
        if self.peso and self.altura:
            return round(float(self.peso) / (self.altura / 100) ** 2, 1)
        return None

    @property
    def massa_magra(self):
        # Garante que tanto o peso quanto o percentual existem
        if self.peso and self.percentual_gordura is not None:
            return round(float(self.peso) * (1 - float(self.percentual_gordura) / 100), 1)
        return None
    
    
class RegistroRanking(models.Model):
    CATEGORIA_CHOICES = [
        ('deltoide', 'Deltoide'),
        ('peito', 'Tórax/Peitoral'),
        ('biceps', 'Bíceps'),
        ('antebraço', 'Antebraço'),
        ('cintura', 'Cintura (menor = melhor)'),
        ('quadril', 'Quadril'),
        ('coxa', 'Coxa'),
        ('panturrilha', 'Panturrilha'),
        
    ]

    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='registros_ranking')
    categoria = models.CharField(max_length=20, choices=CATEGORIA_CHOICES)
    valor = models.DecimalField(max_digits=5, decimal_places=1, help_text='cm')
    foto_comprovante = models.ImageField(upload_to=UploadAleatorio('comprovantes_ranking'))
    verificado = models.BooleanField(default=False)
    enviado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-valor']

    def __str__(self):
        status = 'verificado' if self.verificado else 'pendente'
        return f'{self.usuario.username} — {self.get_categoria_display()}: {self.valor}cm ({status})'