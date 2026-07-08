import os
import secrets
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import auth
import security
from database import Base, SessionLocal, engine, get_db
from recomendacao import recomendar_vagas
from jooble_client import JOOBLE_API_KEY, buscar_vagas_todas_categorias
from migrations import adicionar_colunas_faltantes
from models import Atualizacao, Candidatura, Favorito, Interessado, Usuario, Vaga
from rate_limit import limitar_por_ip
from scheduler import (
    aplicar_correcao_geografica_uma_vez,
    atualizar_vagas_periodicamente,
    iniciar_agendador,
    parar_agendador,
    reclassificar_vagas_sem_categoria,
    remover_vagas_exemplo_se_ha_reais,
)
from seed_data import VAGAS_EXEMPLO
from seo import ROBOTS_TXT, pagina_404_html, pagina_sitemap_xml, pagina_vaga_html

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")


def verificar_admin(request: Request, x_admin_token: Optional[str] = Header(default=None)):
    limitar_por_ip(request, "admin", max_pedidos=30, janela_segundos=600)
    if not ADMIN_TOKEN or not x_admin_token or not secrets.compare_digest(x_admin_token, ADMIN_TOKEN):
        raise HTTPException(status_code=403, detail="Acesso negado")


Base.metadata.create_all(bind=engine)
adicionar_colunas_faltantes(engine, Base)

app = FastAPI(title="LogJobs Brasil")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def cabecalhos_seguranca(request: Request, call_next):
    resposta = await call_next(request)
    resposta.headers["X-Content-Type-Options"] = "nosniff"
    resposta.headers["X-Frame-Options"] = "DENY"
    resposta.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    resposta.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
    resposta.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'"
    )
    return resposta


@app.exception_handler(404)
async def pagina_nao_encontrada(request: Request, exc: HTTPException):
    if request.url.path.startswith("/api/"):
        return JSONResponse(status_code=404, content={"detail": exc.detail})
    return HTMLResponse(status_code=404, content=pagina_404_html())


def popular_banco_se_vazio():
    db = SessionLocal()
    try:
        if db.query(Vaga).count() == 0:
            vagas_reais = buscar_vagas_todas_categorias()
            dados_iniciais = vagas_reais if vagas_reais else [
                {**dados, "fonte": "exemplo"} for dados in VAGAS_EXEMPLO
            ]

            for dados in dados_iniciais:
                db.add(Vaga(**dados))
                try:
                    db.commit()
                except IntegrityError:
                    # Outra instância pode ter populado o banco ao mesmo tempo.
                    db.rollback()
    finally:
        db.close()


@app.on_event("startup")
def on_startup():
    aplicar_correcao_geografica_uma_vez()
    popular_banco_se_vazio()
    remover_vagas_exemplo_se_ha_reais()
    reclassificar_vagas_sem_categoria()
    iniciar_agendador()


@app.on_event("shutdown")
def on_shutdown():
    parar_agendador()


@app.get("/api/vagas")
def listar_vagas(
    cargo: Optional[str] = None,
    cidade: Optional[str] = None,
    estado: Optional[str] = None,
    categoria: Optional[str] = None,
    salario_min: Optional[float] = None,
    limit: int = Query(default=20, le=100),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    query = db.query(Vaga)

    if cargo:
        query = query.filter(Vaga.cargo.ilike(f"%{cargo}%"))
    if cidade:
        query = query.filter(Vaga.cidade.ilike(f"%{cidade}%"))
    if estado:
        query = query.filter(Vaga.estado.ilike(f"%{estado}%"))
    if categoria:
        query = query.filter(Vaga.categoria.ilike(f"%{categoria}%"))
    if salario_min:
        query = query.filter(Vaga.salario >= salario_min)

    total = query.count()
    vagas = query.order_by(Vaga.id.desc()).offset(offset).limit(limit).all()

    return {
        "total": total,
        "vagas": [
            {
                "id": v.id,
                "cargo": v.cargo,
                "empresa": v.empresa,
                "cidade": v.cidade,
                "estado": v.estado,
                "salario": v.salario,
                "modalidade": v.modalidade,
                "veiculo": v.veiculo,
                "categoria": v.categoria,
                "link": v.link,
                "fonte": v.fonte,
            }
            for v in vagas
        ],
    }


@app.get("/api/vagas/{vaga_id}")
def obter_vaga(vaga_id: int, db: Session = Depends(get_db)):
    vaga = db.query(Vaga).filter(Vaga.id == vaga_id).first()
    if not vaga:
        raise HTTPException(status_code=404, detail="Vaga não encontrada")

    return {
        "id": vaga.id,
        "cargo": vaga.cargo,
        "empresa": vaga.empresa,
        "cidade": vaga.cidade,
        "estado": vaga.estado,
        "salario": vaga.salario,
        "modalidade": vaga.modalidade,
        "veiculo": vaga.veiculo,
        "categoria": vaga.categoria,
        "descricao": vaga.descricao,
        "beneficios": vaga.beneficios,
        "requisitos": vaga.requisitos,
        "link": vaga.link,
        "fonte": vaga.fonte,
    }


@app.get("/api/estatisticas")
def estatisticas(db: Session = Depends(get_db)):
    total_vagas = db.query(Vaga).count()
    total_empresas = db.query(func.count(func.distinct(Vaga.empresa))).scalar()
    total_cidades = db.query(func.count(func.distinct(Vaga.cidade))).scalar()

    return {
        "vagas": total_vagas,
        "empresas": total_empresas,
        "cidades": total_cidades,
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/ranking")
def ranking(db: Session = Depends(get_db)):
    por_vagas = (
        db.query(Vaga.empresa, func.count(Vaga.id).label("total"))
        .group_by(Vaga.empresa)
        .order_by(func.count(Vaga.id).desc())
        .limit(15)
        .all()
    )

    por_salario = (
        db.query(Vaga.empresa, func.avg(Vaga.salario).label("media"), func.count(Vaga.id).label("total"))
        .filter(Vaga.salario.isnot(None))
        .group_by(Vaga.empresa)
        .having(func.count(Vaga.id) >= 2)
        .order_by(func.avg(Vaga.salario).desc())
        .limit(15)
        .all()
    )

    return {
        "por_vagas": [{"empresa": e, "total": t} for e, t in por_vagas],
        "por_salario": [
            {"empresa": e, "salario_medio": round(m, 2), "total": t} for e, m, t in por_salario
        ],
    }


@app.get("/api/categorias")
def categorias(db: Session = Depends(get_db)):
    linhas = db.query(Vaga.categoria, func.count(Vaga.id)).group_by(Vaga.categoria).all()
    return [{"categoria": categoria, "total": total} for categoria, total in linhas]


@app.get("/api/dashboard")
def dashboard(db: Session = Depends(get_db)):
    por_categoria = (
        db.query(Vaga.categoria, func.count(Vaga.id))
        .group_by(Vaga.categoria)
        .order_by(func.count(Vaga.id).desc())
        .all()
    )

    por_estado = (
        db.query(Vaga.estado, func.count(Vaga.id))
        .group_by(Vaga.estado)
        .order_by(func.count(Vaga.id).desc())
        .all()
    )

    top_empresas = (
        db.query(Vaga.empresa, func.count(Vaga.id))
        .group_by(Vaga.empresa)
        .order_by(func.count(Vaga.id).desc())
        .limit(10)
        .all()
    )

    salario_por_categoria = (
        db.query(Vaga.categoria, func.avg(Vaga.salario))
        .filter(Vaga.salario.isnot(None))
        .group_by(Vaga.categoria)
        .order_by(func.avg(Vaga.salario).desc())
        .all()
    )

    evolucao = (
        db.query(Atualizacao)
        .order_by(Atualizacao.id.desc())
        .limit(30)
        .all()
    )

    return {
        "por_categoria": [{"categoria": c, "total": t} for c, t in por_categoria],
        "por_estado": [{"estado": e or "Não informado", "total": t} for e, t in por_estado],
        "top_empresas": [{"empresa": e, "total": t} for e, t in top_empresas],
        "salario_por_categoria": [
            {"categoria": c, "salario_medio": round(s, 2)} for c, s in salario_por_categoria
        ],
        "evolucao": [
            {
                "executada_em": a.executada_em.isoformat(),
                "vagas_novas": a.vagas_novas,
                "vagas_totais": a.vagas_totais,
            }
            for a in reversed(evolucao)
        ],
    }


@app.get("/api/status")
def status_atualizacao(db: Session = Depends(get_db)):
    ultima = db.query(Atualizacao).order_by(Atualizacao.id.desc()).first()
    total_por_fonte = dict(
        db.query(Vaga.fonte, func.count(Vaga.id)).group_by(Vaga.fonte).all()
    )

    return {
        "jooble_configurado": bool(JOOBLE_API_KEY),
        "intervalo_atualizacao_minutos": 20,
        "ultima_atualizacao": ultima.executada_em.isoformat() if ultima else None,
        "vagas_novas_na_ultima_atualizacao": ultima.vagas_novas if ultima else None,
        "vagas_por_fonte": total_por_fonte,
    }


@app.post("/api/atualizar-agora", dependencies=[Depends(verificar_admin)])
def forcar_atualizacao():
    atualizar_vagas_periodicamente()
    return {"mensagem": "Atualização executada."}


@app.get("/api/admin/verificar", dependencies=[Depends(verificar_admin)])
def admin_verificar():
    return {"ok": True}


class VagaEntrada(BaseModel):
    cargo: str
    empresa: str
    cidade: str
    estado: str
    categoria: str
    salario: Optional[float] = None
    modalidade: Optional[str] = None
    veiculo: Optional[str] = None
    descricao: Optional[str] = None
    beneficios: Optional[str] = None
    requisitos: Optional[str] = None
    link: Optional[str] = None


class VagaAtualizacao(BaseModel):
    cargo: Optional[str] = None
    empresa: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None
    categoria: Optional[str] = None
    salario: Optional[float] = None
    modalidade: Optional[str] = None
    veiculo: Optional[str] = None
    descricao: Optional[str] = None
    beneficios: Optional[str] = None
    requisitos: Optional[str] = None
    link: Optional[str] = None


def vaga_admin_para_json(v: Vaga) -> dict:
    return {
        "id": v.id,
        "cargo": v.cargo,
        "empresa": v.empresa,
        "cidade": v.cidade,
        "estado": v.estado,
        "salario": v.salario,
        "modalidade": v.modalidade,
        "veiculo": v.veiculo,
        "categoria": v.categoria,
        "descricao": v.descricao,
        "beneficios": v.beneficios,
        "requisitos": v.requisitos,
        "link": v.link,
        "fonte": v.fonte,
        "criada_em": v.criada_em.isoformat() if v.criada_em else None,
    }


@app.get("/api/admin/vagas", dependencies=[Depends(verificar_admin)])
def admin_listar_vagas(
    q: Optional[str] = None,
    limit: int = Query(default=50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    query = db.query(Vaga)
    if q:
        query = query.filter(
            (Vaga.cargo.ilike(f"%{q}%")) | (Vaga.empresa.ilike(f"%{q}%")) | (Vaga.cidade.ilike(f"%{q}%"))
        )
    total = query.count()
    vagas = query.order_by(Vaga.id.desc()).offset(offset).limit(limit).all()
    return {"total": total, "vagas": [vaga_admin_para_json(v) for v in vagas]}


@app.post("/api/admin/vagas", status_code=201, dependencies=[Depends(verificar_admin)])
def admin_criar_vaga(dados: VagaEntrada, db: Session = Depends(get_db)):
    vaga = Vaga(**dados.model_dump(), fonte="manual")
    db.add(vaga)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Já existe uma vaga com esse cargo, empresa e cidade")
    db.refresh(vaga)
    return vaga_admin_para_json(vaga)


@app.patch("/api/admin/vagas/{vaga_id}", dependencies=[Depends(verificar_admin)])
def admin_editar_vaga(vaga_id: int, dados: VagaAtualizacao, db: Session = Depends(get_db)):
    vaga = db.query(Vaga).filter(Vaga.id == vaga_id).first()
    if not vaga:
        raise HTTPException(status_code=404, detail="Vaga não encontrada")

    for campo, valor in dados.model_dump(exclude_unset=True).items():
        setattr(vaga, campo, valor)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Já existe uma vaga com esse cargo, empresa e cidade")
    db.refresh(vaga)
    return vaga_admin_para_json(vaga)


@app.delete("/api/admin/vagas/{vaga_id}", dependencies=[Depends(verificar_admin)])
def admin_excluir_vaga(vaga_id: int, db: Session = Depends(get_db)):
    vaga = db.query(Vaga).filter(Vaga.id == vaga_id).first()
    if not vaga:
        raise HTTPException(status_code=404, detail="Vaga não encontrada")
    db.delete(vaga)
    db.commit()
    return {"mensagem": "Vaga excluída"}


@app.get("/api/admin/candidaturas", dependencies=[Depends(verificar_admin)])
def admin_listar_candidaturas(limit: int = Query(default=50, le=200), db: Session = Depends(get_db)):
    candidaturas = db.query(Candidatura).order_by(Candidatura.id.desc()).limit(limit).all()
    vagas_por_id = {v.id: v for v in db.query(Vaga).filter(
        Vaga.id.in_([c.vaga_id for c in candidaturas])
    ).all()}

    return [
        {
            "id": c.id,
            "nome": c.nome,
            "email": c.email,
            "telefone": c.telefone,
            "vaga_id": c.vaga_id,
            "vaga_cargo": vagas_por_id[c.vaga_id].cargo if c.vaga_id in vagas_por_id else None,
            "vaga_empresa": vagas_por_id[c.vaga_id].empresa if c.vaga_id in vagas_por_id else None,
            "criada_em": c.criada_em.isoformat() if c.criada_em else None,
        }
        for c in candidaturas
    ]


@app.get("/api/admin/interessados", dependencies=[Depends(verificar_admin)])
def admin_listar_interessados(limit: int = Query(default=50, le=200), db: Session = Depends(get_db)):
    interessados = db.query(Interessado).order_by(Interessado.id.desc()).limit(limit).all()
    return [
        {
            "id": i.id,
            "nome": i.nome,
            "email": i.email,
            "tipo": i.tipo,
            "criado_em": i.criado_em.isoformat() if i.criado_em else None,
        }
        for i in interessados
    ]


@app.get("/api/admin/usuarios", dependencies=[Depends(verificar_admin)])
def admin_listar_usuarios(limit: int = Query(default=50, le=200), db: Session = Depends(get_db)):
    usuarios = db.query(Usuario).order_by(Usuario.id.desc()).limit(limit).all()
    return [
        {
            "id": u.id,
            "nome": u.nome,
            "email": u.email,
            "tipo": u.tipo,
            "cidade": u.cidade,
            "criado_em": u.criado_em.isoformat() if u.criado_em else None,
        }
        for u in usuarios
    ]


class CandidaturaEntrada(BaseModel):
    vaga_id: int
    nome: str
    email: EmailStr
    telefone: Optional[str] = None
    empresa_no_meio: Optional[str] = None  # honeypot: deve ficar vazio


@app.post("/api/candidaturas")
def criar_candidatura(dados: CandidaturaEntrada, request: Request, db: Session = Depends(get_db)):
    if dados.empresa_no_meio:
        raise HTTPException(status_code=400, detail="Requisição inválida")

    limitar_por_ip(request, "candidatura", max_pedidos=5, janela_segundos=600)

    vaga = db.query(Vaga).filter(Vaga.id == dados.vaga_id).first()
    if not vaga:
        raise HTTPException(status_code=404, detail="Vaga não encontrada")

    candidatura = Candidatura(
        vaga_id=dados.vaga_id,
        nome=dados.nome,
        email=dados.email,
        telefone=dados.telefone,
    )
    db.add(candidatura)
    db.commit()
    db.refresh(candidatura)

    return {"id": candidatura.id, "mensagem": "Candidatura enviada com sucesso!"}


class InteressadoEntrada(BaseModel):
    nome: str
    email: EmailStr
    tipo: str
    empresa_no_meio: Optional[str] = None  # honeypot: deve ficar vazio


@app.post("/api/interessados")
def criar_interessado(dados: InteressadoEntrada, request: Request, db: Session = Depends(get_db)):
    if dados.empresa_no_meio:
        raise HTTPException(status_code=400, detail="Requisição inválida")

    limitar_por_ip(request, "interessado", max_pedidos=5, janela_segundos=600)

    interessado = Interessado(nome=dados.nome, email=dados.email, tipo=dados.tipo)
    db.add(interessado)
    db.commit()
    db.refresh(interessado)

    return {"id": interessado.id, "mensagem": "Cadastro recebido! Avisaremos você em breve."}


class RegistroEntrada(BaseModel):
    nome: str
    email: EmailStr
    senha: str
    tipo: str = "candidato"


class LoginEntrada(BaseModel):
    email: EmailStr
    senha: str


class PerfilEntrada(BaseModel):
    nome: Optional[str] = None
    telefone: Optional[str] = None
    cidade: Optional[str] = None
    resumo: Optional[str] = None


def usuario_para_json(usuario: Usuario) -> dict:
    return {
        "id": usuario.id,
        "nome": usuario.nome,
        "email": usuario.email,
        "tipo": usuario.tipo,
        "telefone": usuario.telefone,
        "cidade": usuario.cidade,
        "resumo": usuario.resumo,
    }


@app.post("/api/auth/registro", status_code=201)
def registrar(dados: RegistroEntrada, request: Request, db: Session = Depends(get_db)):
    limitar_por_ip(request, "auth-registro", max_pedidos=10, janela_segundos=600)

    if len(dados.senha) < 6:
        raise HTTPException(status_code=400, detail="A senha precisa ter pelo menos 6 caracteres")
    if dados.tipo not in ("candidato", "empresa"):
        raise HTTPException(status_code=400, detail="Tipo de conta inválido")
    if db.query(Usuario).filter(Usuario.email == dados.email).first():
        raise HTTPException(status_code=400, detail="Este e-mail já está cadastrado")

    usuario = Usuario(
        nome=dados.nome,
        email=dados.email,
        senha_hash=security.hash_password(dados.senha),
        tipo=dados.tipo,
    )
    db.add(usuario)
    db.commit()
    db.refresh(usuario)

    token = auth.criar_token(usuario.id)
    return {"access_token": token, "usuario": usuario_para_json(usuario)}


@app.post("/api/auth/login")
def login(dados: LoginEntrada, request: Request, db: Session = Depends(get_db)):
    limitar_por_ip(request, "auth-login", max_pedidos=10, janela_segundos=600)

    usuario = db.query(Usuario).filter(Usuario.email == dados.email).first()
    if not usuario or not security.verify_password(dados.senha, usuario.senha_hash):
        raise HTTPException(status_code=401, detail="E-mail ou senha inválidos")

    token = auth.criar_token(usuario.id)
    return {"access_token": token, "usuario": usuario_para_json(usuario)}


@app.get("/api/auth/me")
def me(usuario: Usuario = Depends(auth.usuario_atual)):
    return usuario_para_json(usuario)


@app.patch("/api/auth/me")
def atualizar_perfil(
    dados: PerfilEntrada,
    usuario: Usuario = Depends(auth.usuario_atual),
    db: Session = Depends(get_db),
):
    if dados.nome is not None:
        nome = dados.nome.strip()
        if not nome:
            raise HTTPException(status_code=400, detail="Nome não pode ficar vazio")
        usuario.nome = nome
    if dados.telefone is not None:
        usuario.telefone = dados.telefone.strip() or None
    if dados.cidade is not None:
        usuario.cidade = dados.cidade.strip() or None
    if dados.resumo is not None:
        usuario.resumo = dados.resumo.strip() or None

    db.commit()
    db.refresh(usuario)
    return usuario_para_json(usuario)


@app.get("/api/favoritos")
def listar_favoritos(usuario: Usuario = Depends(auth.usuario_atual), db: Session = Depends(get_db)):
    ids_favoritos = [f.vaga_id for f in db.query(Favorito).filter(Favorito.usuario_id == usuario.id).all()]
    if not ids_favoritos:
        return {"vagas": []}

    vagas = db.query(Vaga).filter(Vaga.id.in_(ids_favoritos)).all()
    return {
        "vagas": [
            {
                "id": v.id,
                "cargo": v.cargo,
                "empresa": v.empresa,
                "cidade": v.cidade,
                "estado": v.estado,
                "salario": v.salario,
                "modalidade": v.modalidade,
                "categoria": v.categoria,
                "link": v.link,
            }
            for v in vagas
        ]
    }


@app.post("/api/favoritos/{vaga_id}", status_code=201)
def adicionar_favorito(vaga_id: int, usuario: Usuario = Depends(auth.usuario_atual), db: Session = Depends(get_db)):
    if not db.query(Vaga).filter(Vaga.id == vaga_id).first():
        raise HTTPException(status_code=404, detail="Vaga não encontrada")

    ja_existe = db.query(Favorito).filter(
        Favorito.usuario_id == usuario.id, Favorito.vaga_id == vaga_id
    ).first()
    if ja_existe:
        return {"mensagem": "Vaga já estava salva"}

    db.add(Favorito(usuario_id=usuario.id, vaga_id=vaga_id))
    db.commit()
    return {"mensagem": "Vaga salva"}


@app.delete("/api/favoritos/{vaga_id}")
def remover_favorito(vaga_id: int, usuario: Usuario = Depends(auth.usuario_atual), db: Session = Depends(get_db)):
    favorito = db.query(Favorito).filter(
        Favorito.usuario_id == usuario.id, Favorito.vaga_id == vaga_id
    ).first()
    if favorito:
        db.delete(favorito)
        db.commit()
    return {"mensagem": "Vaga removida dos salvos"}


@app.get("/api/recomendacoes")
def recomendacoes(usuario: Usuario = Depends(auth.usuario_atual), db: Session = Depends(get_db)):
    if not usuario.resumo or not usuario.resumo.strip():
        return {"vagas": [], "motivo": "perfil_incompleto"}

    vagas = db.query(Vaga).order_by(Vaga.id.desc()).limit(500).all()
    recomendadas = recomendar_vagas(usuario.resumo, vagas, limite=6)

    return {
        "vagas": [
            {
                "id": item["vaga"].id,
                "cargo": item["vaga"].cargo,
                "empresa": item["vaga"].empresa,
                "cidade": item["vaga"].cidade,
                "estado": item["vaga"].estado,
                "salario": item["vaga"].salario,
                "categoria": item["vaga"].categoria,
                "link": item["vaga"].link,
                "compatibilidade": item["compatibilidade"],
            }
            for item in recomendadas
        ]
    }


@app.get("/vagas/{vaga_id}", response_class=HTMLResponse)
def pagina_vaga(vaga_id: int, db: Session = Depends(get_db)):
    vaga = db.query(Vaga).filter(Vaga.id == vaga_id).first()
    if not vaga:
        raise HTTPException(status_code=404, detail="Vaga não encontrada")
    return pagina_vaga_html(vaga)


@app.get("/sitemap.xml", response_class=PlainTextResponse)
def sitemap(db: Session = Depends(get_db)):
    vagas = db.query(Vaga).order_by(Vaga.id.desc()).limit(1000).all()
    return PlainTextResponse(pagina_sitemap_xml(vagas), media_type="application/xml")


@app.get("/robots.txt", response_class=PlainTextResponse)
def robots():
    return PlainTextResponse(ROBOTS_TXT)


@app.get("/favicon.ico")
def favicon():
    svg = "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🚚</text></svg>"
    return HTMLResponse(content=svg, media_type="image/svg+xml")


frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
