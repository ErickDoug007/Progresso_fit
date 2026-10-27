from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from allauth.account.models import EmailAddress


class ConfiguracoesPerfilEmailTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='teste',
            email='teste@example.com',
            password='senha-forte-123',
        )
        self.client.force_login(self.user)

    def test_exibe_email_cadastrado(self):
        response = self.client.get(reverse('contas:configuracoes_perfil'))

        self.assertContains(response, 'teste@example.com')
        self.assertContains(response, reverse('account_email'))

    def test_indica_quando_email_nao_esta_cadastrado(self):
        self.user.email = ''
        self.user.save(update_fields=['email'])

        response = self.client.get(reverse('contas:configuracoes_perfil'))

        self.assertContains(response, 'E-mail não cadastrado')

    def test_exibe_email_principal_do_allauth_se_user_email_esta_vazio(self):
        self.user.email = ''
        self.user.save(update_fields=['email'])
        EmailAddress.objects.create(
            user=self.user,
            email='principal@example.com',
            primary=True,
            verified=True,
        )

        response = self.client.get(reverse('contas:configuracoes_perfil'))

        self.assertContains(response, 'principal@example.com')

    def test_pagina_gerenciar_email_mostra_endereco_e_opcoes(self):
        EmailAddress.objects.create(
            user=self.user,
            email='teste@example.com',
            primary=True,
            verified=True,
        )

        response = self.client.get(reverse('account_email'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Gerenciar e-mail')
        self.assertContains(response, 'teste@example.com')
        self.assertContains(response, 'Definir como principal')
        self.assertContains(response, 'Reenviar confirmação')
        self.assertContains(response, 'Adicionar e-mail')

    def test_pagina_gerenciar_email_sem_endereco_mostra_aviso_e_formulario(self):
        EmailAddress.objects.filter(user=self.user).delete()
        self.user.email = ''
        self.user.save(update_fields=['email'])

        response = self.client.get(reverse('account_email'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Não há endereço de e-mail associado')
        self.assertContains(response, 'Novo endereço de e-mail')
