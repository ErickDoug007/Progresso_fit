from unittest.mock import Mock, patch

import requests
from django.test import SimpleTestCase

from .views import _gerar_e_salvar_plano


class GeminiErrorTests(SimpleTestCase):
    @patch('treinos.views.gerar_plano_treino')
    def test_erro_403_nao_vaza_detalhe_do_provedor_ao_usuario(self, gerar_plano):
        response = Mock(status_code=403)
        response.json.return_value = {
            'error': {'message': 'This API key does not have permission to use this API.'}
        }
        gerar_plano.side_effect = requests.HTTPError(response=response)

        plano, erro = _gerar_e_salvar_plano(object())

        self.assertIsNone(plano)
        self.assertIn('indisponível', erro)
        # Detalhes técnicos (chave, permissões, modelo) ficam só no log do servidor.
        self.assertNotIn('This API key', erro)
        self.assertNotIn('GEMINI', erro)
        self.assertNotIn('chave', erro)

    @patch('treinos.views.gerar_plano_treino')
    def test_erro_http_sem_corpo_json_tem_fallback(self, gerar_plano):
        response = Mock(status_code=403)
        response.json.side_effect = ValueError('invalid JSON')
        gerar_plano.side_effect = requests.HTTPError(response=response)

        plano, erro = _gerar_e_salvar_plano(object())

        self.assertIsNone(plano)
        self.assertIn('indisponível', erro)
        self.assertNotIn('Detalhe:', erro)
