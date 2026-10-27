from django.contrib import admin
from django.utils.html import format_html
from .models import MetricaCorporal, RegistroRanking
# Register your models here.

admin.site.register(MetricaCorporal)


def _apagar_aprovacoes_anteriores(registro):
    anteriores = RegistroRanking.objects.filter(
        usuario=registro.usuario,
        categoria=registro.categoria,
        verificado=True,
    ).exclude(pk=registro.pk)

    for anterior in anteriores:
        if anterior.foto_comprovante:
            anterior.foto_comprovante.delete(save=False)
        anterior.delete()


@admin.register(RegistroRanking)
class RegistroRankingAdmin(admin.ModelAdmin):
    list_display = (
        'usuario',
        'categoria',
        'valor',
        'foto_preview',
        'verificado',
        'enviado_em',
    )
    list_filter = ('categoria', 'verificado')
    readonly_fields = ('foto_preview',)

    def save_model(self, request, obj, form, change):
        ja_estava_aprovado = (
            RegistroRanking.objects
            .filter(pk=obj.pk)
            .values_list('verificado', flat=True)
            .first()
        )
        super().save_model(request, obj, form, change)
        if obj.verificado and ja_estava_aprovado is not True:
            _apagar_aprovacoes_anteriores(obj)

    @admin.display(description='Foto de comprovação')
    def foto_preview(self, obj):
        if not obj.foto_comprovante:
            return 'Nenhuma foto enviada'

        return format_html(
            '<a href="{}" target="_blank" rel="noopener noreferrer">'
            '<img src="{}" alt="Foto de comprovação" '
            'style="max-width:240px; max-height:180px; object-fit:contain;">'
            '</a>',
            obj.foto_comprovante.url,
            obj.foto_comprovante.url,
        )
