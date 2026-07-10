"""Testes dos recursos de IA sob demanda: análise de perfil, gerador de currículo,
simulador de entrevista e assistente virtual (todos determinísticos)."""
import uuid


def _criar_candidato(client, **extra):
    email = f"ia.{uuid.uuid4().hex[:10]}@exemplo.com"
    resposta = client.post(
        "/api/auth/registro",
        json={"nome": "Candidato IA", "email": email, "senha": "senha123456", "tipo": "candidato"},
    )
    usuario = resposta.json()
    if extra:
        client.patch(
            "/api/auth/me", json=extra, headers={"Authorization": f"Bearer {usuario['access_token']}"}
        )
    return usuario


def _criar_empresa(client):
    email = f"ia.empresa.{uuid.uuid4().hex[:10]}@exemplo.com"
    resposta = client.post(
        "/api/auth/registro",
        json={"nome": "Empresa IA", "email": email, "senha": "senha123456", "tipo": "empresa"},
    )
    return resposta.json()


def _cabecalho(usuario):
    return {"Authorization": f"Bearer {usuario['access_token']}"}


def test_analise_perfil_incompleto_traz_sugestoes(client):
    candidato = _criar_candidato(client)
    resposta = client.get("/api/ia/analise-perfil", headers=_cabecalho(candidato))
    assert resposta.status_code == 200
    dados = resposta.json()
    assert dados["completude"] == 0
    assert len(dados["sugestoes"]) > 0
    assert dados["pontos_fortes"] == []


def test_analise_perfil_completo_traz_pontos_fortes(client):
    candidato = _criar_candidato(
        client,
        resumo="Motorista com 10 anos de experiência em transporte de cargas pesadas por todo o Brasil, sempre pontual.",
        habilidades="Direção defensiva, CNH E, Logística reversa",
        possui_cnh="E",
        disponibilidade="Imediata",
        linkedin_url="https://linkedin.com/in/teste",
        experiencias=[{"cargo": "Motorista", "empresa": "Transportadora X", "descricao": "Entregas regionais"}],
        formacoes=[{"curso": "Técnico em Logística", "instituicao": "Escola Y"}],
        idiomas=[{"idioma": "Português", "nivel": "Nativo"}],
    )
    resposta = client.get("/api/ia/analise-perfil", headers=_cabecalho(candidato))
    dados = resposta.json()
    assert dados["completude"] > 50
    assert any("experiência" in p for p in dados["pontos_fortes"])


def test_analise_perfil_recusa_empresa(client):
    empresa = _criar_empresa(client)
    resposta = client.get("/api/ia/analise-perfil", headers=_cabecalho(empresa))
    assert resposta.status_code == 403


def test_analise_perfil_sem_login_falha(client):
    resposta = client.get("/api/ia/analise-perfil")
    assert resposta.status_code == 401


def test_gerar_curriculo_contem_nome_e_secoes(client):
    candidato = _criar_candidato(
        client,
        resumo="Entregador dedicado e pontual.",
        habilidades="Moto própria, Conhecimento de rotas",
        experiencias=[{"cargo": "Entregador", "empresa": "Loggi", "descricao": "Entregas expressas"}],
    )
    resposta = client.get("/api/ia/gerar-curriculo", headers=_cabecalho(candidato))
    assert resposta.status_code == 200
    texto = resposta.text
    assert "CANDIDATO IA" in texto
    assert "RESUMO PROFISSIONAL" in texto
    assert "EXPERIÊNCIA PROFISSIONAL" in texto
    assert "Entregador" in texto


def test_gerar_curriculo_recusa_empresa(client):
    empresa = _criar_empresa(client)
    resposta = client.get("/api/ia/gerar-curriculo", headers=_cabecalho(empresa))
    assert resposta.status_code == 403


def test_simulador_entrevista_traz_perguntas(client):
    candidato = _criar_candidato(client)
    resposta = client.get(
        "/api/ia/simulador-entrevista", params={"categoria": "Motorista", "quantidade": 3}, headers=_cabecalho(candidato)
    )
    assert resposta.status_code == 200
    dados = resposta.json()
    assert len(dados["perguntas"]) == 3
    assert dados["dica"]


def test_simulador_entrevista_sem_categoria_usa_comportamentais(client):
    candidato = _criar_candidato(client)
    resposta = client.get("/api/ia/simulador-entrevista", headers=_cabecalho(candidato))
    assert resposta.status_code == 200
    assert len(resposta.json()["perguntas"]) == 5


def test_simulador_entrevista_categorias_disponiveis(client):
    resposta = client.get("/api/ia/simulador-entrevista/categorias")
    assert resposta.status_code == 200
    assert "Motorista" in resposta.json()["categorias"]


def test_assistente_reconhece_pergunta_sobre_candidatura(client):
    resposta = client.post("/api/ia/assistente", json={"pergunta": "Como faço para me candidatar a uma vaga?"})
    assert resposta.status_code == 200
    dados = resposta.json()
    assert dados["encontrou"] is True
    assert "candidatar" in dados["resposta"].lower()


def test_assistente_pergunta_desconhecida_traz_resposta_padrao(client):
    resposta = client.post("/api/ia/assistente", json={"pergunta": "qual é a capital da frança"})
    assert resposta.status_code == 200
    assert resposta.json()["encontrou"] is False


def test_assistente_responde_agradecimento(client):
    resposta = client.post("/api/ia/assistente", json={"pergunta": "Ok, obrigado!"})
    assert resposta.status_code == 200
    dados = resposta.json()
    assert dados["encontrou"] is True
    assert "de nada" in dados["resposta"].lower()


def test_assistente_responde_saudacao(client):
    resposta = client.post("/api/ia/assistente", json={"pergunta": "oi"})
    assert resposta.status_code == 200
    assert resposta.json()["encontrou"] is True


def test_assistente_nao_confunde_palavra_parecida_com_chat(client):
    """'chateado' não deveria disparar a intenção de chat (correspondência por palavra inteira, não substring)."""
    resposta = client.post("/api/ia/assistente", json={"pergunta": "Estou meio chateado com a demora da resposta"})
    assert resposta.status_code == 200
    assert resposta.json()["encontrou"] is False


def test_assistente_nao_confunde_ola_com_escola(client):
    """'escola' não deveria disparar a saudação 'olá' (correspondência por palavra inteira, não substring)."""
    resposta = client.post("/api/ia/assistente", json={"pergunta": "fiz um curso técnico numa escola de logística"})
    assert resposta.status_code == 200
    assert resposta.json()["encontrou"] is False


def test_assistente_reconhece_plural(client):
    """'vagas' (plural) deve casar com a intenção de 'vaga'."""
    resposta = client.post("/api/ia/assistente", json={"pergunta": "vagas"})
    assert resposta.status_code == 200
    assert resposta.json()["encontrou"] is True


def test_assistente_reconhece_categoria_de_vaga(client):
    resposta = client.post("/api/ia/assistente", json={"pergunta": "entregador"})
    assert resposta.status_code == 200
    dados = resposta.json()
    assert dados["encontrou"] is True
    assert "categoria" in dados["resposta"].lower()


def test_assistente_rate_limit(client):
    for _ in range(30):
        client.post("/api/ia/assistente", json={"pergunta": "oi"})
    bloqueado = client.post("/api/ia/assistente", json={"pergunta": "oi"})
    assert bloqueado.status_code == 429
