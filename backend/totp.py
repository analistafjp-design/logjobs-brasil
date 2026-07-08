"""TOTP (RFC 6238) para verificação em duas etapas, sem dependências externas.

Mesma filosofia de security.py: implementado só com a biblioteca padrão do
Python, compatível com qualquer app autenticador (Google Authenticator, Authy,
1Password etc.) que siga o padrão — não depende de nenhum serviço externo de
SMS/e-mail, então funciona mesmo sem credenciais de terceiros configuradas.
"""
import base64
import hashlib
import hmac
import os
import struct
import time
import urllib.parse

PERIODO_SEGUNDOS = 30
DIGITOS = 6
JANELA_TOLERANCIA = 1  # aceita o código do período anterior/seguinte (relógios não são perfeitamente sincronizados)


def gerar_segredo() -> str:
    return base64.b32encode(os.urandom(20)).decode("ascii").rstrip("=")


def _hotp(segredo: str, contador: int) -> str:
    chave = base64.b32decode(segredo + "=" * (-len(segredo) % 8))
    msg = struct.pack(">Q", contador)
    digest = hmac.new(chave, msg, hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    codigo = (struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF) % (10 ** DIGITOS)
    return str(codigo).zfill(DIGITOS)


def verificar_totp(segredo: str, codigo: str, tempo: float = None) -> bool:
    if not segredo or not codigo or not codigo.isdigit() or len(codigo) != DIGITOS:
        return False
    tempo = tempo if tempo is not None else time.time()
    contador_atual = int(tempo // PERIODO_SEGUNDOS)
    return any(
        hmac.compare_digest(_hotp(segredo, contador_atual + delta), codigo)
        for delta in range(-JANELA_TOLERANCIA, JANELA_TOLERANCIA + 1)
    )


def uri_otpauth(email: str, segredo: str, emissor: str = "LogJobs Brasil") -> str:
    """URI padrão otpauth:// — qualquer app autenticador consegue importar a
    partir dela (como texto ou codificada num QR gerado pelo próprio app/usuário),
    sem depender de nenhum gerador de QR code de terceiros."""
    label = urllib.parse.quote(f"{emissor}:{email}")
    params = urllib.parse.urlencode({
        "secret": segredo,
        "issuer": emissor,
        "algorithm": "SHA1",
        "digits": DIGITOS,
        "period": PERIODO_SEGUNDOS,
    })
    return f"otpauth://totp/{label}?{params}"
