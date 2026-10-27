"""Testes de segurança: acesso a arquivos, uploads, privacidade, limites, CSRF e vazamento de erros."""
import io
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import requests
from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from PIL import Image

from contas.forms import EditarUsuarioForm, ProfissionalForm
from contas.models import Perfil
from core.security import _chave
from metricas.models import MetricaCorporal, RegistroRanking
from nutricao.models import FichaNutricional
from treinos.models import FichaAnamnese, FotoTreino
from treinos.services import _sanitizar_resultado, gerar_plano_treino


def png_bytes(tamanho=(8, 8)):
    buf = io.BytesIO()
    Image.new('RGB', tamanho, 'red').save(buf, 'PNG')
    return buf.getvalue()


def png_upload(nome='foto.png'):
    return SimpleUploadedFile(nome, png_bytes(), content_type='image/png')


class BaseSeguranca(TestCase):
    def setUp(self):
        cache.clear()
        self.media = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self.media)
        self.override.enable()
        self.addCleanup(self.override.disable)
        self.addCleanup(shutil.rmtree, self.media, ignore_errors=True)

        self.dono = User.objects.create_user('dono', 'dono@example.com', 'senha-forte-123', first_name='Joana')
        self.outro = User.objects.create_user('outro', 'outro@example.com', 'senha-forte-123')
        self.staff = User.objects.create_user('equipe', 'eq@example.com', 'senha-forte-123', is_staff=True)

    def gravar_arquivo(self, nome, conteudo=None):
        caminho = Path(self.media) / nome
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_bytes(conteudo if conteudo is not None else png_bytes())
        return nome


# ---------------------------------------------------------------- arquivos enviados
class MediaProtegidaTests(BaseSeguranca):
    def url(self, nome):
        return f'/media/{nome}'

    def test_anonimo_nao_acessa_nada(self):
        nome = self.gravar_arquivo('fotos_perfil/a.png')
        Perfil.objects.create(usuario=self.dono, foto_perfil=nome)
        resposta = self.client.get(self.url(nome))
        self.assertEqual(resposta.status_code, 302)
        self.assertIn('/accounts/login/', resposta['Location'])

    def test_foto_de_treino_so_dono_e_equipe(self):
        nome = self.gravar_arquivo('fotos_treino/t.png')
        FotoTreino.objects.create(usuario=self.dono, imagem=nome)

        self.client.force_login(self.dono)
        self.assertEqual(self.client.get(self.url(nome)).status_code, 200)
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(self.url(nome)).status_code, 200)
        self.client.force_login(self.outro)
        self.assertEqual(self.client.get(self.url(nome)).status_code, 404)

    def test_documento_de_verificacao_so_dono_e_equipe_e_vai_como_download(self):
        nome = self.gravar_arquivo('verificacao_profissional/d.pdf', b'%PDF-1.4 conteudo')
        Perfil.objects.create(usuario=self.dono, documento_verificacao=nome)

        self.client.force_login(self.outro)
        self.assertEqual(self.client.get(self.url(nome)).status_code, 404)

        self.client.force_login(self.dono)
        resposta = self.client.get(self.url(nome))
        self.assertEqual(resposta.status_code, 200)
        self.assertIn('attachment', resposta['Content-Disposition'])

        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(self.url(nome)).status_code, 200)

    def test_comprovante_regras_de_visibilidade(self):
        nome = self.gravar_arquivo('comprovantes_ranking/c.png')
        reg = RegistroRanking.objects.create(
            usuario=self.dono, categoria='biceps', valor=40, foto_comprovante=nome, verificado=False,
        )
        perfil = Perfil.objects.create(usuario=self.dono, publico=True)

        self.client.force_login(self.outro)
        self.assertEqual(self.client.get(self.url(nome)).status_code, 404, 'pendente: só dono/equipe')

        reg.verificado = True
        reg.save()
        self.assertEqual(self.client.get(self.url(nome)).status_code, 200, 'verificado + público aparece no ranking')

        perfil.publico = False
        perfil.save()
        self.assertEqual(self.client.get(self.url(nome)).status_code, 404, 'perfil privado some do ranking')

        self.client.force_login(self.dono)
        self.assertEqual(self.client.get(self.url(nome)).status_code, 200)

    def test_foto_de_perfil_para_qualquer_logado(self):
        nome = self.gravar_arquivo('fotos_perfil/p.png')
        Perfil.objects.create(usuario=self.dono, foto_perfil=nome)
        self.client.force_login(self.outro)
        self.assertEqual(self.client.get(self.url(nome)).status_code, 200)

    def test_arquivo_sem_registro_no_banco_nao_e_entregue(self):
        nome = self.gravar_arquivo('fotos_treino/solto.png')
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(self.url(nome)).status_code, 404)

    def test_path_traversal_bloqueado(self):
        (Path(self.media).parent / 'segredo.txt').write_text('segredo')
        self.client.force_login(self.staff)
        for tentativa in (
            '/media/../segredo.txt',
            '/media/fotos_perfil/../../segredo.txt',
            '/media/fotos_perfil/%2e%2e/%2e%2e/segredo.txt',
            '/media//etc/passwd',
            '/media/..%2f..%2fsegredo.txt',
        ):
            self.assertEqual(self.client.get(tentativa).status_code, 404, tentativa)

    def test_cabecalhos_de_defesa_na_entrega(self):
        nome = self.gravar_arquivo('fotos_perfil/h.png')
        Perfil.objects.create(usuario=self.dono, foto_perfil=nome)
        self.client.force_login(self.dono)
        resposta = self.client.get(self.url(nome))
        self.assertIn("default-src 'none'", resposta['Content-Security-Policy'])
        self.assertEqual(resposta['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(resposta['Content-Type'], 'image/png')


# ---------------------------------------------------------------- uploads
class UploadsTests(BaseSeguranca):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.dono)

    def enviar_foto(self, arquivo):
        return self.client.post(reverse('treinos:enviar_foto'), {'imagem': arquivo}, follow=True)

    def test_imagem_valida_e_salva_com_nome_aleatorio(self):
        self.enviar_foto(png_upload('IMG_20230514_minha_foto.png'))
        foto = FotoTreino.objects.get()
        self.assertTrue(foto.imagem.name.startswith('fotos_treino/'))
        self.assertNotIn('minha_foto', foto.imagem.name)

    def test_html_disfarcado_de_imagem_e_rejeitado(self):
        falso = SimpleUploadedFile('x.png', b'<html><script>alert(1)</script></html>', content_type='image/png')
        self.enviar_foto(falso)
        self.assertEqual(FotoTreino.objects.count(), 0)

    def test_svg_e_rejeitado(self):
        svg = SimpleUploadedFile('x.svg', b'<svg xmlns="http://www.w3.org/2000/svg"><script/></svg>', content_type='image/svg+xml')
        self.enviar_foto(svg)
        self.assertEqual(FotoTreino.objects.count(), 0)

    def test_extensao_diferente_do_conteudo_e_rejeitada(self):
        self.enviar_foto(SimpleUploadedFile('x.jpg', png_bytes(), content_type='image/jpeg'))
        self.assertEqual(FotoTreino.objects.count(), 0)

    def test_arquivo_grande_demais_e_rejeitado(self):
        grande = SimpleUploadedFile('g.png', png_bytes() + b'0' * (6 * 1024 * 1024), content_type='image/png')
        self.enviar_foto(grande)
        self.assertEqual(FotoTreino.objects.count(), 0)

    def test_documento_profissional_aceita_pdf_real_e_rejeita_executavel_e_pdf_falso(self):
        def form(arquivo):
            return ProfissionalForm(
                {'profissao': 'nutricionista'}, {'documento_verificacao': arquivo},
                instance=Perfil.objects.get_or_create(usuario=self.dono)[0],
            )

        self.assertTrue(form(SimpleUploadedFile('r.pdf', b'%PDF-1.7 ok', content_type='application/pdf')).is_valid())
        self.assertFalse(form(SimpleUploadedFile('r.pdf', b'MZ\x90 nao e pdf', content_type='application/pdf')).is_valid())
        self.assertFalse(form(SimpleUploadedFile('r.exe', b'MZ\x90', content_type='application/octet-stream')).is_valid())
        self.assertFalse(form(SimpleUploadedFile('r.html', b'<script>1</script>', content_type='text/html')).is_valid())

    def test_ranking_rejeita_comprovante_que_nao_e_imagem(self):
        resposta = self.client.post(reverse('metricas:enviar_ranking'), {
            'categoria': 'biceps', 'valor': '40',
            'foto_comprovante': SimpleUploadedFile('c.png', b'GIF89a-nao-eh-png', content_type='image/png'),
        })
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(RegistroRanking.objects.count(), 0)


# ---------------------------------------------------------------- privacidade / IDOR / CSRF
class PrivacidadeTests(BaseSeguranca):
    def test_perfil_privado_esconde_nome_real_e_descricao_de_terceiros(self):
        Perfil.objects.create(usuario=self.dono, publico=False, descricao='descricao-secreta-xyz')
        self.client.force_login(self.outro)
        html = self.client.get(reverse('contas:ver_perfil', args=['dono'])).content.decode()
        self.assertNotIn('Joana', html)
        self.assertNotIn('descricao-secreta-xyz', html)

        self.client.force_login(self.dono)
        html = self.client.get(reverse('contas:perfil')).content.decode()
        self.assertIn('Joana', html)
        self.assertIn('descricao-secreta-xyz', html)

    def test_perfil_publico_continua_visivel(self):
        Perfil.objects.create(usuario=self.dono, publico=True, descricao='bio-publica')
        self.client.force_login(self.outro)
        html = self.client.get(reverse('contas:ver_perfil', args=['dono'])).content.decode()
        self.assertIn('Joana', html)
        self.assertIn('bio-publica', html)

    def test_ver_perfil_de_outro_nao_grava_no_banco(self):
        self.assertFalse(Perfil.objects.filter(usuario=self.dono).exists())
        self.client.force_login(self.outro)
        self.assertEqual(self.client.get(reverse('contas:ver_perfil', args=['dono'])).status_code, 200)
        self.assertFalse(Perfil.objects.filter(usuario=self.dono).exists())

    def test_metricas_de_perfil_privado_nao_vazam(self):
        MetricaCorporal.objects.create(usuario=self.dono, peso=77.7, altura=181)
        Perfil.objects.create(usuario=self.dono, publico=False)
        self.client.force_login(self.outro)
        html = self.client.get(reverse('contas:ver_perfil', args=['dono'])).content.decode()
        self.assertNotIn('77.7', html)
        self.assertNotIn('77,7', html)

    def test_alternar_privacidade_so_post_e_so_do_proprio_usuario(self):
        Perfil.objects.create(usuario=self.dono, publico=False)
        outro_perfil = Perfil.objects.create(usuario=self.outro, publico=False)
        url = reverse('contas:alternar_privacidade')

        self.assertEqual(self.client.post(url).status_code, 302)  # anônimo -> login
        self.client.force_login(self.dono)
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(self.client.post(url).status_code, 200)
        self.assertTrue(Perfil.objects.get(usuario=self.dono).publico)
        outro_perfil.refresh_from_db()
        self.assertFalse(outro_perfil.publico)

    def test_csrf_e_exigido_nos_posts(self):
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.dono)
        self.assertEqual(cliente.post(reverse('contas:alternar_privacidade')).status_code, 403)
        self.assertEqual(cliente.post(reverse('nutricao:formulario'), {'pode_comer': 'x', 'rotina_atual': 'y'}).status_code, 403)

    def test_usuario_nao_se_auto_verifica_como_profissional(self):
        self.client.force_login(self.dono)
        self.client.post(reverse('contas:configuracoes_perfil'), {
            'profissao': 'nutricionista', 'profissional_verificado': 'on',
        })
        perfil = Perfil.objects.get(usuario=self.dono)
        self.assertFalse(perfil.profissional_verificado)

    def test_username_reservado_e_bloqueado(self):
        for nome in ('privacidade', 'Admin', 'suporte'):
            self.assertFalse(EditarUsuarioForm({'username': nome, 'first_name': 'X'}, instance=self.dono).is_valid(), nome)
        self.assertTrue(EditarUsuarioForm({'username': 'joana_fit', 'first_name': 'Joana'}, instance=self.dono).is_valid())

    def test_paginas_sensiveis_exigem_login(self):
        for nome in ('contas:perfil', 'contas:editar_perfil', 'metricas:metricas', 'metricas:evolucao',
                     'nutricao:nutricao', 'treinos:treino', 'treinos:formulario'):
            resposta = self.client.get(reverse(nome))
            self.assertEqual(resposta.status_code, 302, nome)
            self.assertIn('/accounts/login/', resposta['Location'], nome)

    def test_dados_de_outro_usuario_nao_aparecem_em_listas_proprias(self):
        MetricaCorporal.objects.create(usuario=self.dono, peso=91.3, altura=170)
        FichaNutricional.objects.create(usuario=self.dono, pode_comer='segredo-alimentar', rotina_atual='x')
        self.client.force_login(self.outro)
        self.assertNotIn('91,3', self.client.get(reverse('metricas:evolucao')).content.decode())
        self.assertEqual(self.client.get(reverse('nutricao:nutricao')).status_code, 302)  # sem ficha própria -> formulário


# ---------------------------------------------------------------- validação de entrada
class ValidacaoTests(BaseSeguranca):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.dono)

    def test_metricas_fora_da_faixa_sao_rejeitadas(self):
        for peso, altura in (('-5', '170'), ('9999', '170'), ('70', '10'), ('70', '900')):
            self.client.post(reverse('metricas:metricas'), {'peso': peso, 'altura': altura})
        self.assertEqual(MetricaCorporal.objects.count(), 0)

        self.client.post(reverse('metricas:metricas'), {'peso': '70.5', 'altura': '172'})
        self.assertEqual(MetricaCorporal.objects.count(), 1)

    def test_categoria_invalida_no_ranking_cai_no_padrao(self):
        resposta = self.client.get(reverse('metricas:ranking'), {'categoria': "x' OR 1=1 --<script>"})
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.context['categoria_atual'], 'biceps')
        self.assertNotContains(resposta, '<script>')

    def test_nutricao_limita_tamanho_e_orcamento_negativo(self):
        self.client.post(reverse('nutricao:formulario'), {'pode_comer': 'a' * 1501, 'rotina_atual': 'b'})
        self.client.post(reverse('nutricao:formulario'), {'pode_comer': 'a', 'rotina_atual': 'b', 'orcamento_alimentar': '-10'})
        self.assertEqual(FichaNutricional.objects.count(), 0)

    def test_anamnese_com_texto_gigante_nao_chega_na_ia(self):
        dados = dict(status='iniciante', objetivo='forca', tempo_minutos='60', dias=['Segunda'], observacoes='x' * 801)
        with patch('treinos.views.gerar_plano_treino') as ia:
            self.client.post(reverse('treinos:formulario'), dados)
        ia.assert_not_called()
        self.assertEqual(FichaAnamnese.objects.count(), 0)


# ---------------------------------------------------------------- limites e duplo envio
DADOS_TREINO = dict(status='iniciante', objetivo='forca', tempo_minutos='60', dias=['Segunda'])
PLANO_OK = {'resumo': 'r', 'dias': {'Segunda': [{'exercicio': 'Agachamento'}]}, 'orientacoes': 'o'}


class LimitesTests(BaseSeguranca):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.dono)

    def test_geracao_por_ia_tem_limite_por_hora(self):
        with patch('treinos.views.gerar_plano_treino', return_value=PLANO_OK) as ia:
            for _ in range(12):
                self.client.post(reverse('treinos:formulario'), DADOS_TREINO)
        self.assertEqual(ia.call_count, 8)

    def test_envio_duplicado_simultaneo_e_bloqueado(self):
        trinco = _chave('trinco:ia_formulario', self.dono.pk)
        cache.add(trinco, 1, timeout=60)  # simula uma geração já em andamento
        with patch('treinos.views.gerar_plano_treino', return_value=PLANO_OK) as ia:
            resposta = self.client.post(reverse('treinos:formulario'), DADOS_TREINO, follow=True)
        ia.assert_not_called()
        self.assertEqual(FichaAnamnese.objects.count(), 0)
        self.assertContains(resposta, 'ainda está sendo processado')

    def test_duplo_clique_em_formulario_comum_nao_duplica_registro(self):
        dados = {'pode_comer': 'tudo', 'rotina_atual': 'arroz e feijao'}
        self.client.post(reverse('nutricao:formulario'), dados)
        self.client.post(reverse('nutricao:formulario'), dados)  # reenvio imediato
        self.assertEqual(FichaNutricional.objects.count(), 1)

    def test_fluxo_feliz_de_treino_redireciona_sem_erro(self):
        with patch('treinos.views.gerar_plano_treino', return_value=PLANO_OK):
            resposta = self.client.post(reverse('treinos:formulario'), DADOS_TREINO)
        self.assertRedirects(resposta, reverse('treinos:treino'), fetch_redirect_response=False)

    def test_login_do_admin_tem_limite_de_tentativas(self):
        cliente = Client()
        url = reverse('admin:login')
        codigos = [cliente.post(url, {'username': 'x', 'password': 'y'}).status_code for _ in range(12)]
        self.assertIn(429, codigos)
        self.assertEqual(codigos[0], 200)

    def test_erro_da_ia_nao_vaza_detalhe_para_a_pagina(self):
        resposta_http = type('R', (), {
            'status_code': 403,
            'json': lambda self: {'error': {'message': 'SEGREDO-DO-PROVEDOR projeto-123'}},
        })()
        with patch('treinos.views.gerar_plano_treino', side_effect=requests.HTTPError(response=resposta_http)):
            resposta = self.client.post(reverse('treinos:formulario'), DADOS_TREINO)
        html = resposta.content.decode()
        self.assertNotIn('SEGREDO-DO-PROVEDOR', html)
        self.assertNotIn('projeto-123', html)
        self.assertEqual(FichaAnamnese.objects.count(), 0)


# ---------------------------------------------------------------- serviço de IA / configuração
class ServicoIATests(SimpleTestCase):
    def test_sanitizacao_rejeita_estrutura_invalida_e_corta_tamanhos(self):
        with self.assertRaises(TypeError):
            _sanitizar_resultado({'dias': ['nao', 'e', 'dict']})
        with self.assertRaises(TypeError):
            _sanitizar_resultado({'dias': {'Segunda': 'texto'}})
        limpo = _sanitizar_resultado({
            'resumo': 'r' * 5000,
            'dias': {'Segunda': [{'exercicio': 'e' * 999, 'series': 4}] + ['lixo'] * 50},
            'orientacoes': None,
        })
        self.assertEqual(len(limpo['resumo']), 2000)
        self.assertEqual(len(limpo['dias']['Segunda'][0]['exercicio']), 120)
        self.assertEqual(limpo['dias']['Segunda'][0]['series'], '4')
        self.assertEqual(limpo['orientacoes'], '')

    @override_settings(GEMINI_API_KEY='k', GEMINI_MODEL='../../evil?x=1')
    def test_modelo_com_caracteres_perigosos_nao_chega_na_url(self):
        with patch('treinos.services.requests.post') as post:
            with self.assertRaises(RuntimeError):
                gerar_plano_treino(object())
        post.assert_not_called()

    @override_settings(GEMINI_API_KEY='')
    def test_sem_chave_nao_chama_a_api(self):
        with patch('treinos.services.requests.post') as post:
            with self.assertRaises(RuntimeError):
                gerar_plano_treino(object())
        post.assert_not_called()


class ConfiguracaoProducaoTests(SimpleTestCase):
    def _rodar(self, **env):
        base = {k: v for k, v in os.environ.items() if k not in ('DEBUG', 'SECRET_KEY')}
        base.update(env)
        return subprocess.run(
            [sys.executable, 'manage.py', 'check', '--deploy'],
            cwd=settings.BASE_DIR, env=base, capture_output=True, text=True,
        )

    def test_producao_nao_tem_avisos_criticos_do_django(self):
        r = self._rodar(DEBUG='False', SECRET_KEY='k3y-AbCdEfGhIjKlMnOpQrStUvWxYz0123456789-AbCdEfGhIjKlMnOpQrStUvWxYz', ALLOWED_HOSTS='exemplo.com')
        saida = r.stdout + r.stderr
        for aviso in ('W004', 'W008', 'W009', 'W012', 'W016', 'W018'):
            self.assertNotIn(f'security.{aviso}', saida, saida)

    def test_producao_recusa_secret_key_fraca(self):
        r = self._rodar(DEBUG='False', SECRET_KEY='django-insecure-' + 'x' * 40)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn('SECRET_KEY', r.stderr + r.stdout)
