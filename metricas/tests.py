from datetime import datetime, timezone as datetime_timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib import admin
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from types import SimpleNamespace

from .admin import RegistroRankingAdmin
from contas.models import Perfil
from .models import RegistroRanking


class RankingAprovacaoTests(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user(
            username='perfil_privado',
            email='privado@example.com',
            password='senha-forte-123',
        )
        Perfil.objects.create(usuario=self.usuario, publico=False)

    def criar_registro(self, verificado, categoria='biceps'):
        return RegistroRanking.objects.create(
            usuario=self.usuario,
            categoria=categoria,
            valor='42.0',
            foto_comprovante=SimpleUploadedFile(
                'comprovante.jpg',
                b'conteudo-de-teste',
                content_type='image/jpeg',
            ),
            verificado=verificado,
        )

    def test_medida_aprovada_de_perfil_privado_nao_aparece(self):
        self.criar_registro(verificado=True)

        response = self.client.get(reverse('metricas:ranking'), {'categoria': 'biceps'})

        self.assertNotContains(response, 'perfil_privado')
        self.assertContains(response, 'Ainda não há registros verificados')

    def test_categoria_mais_recente_de_perfil_privado_nao_e_selecionada(self):
        self.criar_registro(verificado=True, categoria='antebraço')

        response = self.client.get(reverse('metricas:ranking'))

        self.assertNotContains(response, 'perfil_privado')
        self.assertEqual(response.context['categoria_atual'], 'biceps')

    def test_medida_aprovada_de_perfil_publico_aparece(self):
        self.usuario.perfil.publico = True
        self.usuario.perfil.save(update_fields=['publico'])
        registro = self.criar_registro(verificado=True)
        registro.enviado_em = datetime(
            2025, 6, 15, 12, 0, tzinfo=datetime_timezone.utc
        )
        registro.save(update_fields=['enviado_em'])

        response = self.client.get(reverse('metricas:ranking'), {'categoria': 'biceps'})

        self.assertContains(response, 'perfil_privado')
        self.assertContains(response, '42,0 cm')
        self.assertContains(response, 'Data do envio')
        self.assertContains(response, '15/06/2025')
        self.assertContains(response, 'Comprovante da medida de perfil_privado')
        self.assertRegex(
            response.content.decode(),
            r'/media/comprovantes_ranking/[0-9a-f]{32}\.jpg',
        )
        html = response.content.decode()
        self.assertLess(html.index('Foto Músculo'), html.index('Data do envio'))

    def test_medida_pendente_nao_aparece(self):
        self.criar_registro(verificado=False)

        response = self.client.get(reverse('metricas:ranking'), {'categoria': 'biceps'})

        self.assertNotContains(response, 'perfil_privado')
        self.assertContains(response, 'Ainda não há registros verificados')

    def test_nova_medida_aprovada_substitui_anterior_mesmo_se_for_menor(self):
        self.usuario.perfil.publico = True
        self.usuario.perfil.save(update_fields=['publico'])
        anterior = self.criar_registro(verificado=True)
        anterior.valor = '50.0'
        anterior.enviado_em = anterior.enviado_em.replace(year=2025)
        anterior.save(update_fields=['valor', 'enviado_em'])

        mais_recente = self.criar_registro(verificado=True)
        mais_recente.valor = '40.0'
        mais_recente.enviado_em = anterior.enviado_em.replace(year=2026)
        mais_recente.save(update_fields=['valor', 'enviado_em'])

        response = self.client.get(reverse('metricas:ranking'), {'categoria': 'biceps'})

        self.assertContains(response, '40,0 cm')
        self.assertNotContains(response, '50,0 cm')
        self.assertEqual(len(response.context['melhores']), 1)

    def test_medida_pendente_nao_substitui_ultima_aprovada(self):
        self.usuario.perfil.publico = True
        self.usuario.perfil.save(update_fields=['publico'])
        aprovada = self.criar_registro(verificado=True)
        aprovada.valor = '42.0'
        aprovada.save(update_fields=['valor'])
        pendente = self.criar_registro(verificado=False)
        pendente.valor = '55.0'
        pendente.enviado_em = aprovada.enviado_em.replace(year=2027)
        pendente.save(update_fields=['valor', 'enviado_em'])

        response = self.client.get(reverse('metricas:ranking'), {'categoria': 'biceps'})

        self.assertContains(response, '42,0 cm')
        self.assertNotContains(response, '55,0 cm')
        self.assertEqual(len(response.context['melhores']), 1)


class RegistroRankingAdminTests(SimpleTestCase):
    def test_preview_links_to_uploaded_proof_image(self):
        registro = SimpleNamespace(
            foto_comprovante=SimpleNamespace(
                name='comprovantes_ranking/prova.jpg',
                url='/media/comprovantes_ranking/prova.jpg',
            )
        )

        preview = str(RegistroRankingAdmin.foto_preview(None, registro))

        self.assertIn('src="/media/comprovantes_ranking/prova.jpg"', preview)
        self.assertIn('href="/media/comprovantes_ranking/prova.jpg"', preview)
        self.assertIn('target="_blank"', preview)


class AprovacaoSubstituiRegistroAnteriorTests(TestCase):
    def test_aprovacao_apaga_registro_anterior_e_foto_da_mesma_categoria(self):
        with TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                usuario = User.objects.create_user(
                    username='atleta',
                    password='senha-forte-123',
                )
                anterior = RegistroRanking.objects.create(
                    usuario=usuario,
                    categoria='biceps',
                    valor='50.0',
                    foto_comprovante=SimpleUploadedFile(
                        'foto-antiga.jpg',
                        b'foto antiga',
                        content_type='image/jpeg',
                    ),
                    verificado=True,
                )
                caminho_foto_antiga = Path(anterior.foto_comprovante.path)
                nova = RegistroRanking.objects.create(
                    usuario=usuario,
                    categoria='biceps',
                    valor='40.0',
                    foto_comprovante=SimpleUploadedFile(
                        'foto-nova.jpg',
                        b'foto nova',
                        content_type='image/jpeg',
                    ),
                    verificado=False,
                )
                outra_categoria = RegistroRanking.objects.create(
                    usuario=usuario,
                    categoria='peito',
                    valor='100.0',
                    foto_comprovante=SimpleUploadedFile(
                        'foto-outra-categoria.jpg',
                        b'outra categoria',
                        content_type='image/jpeg',
                    ),
                    verificado=True,
                )

                nova.verificado = True
                model_admin = RegistroRankingAdmin(RegistroRanking, admin.site)
                model_admin.save_model(
                    RequestFactory().post('/admin/metricas/registroranking/'),
                    nova,
                    form=None,
                    change=True,
                )

                self.assertFalse(
                    RegistroRanking.objects.filter(pk=anterior.pk).exists()
                )
                self.assertFalse(caminho_foto_antiga.exists())
                self.assertTrue(
                    RegistroRanking.objects.filter(pk=nova.pk, verificado=True).exists()
                )
                self.assertTrue(
                    RegistroRanking.objects.filter(pk=outra_categoria.pk).exists()
                )
