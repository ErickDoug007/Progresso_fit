from django.urls import path

from . import views

app_name = 'profissionais'

urlpatterns = [
    path('painel/', views.painel_view, name='painel'),
    path('planos/<int:pk>/', views.revisar_plano_view, name='revisar_plano'),
    path('duvidas/', views.minhas_duvidas_view, name='minhas_duvidas'),
    path('duvidas/<int:pk>/responder/', views.responder_duvida_view, name='responder_duvida'),
]