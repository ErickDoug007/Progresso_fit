from django.urls import path
from . import views

app_name = 'metricas'

urlpatterns = [
    path('metricas/', views.painel_view, name='metricas'),
    path('evolucao/', views.evolucao_view, name='evolucao'),
    path('ranking/', views.ranking_view, name='ranking'),
    path('ranking/enviar/', views.enviar_ranking_view, name='enviar_ranking'),
]