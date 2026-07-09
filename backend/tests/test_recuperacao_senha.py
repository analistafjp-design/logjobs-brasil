"""Testes do fluxo de recuperação de senha. O envio real de e-mail é substituído
por um stub (monkeypatch) — não depende de nenhum servidor SMTP de verdade."""
import uuid

import email_sender


def _criar_candidato(client):
    email = f"recuperar.{uuid.uuid4().hex[:10]}@exemplo.com"
    resposta = client.post(
        "/api/auth/registro",
        json={"nome": "Candidato Recuperação", "email": email, "senha": "senha123456", "tipo": "candidato"},
    )
    return resposta.json()


def test_configurado_reflete_smtp(client, monkeypatch):
    monkeypatch.setattr(email_sender, "SMTP_HOST", None)
    assert client.get("/api/auth/recuperar-senha/configurado").json() == {"configurado": False}

    monkeypatch.setattr(email_sender, "SMTP_HOST", "smtp.exemplo.com")
    monkeypatch.setattr(email_sender, "SMTP_USER", "usuario")
    monkeypatch.setattr(email_sender, "SMTP_PASSWORD", "senha")
    assert client.get("/api/auth/recuperar-senha/configurado").json() == {"configurado": True}


def test_recuperar_senha_sem_smtp_configurado_falha(client, monkeypatch):
    monkeypatch.setattr(email_sender, "SMTP_HOST", None)
    resposta = client.post("/api/auth/recuperar-senha", json={"email": "qualquer@exemplo.com"})
    assert resposta.status_code == 503


def test_fluxo_completo_recuperacao_de_senha(client, monkeypatch):
    monkeypatch.setattr(email_sender, "SMTP_HOST", "smtp.exemplo.com")
    monkeypatch.setattr(email_sender, "SMTP_USER", "usuario")
    monkeypatch.setattr(email_sender, "SMTP_PASSWORD", "senha")

    emails_enviados = []
    monkeypatch.setattr(
        email_sender, "enviar_email",
        lambda destinatario, assunto, corpo: emails_enviados.append((destinatario, assunto, corpo)),
    )

    candidato = _criar_candidato(client)
    email = candidato["usuario"]["email"]

    resposta = client.post("/api/auth/recuperar-senha", json={"email": email})
    assert resposta.status_code == 200
    assert len(emails_enviados) == 1
    destinatario, assunto, corpo = emails_enviados[0]
    assert destinatario == email
    assert "redefinir-senha.html?token=" in corpo

    token = corpo.split("token=")[1].split("\n")[0].strip()

    redefinir = client.post("/api/auth/redefinir-senha", json={"token": token, "nova_senha": "novaSenha123"})
    assert redefinir.status_code == 200

    login_com_senha_antiga = client.post("/api/auth/login", json={"email": email, "senha": "senha123456"})
    assert login_com_senha_antiga.status_code == 401

    login_com_senha_nova = client.post("/api/auth/login", json={"email": email, "senha": "novaSenha123"})
    assert login_com_senha_nova.status_code == 200


def test_token_recuperacao_e_uso_unico(client, monkeypatch):
    monkeypatch.setattr(email_sender, "SMTP_HOST", "smtp.exemplo.com")
    monkeypatch.setattr(email_sender, "SMTP_USER", "usuario")
    monkeypatch.setattr(email_sender, "SMTP_PASSWORD", "senha")

    emails_enviados = []
    monkeypatch.setattr(
        email_sender, "enviar_email",
        lambda destinatario, assunto, corpo: emails_enviados.append((destinatario, assunto, corpo)),
    )

    candidato = _criar_candidato(client)
    client.post("/api/auth/recuperar-senha", json={"email": candidato["usuario"]["email"]})
    token = emails_enviados[0][2].split("token=")[1].split("\n")[0].strip()

    primeira_troca = client.post("/api/auth/redefinir-senha", json={"token": token, "nova_senha": "senhaUm12345"})
    assert primeira_troca.status_code == 200

    segunda_tentativa = client.post("/api/auth/redefinir-senha", json={"token": token, "nova_senha": "senhaDois12345"})
    assert segunda_tentativa.status_code == 401


def test_redefinir_com_token_invalido_falha(client):
    resposta = client.post("/api/auth/redefinir-senha", json={"token": "token-que-nao-existe", "nova_senha": "novaSenha123"})
    assert resposta.status_code == 401


def test_redefinir_senha_curta_falha(client, monkeypatch):
    monkeypatch.setattr(email_sender, "SMTP_HOST", "smtp.exemplo.com")
    monkeypatch.setattr(email_sender, "SMTP_USER", "usuario")
    monkeypatch.setattr(email_sender, "SMTP_PASSWORD", "senha")

    emails_enviados = []
    monkeypatch.setattr(
        email_sender, "enviar_email",
        lambda destinatario, assunto, corpo: emails_enviados.append((destinatario, assunto, corpo)),
    )

    candidato = _criar_candidato(client)
    client.post("/api/auth/recuperar-senha", json={"email": candidato["usuario"]["email"]})
    token = emails_enviados[0][2].split("token=")[1].split("\n")[0].strip()

    resposta = client.post("/api/auth/redefinir-senha", json={"token": token, "nova_senha": "123"})
    assert resposta.status_code == 400


def test_email_inexistente_nao_revela_se_existe_conta(client, monkeypatch):
    monkeypatch.setattr(email_sender, "SMTP_HOST", "smtp.exemplo.com")
    monkeypatch.setattr(email_sender, "SMTP_USER", "usuario")
    monkeypatch.setattr(email_sender, "SMTP_PASSWORD", "senha")

    resposta = client.post("/api/auth/recuperar-senha", json={"email": "ninguem-tem-essa-conta@exemplo.com"})
    assert resposta.status_code == 200
    assert "receber um link" in resposta.json()["mensagem"]


def test_redefinir_senha_revoga_sessoes_ativas(client, monkeypatch):
    monkeypatch.setattr(email_sender, "SMTP_HOST", "smtp.exemplo.com")
    monkeypatch.setattr(email_sender, "SMTP_USER", "usuario")
    monkeypatch.setattr(email_sender, "SMTP_PASSWORD", "senha")

    emails_enviados = []
    monkeypatch.setattr(
        email_sender, "enviar_email",
        lambda destinatario, assunto, corpo: emails_enviados.append((destinatario, assunto, corpo)),
    )

    candidato = _criar_candidato(client)
    refresh_token_antigo = candidato["refresh_token"]

    client.post("/api/auth/recuperar-senha", json={"email": candidato["usuario"]["email"]})
    token = emails_enviados[0][2].split("token=")[1].split("\n")[0].strip()
    client.post("/api/auth/redefinir-senha", json={"token": token, "nova_senha": "outraSenha123"})

    resposta = client.post("/api/auth/refresh", json={"refresh_token": refresh_token_antigo})
    assert resposta.status_code == 401
