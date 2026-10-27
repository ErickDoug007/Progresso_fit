"""Validação de uploads e de limites de campos (aplicada nos formulários)."""
import os

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.core.validators import MaxLengthValidator, MaxValueValidator, MinValueValidator
from PIL import Image, UnidentifiedImageError

TAMANHO_MAX_IMAGEM = 5 * 1024 * 1024       # 5 MB
TAMANHO_MAX_DOCUMENTO = 8 * 1024 * 1024    # 8 MB
PIXELS_MAX = 40_000_000                    # ~40 MP; evita "bombas de descompressão"

FORMATOS_IMAGEM = {'JPEG': {'.jpg', '.jpeg'}, 'PNG': {'.png'}, 'WEBP': {'.webp'}}
EXTENSOES_IMAGEM = {e for exts in FORMATOS_IMAGEM.values() for e in exts}


def _eh_upload_novo(arquivo):
    # Valor existente (já salvo) ou False (marcado para limpar) não precisa ser revalidado.
    return isinstance(arquivo, UploadedFile)


def _checar_imagem(arquivo):
    try:
        arquivo.seek(0)
        imagem = Image.open(arquivo)
        formato = imagem.format
        largura, altura = imagem.size
        if largura * altura > PIXELS_MAX:
            raise ValidationError('A imagem tem dimensões grandes demais.')
        imagem.verify()
    except ValidationError:
        raise
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError, Image.DecompressionBombError):
        raise ValidationError('Envie uma imagem válida (JPG, PNG ou WEBP).')
    finally:
        arquivo.seek(0)

    if formato not in FORMATOS_IMAGEM:
        raise ValidationError('Formato não permitido. Use JPG, PNG ou WEBP.')
    return formato


def validar_imagem_upload(arquivo, tamanho_max=TAMANHO_MAX_IMAGEM):
    """Aceita só JPG/PNG/WEBP reais (confere o conteúdo, não só a extensão), com limite de tamanho."""
    if not _eh_upload_novo(arquivo):
        return arquivo
    if arquivo.size > tamanho_max:
        raise ValidationError(f'A imagem passa de {tamanho_max // (1024 * 1024)} MB.')
    extensao = os.path.splitext(arquivo.name)[1].lower()
    formato = _checar_imagem(arquivo)
    if extensao not in FORMATOS_IMAGEM[formato]:
        raise ValidationError('A extensão do arquivo não corresponde ao conteúdo da imagem.')
    return arquivo


def validar_documento_upload(arquivo, tamanho_max=TAMANHO_MAX_DOCUMENTO):
    """Documento de verificação: PDF de verdade (assinatura %PDF-) ou imagem JPG/PNG/WEBP."""
    if not _eh_upload_novo(arquivo):
        return arquivo
    if arquivo.size > tamanho_max:
        raise ValidationError(f'O arquivo passa de {tamanho_max // (1024 * 1024)} MB.')
    extensao = os.path.splitext(arquivo.name)[1].lower()
    if extensao == '.pdf':
        arquivo.seek(0)
        cabecalho = arquivo.read(5)
        arquivo.seek(0)
        if cabecalho != b'%PDF-':
            raise ValidationError('O arquivo não é um PDF válido.')
        return arquivo
    if extensao in EXTENSOES_IMAGEM:
        formato = _checar_imagem(arquivo)
        if extensao not in FORMATOS_IMAGEM[formato]:
            raise ValidationError('A extensão do arquivo não corresponde ao conteúdo da imagem.')
        return arquivo
    raise ValidationError('Formato não permitido. Envie PDF, JPG, PNG ou WEBP.')


def limitar_texto(formulario, **maximos):
    """formulario.fields[campo] ganha limite de caracteres (servidor + atributo maxlength no HTML)."""
    for nome, maximo in maximos.items():
        campo = formulario.fields[nome]
        campo.validators.append(MaxLengthValidator(maximo))
        campo.widget.attrs['maxlength'] = maximo


def limitar_numero(formulario, minimo, maximo, *nomes):
    """Faixa de valores aceitos (servidor + min/max no HTML) para cada campo numérico."""
    for nome in nomes:
        campo = formulario.fields[nome]
        campo.validators.append(MinValueValidator(minimo))
        campo.validators.append(MaxValueValidator(maximo))
        campo.widget.attrs.update({'min': minimo, 'max': maximo})
