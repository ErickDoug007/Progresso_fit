from django.contrib import admin

from .models import Duvida


@admin.register(Duvida)
class DuvidaAdmin(admin.ModelAdmin):
    list_display = ('aluno', 'area', 'criada_em', 'respondida_por', 'respondida_em')
    list_filter = ('area',)
    search_fields = ('aluno__username', 'pergunta')