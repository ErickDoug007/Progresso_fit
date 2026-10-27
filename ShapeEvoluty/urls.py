"""
URL configuration for ShapeEvoluty project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
"""
from django.conf import settings
from django.contrib import admin
from django.urls import path, include

from core.security import limitar_taxa
from core.views import media_protegida

# O login do admin não passa pelo allauth (que tem limite de tentativas), então limitamos aqui:
# no máximo 10 tentativas por minuto por IP. Precisa vir antes de admin.site.urls ser usado.
admin.site.login = limitar_taxa(
    'admin_login', 10, 60, por='ip', redirecionar=False
)(admin.site.login)

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('', include('core.urls')),
    path('contas/', include('contas.urls')),
    path('metricas/', include('metricas.urls')),
    path('treinos/', include('treinos.urls')),
    path('nutricao/', include('nutricao.urls')),
    path('profissionais/', include('profissionais.urls')),
    # Arquivos enviados: sempre por esta view (login + permissão), em debug e em produção.
    path('media/<path:caminho>', media_protegida, name='media_protegida'),
]
