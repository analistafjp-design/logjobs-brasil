"""Testes dos endpoints públicos principais: vagas, estatísticas, favoritos e proteção do admin."""

import uuid


def test_rate_limit_bloqueia_apos_muitas_tentativas(client):
    for _ in range(10):
        client.post(
            "/api/auth/login",
            json={"email": f"{uuid.uuid4().hex}@exemplo.com", "senha": "qualquer"},
        )
    bloqueado = client.post(
        "/api/auth/login", json={"email": f"{uuid.uuid4().hex}@exemplo.com", "senha": "qualquer"}
    )
    assert bloqueado.status_code == 429


def test_health(client):
    resposta = client.get("/health")
    assert resposta.status_code == 200
    assert resposta.json() == {"status": "ok"}


def test_estatisticas_retorna_contadores(client):
    resposta = client.get("/api/estatisticas")
    assert resposta.status_code == 200
    dados = resposta.json()
    assert set(dados.keys()) == {"vagas", "empresas", "cidades"}
    assert isinstance(dados["vagas"], int)


def test_listar_vagas_formato_padrao(client):
    resposta = client.get("/api/vagas")
    assert resposta.status_code == 200
    dados = resposta.json()
    assert "vagas" in dados
    assert "total" in dados
    assert isinstance(dados["vagas"], list)


def test_listar_vagas_filtro_cidade_inexistente_retorna_vazio(client):
    resposta = client.get("/api/vagas", params={"cidade": "CidadeQueNaoExisteXYZ123"})
    assert resposta.status_code == 200
    assert resposta.json()["vagas"] == []
    assert resposta.json()["total"] == 0


def test_vaga_inexistente_retorna_404(client):
    resposta = client.get("/api/vagas/99999999")
    assert resposta.status_code == 404


def test_dashboard_estrutura_basica(client):
    resposta = client.get("/api/dashboard")
    assert resposta.status_code == 200
    dados = resposta.json()
    for chave in ("por_categoria", "por_estado", "top_empresas", "salario_por_categoria", "evolucao"):
        assert chave in dados


def test_blog_lista_artigos(client):
    resposta = client.get("/api/blog")
    assert resposta.status_code == 200
    assert isinstance(resposta.json(), list)


def test_ranking_retorna_lista(client):
    resposta = client.get("/api/ranking")
    assert resposta.status_code == 200


def test_favoritos_sem_login_falha(client):
    resposta = client.get("/api/favoritos")
    assert resposta.status_code == 401


def test_favoritar_e_desfavoritar_vaga(client, usuario_registrado):
    token = usuario_registrado["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    vagas = client.get("/api/vagas").json()["vagas"]
    if not vagas:
        return  # ambiente sem vagas seedadas — nada a testar aqui
    vaga_id = vagas[0]["id"]

    favoritar = client.post(f"/api/favoritos/{vaga_id}", headers=headers)
    assert favoritar.status_code == 201

    lista = client.get("/api/favoritos", headers=headers).json()
    assert any(v["id"] == vaga_id for v in lista["vagas"])

    desfavoritar = client.delete(f"/api/favoritos/{vaga_id}", headers=headers)
    assert desfavoritar.status_code == 200

    lista_depois = client.get("/api/favoritos", headers=headers).json()
    assert not any(v["id"] == vaga_id for v in lista_depois["vagas"])


def test_candidatura_honeypot_bloqueia_bot(client):
    vagas = client.get("/api/vagas").json()["vagas"]
    if not vagas:
        return
    resposta = client.post(
        "/api/candidaturas",
        json={
            "vaga_id": vagas[0]["id"],
            "nome": "Bot",
            "email": "bot@exemplo.com",
            "empresa_no_meio": "preenchido-por-um-bot",
        },
    )
    assert resposta.status_code == 400


def test_admin_sem_token_e_negado(client):
    assert client.get("/api/admin/verificar").status_code == 403


def test_admin_com_token_errado_e_negado(client):
    resposta = client.get("/api/admin/verificar", headers={"X-Admin-Token": "token-errado"})
    assert resposta.status_code == 403


def test_admin_com_token_correto_e_autorizado(client):
    resposta = client.get("/api/admin/verificar", headers={"X-Admin-Token": "test-admin-token"})
    assert resposta.status_code == 200
    assert resposta.json() == {"ok": True}


def test_admin_criar_vaga_com_campos_muito_longos_e_rejeitado(client):
    resposta = client.post(
        "/api/admin/vagas",
        headers={"X-Admin-Token": "test-admin-token"},
        json={
            "cargo": "x" * 500,
            "empresa": "Empresa Teste",
            "cidade": "São Paulo",
            "estado": "SP",
            "categoria": "Motorista",
        },
    )
    assert resposta.status_code == 422
