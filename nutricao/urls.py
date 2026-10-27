from django.urls import path
from . import views

app_name = 'nutricao'

urlpatterns = [
    path('', views.nutricao_view, name='nutricao'),
    path('formulario/', views.formulario_view, name='formulario'),
]