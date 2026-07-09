"""Testes do fluxo de autenticação: registro, login, refresh token, logout e 2FA."""


def test_registro_cria_usuario_e_devolve_tokens(client, email_unico):
    resposta = client.post(
        "/api/auth/registro",
        json={"nome": "Ana Teste", "email": email_unico, "senha": "senha123456", "tipo": "candidato"},
    )
    assert resposta.status_code == 201
    dados = resposta.json()
    assert dados["access_token"]
    assert dados["refresh_token"]
    assert dados["usuario"]["email"] == email_unico
    assert dados["usuario"]["tipo"] == "candidato"


def test_registro_email_duplicado_falha(client, email_unico):
    corpo = {"nome": "Ana", "email": email_unico, "senha": "senha123456", "tipo": "candidato"}
    assert client.post("/api/auth/registro", json=corpo).status_code == 201
    resposta_duplicada = client.post("/api/auth/registro", json=corpo)
    assert resposta_duplicada.status_code == 400


def test_registro_senha_curta_falha_com_mensagem_amigavel(client, email_unico):
    resposta = client.post(
        "/api/auth/registro",
        json={"nome": "Ana", "email": email_unico, "senha": "123", "tipo": "candidato"},
    )
    assert resposta.status_code == 400
    assert isinstance(resposta.json()["detail"], str)
    assert "senha" in resposta.json()["detail"].lower()


def test_registro_tipo_invalido_falha(client, email_unico):
    resposta = client.post(
        "/api/auth/registro",
        json={"nome": "Ana", "email": email_unico, "senha": "senha123456", "tipo": "hacker"},
    )
    assert resposta.status_code == 400


def test_login_com_credenciais_corretas(client, usuario_registrado):
    email = usuario_registrado["usuario"]["email"]
    resposta = client.post("/api/auth/login", json={"email": email, "senha": "senha123456"})
    assert resposta.status_code == 200
    dados = resposta.json()
    assert dados["access_token"]
    assert dados["refresh_token"]


def test_login_com_senha_errada_falha(client, usuario_registrado):
    email = usuario_registrado["usuario"]["email"]
    resposta = client.post("/api/auth/login", json={"email": email, "senha": "senha-errada"})
    assert resposta.status_code == 401


def test_login_email_inexistente_falha(client):
    resposta = client.post("/api/auth/login", json={"email": "ninguem@exemplo.com", "senha": "qualquer"})
    assert resposta.status_code == 401


def test_me_com_token_valido(client, usuario_registrado):
    token = usuario_registrado["access_token"]
    resposta = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resposta.status_code == 200
    assert resposta.json()["email"] == usuario_registrado["usuario"]["email"]


def test_me_sem_token_falha(client):
    resposta = client.get("/api/auth/me")
    assert resposta.status_code == 401


def test_me_com_token_invalido_falha(client):
    resposta = client.get("/api/auth/me", headers={"Authorization": "Bearer token-invalido"})
    assert resposta.status_code == 401


def test_refresh_rotaciona_tokens_e_invalida_o_antigo(client, usuario_registrado):
    refresh_token = usuario_registrado["refresh_token"]

    resposta = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert resposta.status_code == 200
    novos = resposta.json()
    assert novos["access_token"] != usuario_registrado["access_token"]
    assert novos["refresh_token"] != refresh_token

    # o refresh token antigo já foi consumido (rotação de uso único) — reusar falha
    reuso = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert reuso.status_code == 401

    # mas o novo token de acesso funciona normalmente
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {novos['access_token']}"})
    assert me.status_code == 200


def test_refresh_com_token_invalido_falha(client):
    resposta = client.post("/api/auth/refresh", json={"refresh_token": "token-que-nao-existe"})
    assert resposta.status_code == 401


def test_logout_revoga_refresh_token(client, usuario_registrado):
    refresh_token = usuario_registrado["refresh_token"]

    logout = client.post("/api/auth/logout", json={"refresh_token": refresh_token})
    assert logout.status_code == 204

    resposta = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert resposta.status_code == 401


def test_logout_com_token_ja_invalido_nao_quebra(client):
    """Logout deve ser idempotente/silencioso mesmo com um token que nunca existiu."""
    resposta = client.post("/api/auth/logout", json={"refresh_token": "nunca-existiu"})
    assert resposta.status_code == 204


def test_ativar_2fa_exige_login_com_codigo_depois(client, email_unico):
    registro = client.post(
        "/api/auth/registro",
        json={"nome": "Beto 2FA", "email": email_unico, "senha": "senha123456", "tipo": "candidato"},
    ).json()
    token = registro["access_token"]

    iniciar = client.post("/api/auth/2fa/iniciar", headers={"Authorization": f"Bearer {token}"})
    assert iniciar.status_code == 200
    segredo = iniciar.json()["segredo"]

    import time as time_module
    import totp

    def codigo_atual():
        contador = int(time_module.time() // totp.PERIODO_SEGUNDOS)
        return totp._hotp(segredo, contador)

    confirmar = client.post(
        "/api/auth/2fa/confirmar", json={"codigo": codigo_atual()}, headers={"Authorization": f"Bearer {token}"}
    )
    assert confirmar.status_code == 200

    login_sem_codigo = client.post("/api/auth/login", json={"email": email_unico, "senha": "senha123456"})
    assert login_sem_codigo.status_code == 200
    assert login_sem_codigo.json().get("requer_totp") is True

    login_com_codigo = client.post(
        "/api/auth/login",
        json={"email": email_unico, "senha": "senha123456", "codigo_totp": codigo_atual()},
    )
    assert login_com_codigo.status_code == 200
    assert login_com_codigo.json()["access_token"]


def test_atualizar_perfil_empresa_logo_e_redes_sociais(client, email_unico):
    registro = client.post(
        "/api/auth/registro",
        json={"nome": "Transportadora Teste", "email": email_unico, "senha": "senha123456", "tipo": "empresa"},
    ).json()
    token = registro["access_token"]

    resposta = client.patch(
        "/api/auth/me",
        json={
            "logo_url": "https://exemplo.com/logo.png",
            "site_url": "https://exemplo.com",
            "instagram_url": "https://instagram.com/transportadorateste",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resposta.status_code == 200
    dados = resposta.json()
    assert dados["logo_url"] == "https://exemplo.com/logo.png"
    assert dados["site_url"] == "https://exemplo.com"
    assert dados["instagram_url"] == "https://instagram.com/transportadorateste"


def test_exportar_meus_dados(client, usuario_registrado):
    token = usuario_registrado["access_token"]
    resposta = client.get("/api/auth/meus-dados", headers={"Authorization": f"Bearer {token}"})
    assert resposta.status_code == 200
    dados = resposta.json()
    assert dados["perfil"]["email"] == usuario_registrado["usuario"]["email"]
    assert dados["favoritos"] == []
    assert dados["alertas"] == []
    assert dados["candidaturas"] == []


def test_excluir_conta_com_senha_errada_falha(client, usuario_registrado):
    token = usuario_registrado["access_token"]
    resposta = client.request(
        "DELETE", "/api/auth/me", json={"senha": "senha-errada"}, headers={"Authorization": f"Bearer {token}"}
    )
    assert resposta.status_code == 401


def test_excluir_conta_com_senha_correta_apaga_e_revoga_sessao(client, usuario_registrado):
    token = usuario_registrado["access_token"]
    refresh_token = usuario_registrado["refresh_token"]

    resposta = client.request(
        "DELETE", "/api/auth/me", json={"senha": "senha123456"}, headers={"Authorization": f"Bearer {token}"}
    )
    assert resposta.status_code == 204

    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401
    assert client.post("/api/auth/refresh", json={"refresh_token": refresh_token}).status_code == 401
