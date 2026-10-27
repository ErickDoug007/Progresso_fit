from django.urls import path
from . import views

app_name = 'contas'

urlpatterns = [
    path('perfil/', views.perfil_view, name='perfil'),
    path('editar_perfil/', views.editar_perfil_view, name='editar_perfil'),
    path('configuracoes_perfil/', views.configuracoes_perfil_view, name='configuracoes_perfil'),
    path('perfil/privacidade/', views.alternar_privacidade_view, name='alternar_privacidade'),
    path('perfil/<str:username>/', views.ver_perfil_view, name='ver_perfil'),
]