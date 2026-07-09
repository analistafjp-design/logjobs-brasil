"""Testes do chat: iniciar conversa (candidato→empresa e empresa→candidato), listar, enviar, WebSocket."""
import uuid


def _criar_empresa(client):
    sufixo = uuid.uuid4().hex[:10]
    email = f"empresa.{sufixo}@exemplo.com"
    resposta = client.post(
        "/api/auth/registro",
        json={"nome": f"Empresa Teste {sufixo}", "email": email, "senha": "senha123456", "tipo": "empresa"},
    )
    return resposta.json()


def _criar_candidato(client):
    email = f"candidato.{uuid.uuid4().hex[:10]}@exemplo.com"
    resposta = client.post(
        "/api/auth/registro",
        json={"nome": "Candidato Teste", "email": email, "senha": "senha123456", "tipo": "candidato"},
    )
    return resposta.json()


def _cabecalho(usuario):
    return {"Authorization": f"Bearer {usuario['access_token']}"}


def _criar_vaga_da_empresa(client, empresa):
    sufixo = uuid.uuid4().hex[:10]
    resposta = client.post(
        "/api/empresa/vagas",
        headers=_cabecalho(empresa),
        json={
            "cargo": f"Motorista Categoria D {sufixo}",
            "empresa": empresa["usuario"]["nome"],
            "cidade": "São Paulo",
            "estado": "SP",
            "categoria": "Motorista",
        },
    )
    assert resposta.status_code == 201
    return resposta.json()


def test_candidato_inicia_conversa_a_partir_da_vaga(client):
    empresa = _criar_empresa(client)
    candidato = _criar_candidato(client)
    vaga = _criar_vaga_da_empresa(client, empresa)

    resposta = client.post(
        "/api/chat/conversas",
        headers=_cabecalho(candidato),
        json={"vaga_id": vaga["id"], "mensagem": "Olá, tenho interesse na vaga!"},
    )
    assert resposta.status_code == 201
    dados = resposta.json()
    assert dados["mensagem"]["texto"] == "Olá, tenho interesse na vaga!"
    assert dados["mensagem"]["de_mim"] is True

    conversas_empresa = client.get("/api/chat/conversas", headers=_cabecalho(empresa)).json()
    assert len(conversas_empresa) == 1
    assert conversas_empresa[0]["outro_usuario"]["nome"] == "Candidato Teste"
    assert conversas_empresa[0]["nao_lidas"] == 1


def test_conversa_e_reaproveitada_para_o_mesmo_par(client):
    empresa = _criar_empresa(client)
    candidato = _criar_candidato(client)
    vaga = _criar_vaga_da_empresa(client, empresa)

    r1 = client.post(
        "/api/chat/conversas", headers=_cabecalho(candidato), json={"vaga_id": vaga["id"], "mensagem": "Primeira mensagem"}
    )
    r2 = client.post(
        "/api/chat/conversas", headers=_cabecalho(candidato), json={"vaga_id": vaga["id"], "mensagem": "Segunda mensagem"}
    )
    assert r1.json()["conversa_id"] == r2.json()["conversa_id"]

    mensagens = client.get(
        f"/api/chat/conversas/{r1.json()['conversa_id']}/mensagens", headers=_cabecalho(candidato)
    ).json()["mensagens"]
    assert len(mensagens) == 2


def test_candidato_sem_vaga_id_falha(client):
    candidato = _criar_candidato(client)
    resposta = client.post("/api/chat/conversas", headers=_cabecalho(candidato), json={"mensagem": "oi"})
    assert resposta.status_code == 400


def test_vaga_sem_empresa_dona_nao_permite_chat(client):
    candidato = _criar_candidato(client)
    sufixo = uuid.uuid4().hex[:10]
    vaga_admin = client.post(
        "/api/admin/vagas",
        headers={"X-Admin-Token": "test-admin-token"},
        json={
            "cargo": f"Vaga sem dono {sufixo}",
            "empresa": "Empresa Externa",
            "cidade": "Curitiba",
            "estado": "PR",
            "categoria": "Estoquista",
        },
    ).json()

    resposta = client.post(
        "/api/chat/conversas", headers=_cabecalho(candidato), json={"vaga_id": vaga_admin["id"], "mensagem": "oi"}
    )
    assert resposta.status_code == 400


def test_empresa_inicia_conversa_a_partir_de_candidatura(client):
    empresa = _criar_empresa(client)
    candidato = _criar_candidato(client)
    vaga = _criar_vaga_da_empresa(client, empresa)

    candidatura = client.post(
        "/api/candidaturas",
        json={
            "vaga_id": vaga["id"],
            "nome": candidato["usuario"]["nome"],
            "email": candidato["usuario"]["email"],
        },
    )
    assert candidatura.status_code == 200
    candidatura_id = candidatura.json()["id"]

    resposta = client.post(
        "/api/chat/conversas",
        headers=_cabecalho(empresa),
        json={"candidatura_id": candidatura_id, "mensagem": "Vamos agendar uma entrevista?"},
    )
    assert resposta.status_code == 201

    conversas_candidato = client.get("/api/chat/conversas", headers=_cabecalho(candidato)).json()
    assert len(conversas_candidato) == 1
    assert conversas_candidato[0]["vaga"]["cargo"] == vaga["cargo"]


def test_empresa_candidatura_sem_conta_correspondente_falha(client):
    empresa = _criar_empresa(client)
    vaga = _criar_vaga_da_empresa(client, empresa)

    candidatura = client.post(
        "/api/candidaturas",
        json={"vaga_id": vaga["id"], "nome": "Anônimo", "email": f"sem-conta.{uuid.uuid4().hex[:8]}@exemplo.com"},
    )
    candidatura_id = candidatura.json()["id"]

    resposta = client.post(
        "/api/chat/conversas",
        headers=_cabecalho(empresa),
        json={"candidatura_id": candidatura_id, "mensagem": "oi"},
    )
    assert resposta.status_code == 404


def test_participante_fora_da_conversa_nao_acessa(client):
    empresa = _criar_empresa(client)
    candidato = _criar_candidato(client)
    intruso = _criar_candidato(client)
    vaga = _criar_vaga_da_empresa(client, empresa)

    conversa_id = client.post(
        "/api/chat/conversas", headers=_cabecalho(candidato), json={"vaga_id": vaga["id"], "mensagem": "oi"}
    ).json()["conversa_id"]

    resposta = client.get(f"/api/chat/conversas/{conversa_id}/mensagens", headers=_cabecalho(intruso))
    assert resposta.status_code == 404

    envio = client.post(
        f"/api/chat/conversas/{conversa_id}/mensagens", headers=_cabecalho(intruso), json={"texto": "invasão"}
    )
    assert envio.status_code == 404


def test_enviar_mensagem_marca_como_nao_lida_para_o_outro(client):
    empresa = _criar_empresa(client)
    candidato = _criar_candidato(client)
    vaga = _criar_vaga_da_empresa(client, empresa)

    conversa_id = client.post(
        "/api/chat/conversas", headers=_cabecalho(candidato), json={"vaga_id": vaga["id"], "mensagem": "oi"}
    ).json()["conversa_id"]

    envio = client.post(
        f"/api/chat/conversas/{conversa_id}/mensagens", headers=_cabecalho(empresa), json={"texto": "Podemos conversar?"}
    )
    assert envio.status_code == 201

    lista_candidato = client.get("/api/chat/conversas", headers=_cabecalho(candidato)).json()
    assert lista_candidato[0]["nao_lidas"] == 1

    # abrir as mensagens marca como lidas
    client.get(f"/api/chat/conversas/{conversa_id}/mensagens", headers=_cabecalho(candidato))
    lista_depois = client.get("/api/chat/conversas", headers=_cabecalho(candidato)).json()
    assert lista_depois[0]["nao_lidas"] == 0


def test_websocket_recebe_mensagem_em_tempo_real(client):
    empresa = _criar_empresa(client)
    candidato = _criar_candidato(client)
    vaga = _criar_vaga_da_empresa(client, empresa)

    conversa_id = client.post(
        "/api/chat/conversas", headers=_cabecalho(candidato), json={"vaga_id": vaga["id"], "mensagem": "oi"}
    ).json()["conversa_id"]

    with client.websocket_connect(f"/ws/chat/{conversa_id}?token={empresa['access_token']}") as ws:
        client.post(
            f"/api/chat/conversas/{conversa_id}/mensagens",
            headers=_cabecalho(candidato),
            json={"texto": "Mensagem em tempo real"},
        )
        recebida = ws.receive_json()
        assert recebida["texto"] == "Mensagem em tempo real"


def test_websocket_token_invalido_e_recusado(client):
    empresa = _criar_empresa(client)
    candidato = _criar_candidato(client)
    vaga = _criar_vaga_da_empresa(client, empresa)
    conversa_id = client.post(
        "/api/chat/conversas", headers=_cabecalho(candidato), json={"vaga_id": vaga["id"], "mensagem": "oi"}
    ).json()["conversa_id"]

    from starlette.websockets import WebSocketDisconnect
    try:
        with client.websocket_connect(f"/ws/chat/{conversa_id}?token=invalido"):
            assert False, "deveria ter recusado a conexão"
    except WebSocketDisconnect:
        pass


def test_websocket_usuario_nao_participante_e_recusado(client):
    empresa = _criar_empresa(client)
    candidato = _criar_candidato(client)
    intruso = _criar_candidato(client)
    vaga = _criar_vaga_da_empresa(client, empresa)
    conversa_id = client.post(
        "/api/chat/conversas", headers=_cabecalho(candidato), json={"vaga_id": vaga["id"], "mensagem": "oi"}
    ).json()["conversa_id"]

    from starlette.websockets import WebSocketDisconnect
    try:
        with client.websocket_connect(f"/ws/chat/{conversa_id}?token={intruso['access_token']}"):
            assert False, "deveria ter recusado a conexão"
    except WebSocketDisconnect:
        pass
