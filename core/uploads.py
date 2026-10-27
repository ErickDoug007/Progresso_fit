import os
import re
import uuid

from django.utils.deconstruct import deconstructible


@deconstructible
class UploadAleatorio:
    """
    upload_to que ignora o nome enviado pelo usuário e grava com um nome aleatório (uuid4).
    Evita nomes previsíveis/enumeráveis, caracteres estranhos e vazamento do nome original
    do arquivo (que costuma conter data, aparelho, etc.).
    """

    def __init__(self, pasta):
        self.pasta = pasta

    def __call__(self, instance, filename):
        extensao = os.path.splitext(filename)[1].lower()
        if not re.fullmatch(r'\.[a-z0-9]{1,5}', extensao):
            extensao = ''
        return f'{self.pasta}/{uuid.uuid4().hex}{extensao}'
