"""Login social com Google (OAuth 2.0 Authorization Code flow), usando só a
biblioteca padrão do Python para as chamadas HTTP — mesma filosofia de
security.py e totp.py, evitando dependências como authlib/google-auth-library
que têm superfícies grandes e trazem outras dependências transitivas junto.
"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/auth/google/callback")

AUTORIZACAO_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


def configurado() -> bool:
    return bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)


def url_autorizacao(state: str) -> str:
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "prompt": "select_account",
    }
    return f"{AUTORIZACAO_URL}?{urllib.parse.urlencode(params)}"


def _post_form(url: str, dados: dict) -> dict:
    corpo = urllib.parse.urlencode(dados).encode()
    requisicao = urllib.request.Request(url, data=corpo, method="POST")
    requisicao.add_header("Content-Type", "application/x-www-form-urlencoded")
    with urllib.request.urlopen(requisicao, timeout=10) as resposta:
        return json.loads(resposta.read().decode())


class ErroTrocaGoogle(Exception):
    pass


def trocar_codigo_por_perfil(code: str) -> dict:
    """Troca o código de autorização por um access_token e busca o perfil do
    usuário (email, nome, id do Google). Levanta ErroTrocaGoogle se o código
    for inválido/expirado ou a chamada à API do Google falhar."""
    try:
        tokens = _post_form(TOKEN_URL, {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "code": code,
            "redirect_uri": GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        })
        access_token = tokens["access_token"]

        requisicao = urllib.request.Request(USERINFO_URL)
        requisicao.add_header("Authorization", f"Bearer {access_token}")
        with urllib.request.urlopen(requisicao, timeout=10) as resposta:
            return json.loads(resposta.read().decode())
    except (urllib.error.URLError, KeyError, json.JSONDecodeError) as erro:
        raise ErroTrocaGoogle(str(erro)) from erro
