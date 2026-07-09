import os
import sys
import tempfile
import uuid
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# Banco de dados isolado por sessão de testes, criado antes de importar
# `database`/`main` (que leem DATABASE_URL na hora do import) — nunca toca
# no logjobs.db real usado em desenvolvimento/produção.
_TMP_DIR = tempfile.mkdtemp(prefix="logjobs-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP_DIR}/test_logjobs.db"
os.environ["LOGJOBS_SECRET_KEY"] = "test-secret-key-nao-usar-em-producao"
os.environ["ADMIN_TOKEN"] = "test-admin-token"
os.environ.pop("JOOBLE_API_KEY", None)
os.environ.pop("GOOGLE_CLIENT_ID", None)
os.environ.pop("GOOGLE_CLIENT_SECRET", None)

import pytest
from fastapi.testclient import TestClient

import rate_limit
from main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def _sem_rate_limit_entre_testes():
    """O limitador de pedidos é por IP e o TestClient usa sempre o mesmo IP —
    sem isso, testes sem relação nenhuma entre si esbarrariam no limite um do
    outro. O rate limit em si tem seu próprio teste dedicado (veja test_api.py)."""
    rate_limit._registros.clear()
    yield
    rate_limit._registros.clear()


@pytest.fixture()
def email_unico():
    """E-mail único por teste — os testes compartilham um único banco (mesma
    sessão), então cada teste que cria usuário precisa do seu próprio e-mail."""
    return f"teste.{uuid.uuid4().hex[:12]}@exemplo.com"


@pytest.fixture()
def usuario_registrado(client, email_unico):
    """Registra um candidato novo e devolve (tokens, dados) prontos para uso."""
    resposta = client.post(
        "/api/auth/registro",
        json={"nome": "Usuário de Teste", "email": email_unico, "senha": "senha123456", "tipo": "candidato"},
    )
    assert resposta.status_code == 201
    return resposta.json()
