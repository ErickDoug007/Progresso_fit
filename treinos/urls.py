from django.urls import path
from . import views

app_name = 'treinos'

urlpatterns = [
    path('', views.treino_view, name='treino'),
    path('formulario/', views.formulario_view, name='formulario'),
    path('foto/', views.enviar_foto_view, name='enviar_foto'),
    path('continuar/', views.continuar_treino_anterior_view, name='continuar_anterior'),
]