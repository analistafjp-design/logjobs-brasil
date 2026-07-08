import json
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
import totp
from blog_seed import ARTIGOS_EXEMPLO
from database import Base, SessionLocal, engine, get_db
from recomendacao import recomendar_vagas
from jooble_client import JOOBLE_API_KEY, buscar_vagas_todas_categorias
from migrations import adicionar_colunas_faltantes
from models import Alerta, Artigo, Atualizacao, Candidatura, Favorito, Interessado, Usuario, Vaga
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


def popular_blog_se_vazio():
    db = SessionLocal()
    try:
        if db.query(Artigo).count() == 0:
            for dados in ARTIGOS_EXEMPLO:
                db.add(Artigo(**dados))
            try:
                db.commit()
            except IntegrityError:
                db.rollback()
    finally:
        db.close()


@app.on_event("startup")
def on_startup():
    aplicar_correcao_geografica_uma_vez()
    popular_banco_se_vazio()
    popular_blog_se_vazio()
    remover_vagas_exemplo_se_ha_reais()
    reclassificar_vagas_sem_categoria()
    iniciar_agendador()


@app.on_event("shutdown")
def on_shutdown():
    parar_agendador()


@app.get("/api/vagas")
def listar_vagas(
    cargo: Optional[str] = None,
    empresa: Optional[str] = None,
    cidade: Optional[str] = None,
    estado: Optional[str] = None,
    categoria: Optional[str] = None,
    modalidade: Optional[str] = None,
    turno: Optional[str] = None,
    tipo_contratacao: Optional[str] = None,
    beneficio: Optional[str] = None,
    salario_min: Optional[float] = None,
    salario_max: Optional[float] = None,
    ordenar: str = "recentes",
    limit: int = Query(default=20, le=100),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    query = db.query(Vaga).filter((Vaga.pausada.is_(None)) | (Vaga.pausada == 0))

    if cargo:
        query = query.filter(Vaga.cargo.ilike(f"%{cargo}%"))
    if empresa:
        query = query.filter(Vaga.empresa.ilike(f"%{empresa}%"))
    if cidade:
        query = query.filter(Vaga.cidade.ilike(f"%{cidade}%"))
    if estado:
        query = query.filter(Vaga.estado.ilike(f"%{estado}%"))
    if categoria:
        query = query.filter(Vaga.categoria.ilike(f"%{categoria}%"))
    if modalidade:
        query = query.filter(Vaga.modalidade.ilike(modalidade))
    if turno:
        query = query.filter(Vaga.turno.ilike(turno))
    if tipo_contratacao:
        query = query.filter(Vaga.tipo_contratacao.ilike(tipo_contratacao))
    if beneficio:
        query = query.filter(Vaga.beneficios.ilike(f"%{beneficio}%"))
    if salario_min:
        query = query.filter(Vaga.salario >= salario_min)
    if salario_max:
        query = query.filter(Vaga.salario <= salario_max)

    total = query.count()

    if ordenar == "relevancia" and cargo:
        # Sem motor de busca full-text: aproxima "relevância" priorizando cargo
        # que começa com o termo buscado, depois os que só contêm o termo,
        # com a data de publicação como critério de desempate.
        comeca_com = Vaga.cargo.ilike(f"{cargo}%")
        query = query.order_by(comeca_com.desc(), Vaga.id.desc())
    elif ordenar == "salario":
        query = query.order_by(Vaga.salario.is_(None), Vaga.salario.desc())
    else:
        query = query.order_by(Vaga.id.desc())

    vagas = query.offset(offset).limit(limit).all()

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
                "turno": v.turno,
                "tipo_contratacao": v.tipo_contratacao,
                "veiculo": v.veiculo,
                "categoria": v.categoria,
                "beneficios": v.beneficios,
                "link": v.link,
                "fonte": v.fonte,
                "criada_em": v.criada_em.isoformat() if v.criada_em else None,
            }
            for v in vagas
        ],
    }


@app.get("/api/sugestoes")
def sugestoes(tipo: str, q: str = "", db: Session = Depends(get_db)):
    if tipo not in ("cargo", "cidade", "empresa"):
        raise HTTPException(status_code=400, detail="Tipo de sugestão inválido")

    coluna = {"cargo": Vaga.cargo, "cidade": Vaga.cidade, "empresa": Vaga.empresa}[tipo]
    query = db.query(coluna).distinct()
    if q:
        query = query.filter(coluna.ilike(f"%{q}%"))
    valores = [v[0] for v in query.order_by(coluna).limit(8).all()]
    return valores


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
        "turno": vaga.turno,
        "tipo_contratacao": vaga.tipo_contratacao,
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


@app.get("/api/salarios")
def salarios(db: Session = Depends(get_db)):
    linhas = (
        db.query(
            Vaga.categoria,
            func.min(Vaga.salario).label("minimo"),
            func.avg(Vaga.salario).label("media"),
            func.max(Vaga.salario).label("maximo"),
            func.count(Vaga.id).label("total"),
        )
        .filter(Vaga.salario.isnot(None))
        .group_by(Vaga.categoria)
        .order_by(func.avg(Vaga.salario).desc())
        .all()
    )

    return [
        {
            "categoria": categoria,
            "minimo": minimo,
            "media": round(media, 2),
            "maximo": maximo,
            "total": total,
        }
        for categoria, minimo, media, maximo, total in linhas
    ]


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


def artigo_resumo_para_json(a: Artigo) -> dict:
    return {
        "slug": a.slug,
        "titulo": a.titulo,
        "resumo": a.resumo,
        "categoria": a.categoria,
        "autor": a.autor,
        "publicado_em": a.publicado_em.isoformat() if a.publicado_em else None,
    }


@app.get("/api/blog")
def listar_blog(categoria: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(Artigo)
    if categoria:
        query = query.filter(Artigo.categoria == categoria)
    artigos = query.order_by(Artigo.publicado_em.desc()).all()
    return [artigo_resumo_para_json(a) for a in artigos]


@app.get("/api/blog/{slug}")
def obter_artigo(slug: str, db: Session = Depends(get_db)):
    artigo = db.query(Artigo).filter(Artigo.slug == slug).first()
    if not artigo:
        raise HTTPException(status_code=404, detail="Artigo não encontrado")
    return {**artigo_resumo_para_json(artigo), "conteudo": artigo.conteudo}


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
    turno: Optional[str] = None
    tipo_contratacao: Optional[str] = None
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
    turno: Optional[str] = None
    tipo_contratacao: Optional[str] = None
    veiculo: Optional[str] = None
    descricao: Optional[str] = None
    beneficios: Optional[str] = None
    requisitos: Optional[str] = None
    link: Optional[str] = None
    pausada: Optional[int] = None


def vaga_admin_para_json(v: Vaga) -> dict:
    return {
        "id": v.id,
        "cargo": v.cargo,
        "empresa": v.empresa,
        "cidade": v.cidade,
        "estado": v.estado,
        "salario": v.salario,
        "modalidade": v.modalidade,
        "turno": v.turno,
        "tipo_contratacao": v.tipo_contratacao,
        "veiculo": v.veiculo,
        "categoria": v.categoria,
        "descricao": v.descricao,
        "beneficios": v.beneficios,
        "requisitos": v.requisitos,
        "link": v.link,
        "fonte": v.fonte,
        "pausada": bool(v.pausada),
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
    db.query(Candidatura).filter(Candidatura.vaga_id == vaga_id).delete()
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
def admin_listar_usuarios(
    q: Optional[str] = None, limit: int = Query(default=50, le=200), db: Session = Depends(get_db)
):
    query = db.query(Usuario)
    if q:
        query = query.filter((Usuario.nome.ilike(f"%{q}%")) | (Usuario.email.ilike(f"%{q}%")))
    usuarios = query.order_by(Usuario.id.desc()).limit(limit).all()
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


@app.delete("/api/admin/usuarios/{usuario_id}", dependencies=[Depends(verificar_admin)])
def admin_excluir_usuario(usuario_id: int, db: Session = Depends(get_db)):
    """Exclui a conta e os dados que dependem dela. Se for empresa, também remove as
    vagas que ela publicou (e as candidaturas dessas vagas) — do contrário elas
    ficariam "órfãs" na busca pública, sem ninguém para gerenciá-las."""
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    db.query(Favorito).filter(Favorito.usuario_id == usuario_id).delete()
    db.query(Alerta).filter(Alerta.usuario_id == usuario_id).delete()

    vaga_ids = [v.id for v in db.query(Vaga.id).filter(Vaga.usuario_id == usuario_id).all()]
    if vaga_ids:
        db.query(Candidatura).filter(Candidatura.vaga_id.in_(vaga_ids)).delete(synchronize_session=False)
        db.query(Vaga).filter(Vaga.usuario_id == usuario_id).delete(synchronize_session=False)

    db.delete(usuario)
    db.commit()
    return {"mensagem": "Usuário excluído"}


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
    codigo_totp: Optional[str] = None


class ExperienciaItem(BaseModel):
    cargo: str
    empresa: str
    cidade: Optional[str] = None
    inicio: Optional[str] = None  # "MM/AAAA"
    fim: Optional[str] = None  # vazio/None = emprego atual
    descricao: Optional[str] = None


class FormacaoItem(BaseModel):
    curso: str
    instituicao: str
    nivel: Optional[str] = None  # Ensino Médio | Técnico | Graduação | Pós-graduação | Mestrado | Doutorado
    status: Optional[str] = None  # Concluído | Cursando | Trancado
    ano: Optional[str] = None


class CursoItem(BaseModel):
    nome: str
    instituicao: Optional[str] = None
    ano: Optional[str] = None


class CertificadoItem(BaseModel):
    nome: str
    instituicao: Optional[str] = None
    ano: Optional[str] = None


class IdiomaItem(BaseModel):
    idioma: str
    nivel: Optional[str] = None  # Básico | Intermediário | Avançado | Fluente | Nativo


class PerfilEntrada(BaseModel):
    nome: Optional[str] = None
    telefone: Optional[str] = None
    cidade: Optional[str] = None
    resumo: Optional[str] = None
    habilidades: Optional[str] = None
    pretensao_salarial: Optional[float] = None
    disponibilidade: Optional[str] = None
    possui_cnh: Optional[str] = None
    veiculo_proprio: Optional[str] = None
    portfolio_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    experiencias: Optional[list[ExperienciaItem]] = None
    formacoes: Optional[list[FormacaoItem]] = None
    cursos: Optional[list[CursoItem]] = None
    certificados: Optional[list[CertificadoItem]] = None
    idiomas: Optional[list[IdiomaItem]] = None


def _lista_json(texto: Optional[str]) -> list:
    if not texto:
        return []
    try:
        return json.loads(texto)
    except (json.JSONDecodeError, TypeError):
        return []


def calcular_completude_perfil(usuario: Usuario) -> int:
    if usuario.tipo != "candidato":
        return 100
    campos = [
        bool(usuario.telefone),
        bool(usuario.cidade),
        bool(usuario.resumo),
        bool(usuario.habilidades),
        bool(usuario.pretensao_salarial),
        bool(usuario.disponibilidade),
        bool(_lista_json(usuario.experiencias_json)),
        bool(_lista_json(usuario.formacoes_json)),
        bool(usuario.idiomas_json and _lista_json(usuario.idiomas_json)),
        bool(usuario.linkedin_url or usuario.portfolio_url or usuario.github_url),
    ]
    return round(100 * sum(campos) / len(campos))


def usuario_para_json(usuario: Usuario) -> dict:
    return {
        "id": usuario.id,
        "nome": usuario.nome,
        "email": usuario.email,
        "tipo": usuario.tipo,
        "telefone": usuario.telefone,
        "cidade": usuario.cidade,
        "resumo": usuario.resumo,
        "habilidades": usuario.habilidades,
        "pretensao_salarial": usuario.pretensao_salarial,
        "disponibilidade": usuario.disponibilidade,
        "possui_cnh": usuario.possui_cnh,
        "veiculo_proprio": usuario.veiculo_proprio,
        "portfolio_url": usuario.portfolio_url,
        "linkedin_url": usuario.linkedin_url,
        "github_url": usuario.github_url,
        "experiencias": _lista_json(usuario.experiencias_json),
        "formacoes": _lista_json(usuario.formacoes_json),
        "cursos": _lista_json(usuario.cursos_json),
        "certificados": _lista_json(usuario.certificados_json),
        "idiomas": _lista_json(usuario.idiomas_json),
        "totp_ativado": bool(usuario.totp_ativado),
        "perfil_completude": calcular_completude_perfil(usuario),
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

    if usuario.totp_ativado:
        if not dados.codigo_totp:
            return {"requer_totp": True}
        if not totp.verificar_totp(usuario.totp_secret, dados.codigo_totp):
            raise HTTPException(status_code=401, detail="Código de verificação inválido")

    token = auth.criar_token(usuario.id)
    return {"access_token": token, "usuario": usuario_para_json(usuario)}


@app.get("/api/auth/me")
def me(usuario: Usuario = Depends(auth.usuario_atual)):
    return usuario_para_json(usuario)


@app.post("/api/auth/2fa/iniciar")
def iniciar_2fa(usuario: Usuario = Depends(auth.usuario_atual), db: Session = Depends(get_db)):
    if usuario.totp_ativado:
        raise HTTPException(status_code=400, detail="Verificação em duas etapas já está ativada")
    segredo = totp.gerar_segredo()
    usuario.totp_secret = segredo
    db.commit()
    return {"segredo": segredo, "otpauth_uri": totp.uri_otpauth(usuario.email, segredo)}


class Confirmar2FAEntrada(BaseModel):
    codigo: str


@app.post("/api/auth/2fa/confirmar")
def confirmar_2fa(
    dados: Confirmar2FAEntrada, usuario: Usuario = Depends(auth.usuario_atual), db: Session = Depends(get_db)
):
    if not usuario.totp_secret:
        raise HTTPException(status_code=400, detail="Nenhuma ativação de verificação em duas etapas pendente")
    if not totp.verificar_totp(usuario.totp_secret, dados.codigo):
        raise HTTPException(status_code=400, detail="Código inválido")
    usuario.totp_ativado = 1
    db.commit()
    return {"mensagem": "Verificação em duas etapas ativada"}


class Desativar2FAEntrada(BaseModel):
    senha: str


@app.post("/api/auth/2fa/desativar")
def desativar_2fa(
    dados: Desativar2FAEntrada, usuario: Usuario = Depends(auth.usuario_atual), db: Session = Depends(get_db)
):
    if not security.verify_password(dados.senha, usuario.senha_hash):
        raise HTTPException(status_code=401, detail="Senha incorreta")
    usuario.totp_ativado = 0
    usuario.totp_secret = None
    db.commit()
    return {"mensagem": "Verificação em duas etapas desativada"}


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
    if dados.habilidades is not None:
        usuario.habilidades = dados.habilidades.strip() or None
    if dados.pretensao_salarial is not None:
        usuario.pretensao_salarial = dados.pretensao_salarial
    if dados.disponibilidade is not None:
        usuario.disponibilidade = dados.disponibilidade.strip() or None
    if dados.possui_cnh is not None:
        usuario.possui_cnh = dados.possui_cnh.strip() or None
    if dados.veiculo_proprio is not None:
        usuario.veiculo_proprio = dados.veiculo_proprio.strip() or None
    if dados.portfolio_url is not None:
        usuario.portfolio_url = dados.portfolio_url.strip() or None
    if dados.linkedin_url is not None:
        usuario.linkedin_url = dados.linkedin_url.strip() or None
    if dados.github_url is not None:
        usuario.github_url = dados.github_url.strip() or None
    if dados.experiencias is not None:
        usuario.experiencias_json = json.dumps([e.model_dump() for e in dados.experiencias])
    if dados.formacoes is not None:
        usuario.formacoes_json = json.dumps([f.model_dump() for f in dados.formacoes])
    if dados.cursos is not None:
        usuario.cursos_json = json.dumps([c.model_dump() for c in dados.cursos])
    if dados.certificados is not None:
        usuario.certificados_json = json.dumps([c.model_dump() for c in dados.certificados])
    if dados.idiomas is not None:
        usuario.idiomas_json = json.dumps([i.model_dump() for i in dados.idiomas])

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

    texto_experiencias = " ".join(
        f"{e.get('cargo', '')} {e.get('descricao', '')}" for e in _lista_json(usuario.experiencias_json)
    )
    texto_formacoes = " ".join(f.get("curso", "") for f in _lista_json(usuario.formacoes_json))
    texto_perfil = " ".join(filter(None, [usuario.resumo, usuario.habilidades, texto_experiencias, texto_formacoes]))
    vagas = db.query(Vaga).order_by(Vaga.id.desc()).limit(500).all()
    recomendadas = recomendar_vagas(texto_perfil, vagas, limite=6)

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


NIVEIS_CONQUISTA = [
    (0, "Iniciante"),
    (2, "Em busca ativa"),
    (4, "Candidato de destaque"),
]


@app.get("/api/conquistas")
def conquistas(usuario: Usuario = Depends(auth.usuario_atual), db: Session = Depends(get_db)):
    perfil_completo = bool(usuario.telefone and usuario.cidade and usuario.resumo)
    total_favoritos = db.query(Favorito).filter(Favorito.usuario_id == usuario.id).count()
    total_candidaturas = db.query(Candidatura).filter(Candidatura.email == usuario.email).count()

    badges = [
        {
            "chave": "perfil_completo",
            "titulo": "Perfil completo",
            "descricao": "Preencheu nome, telefone, cidade e mini-currículo",
            "icone": "🧑‍💼",
            "conquistado": perfil_completo,
        },
        {
            "chave": "primeira_vaga_salva",
            "titulo": "Primeira vaga salva",
            "descricao": "Salvou pelo menos uma vaga nos favoritos",
            "icone": "⭐",
            "conquistado": total_favoritos >= 1,
        },
        {
            "chave": "colecionador",
            "titulo": "Colecionador de oportunidades",
            "descricao": "Salvou 5 ou mais vagas",
            "icone": "📌",
            "conquistado": total_favoritos >= 5,
        },
        {
            "chave": "primeira_candidatura",
            "titulo": "Primeira candidatura",
            "descricao": "Enviou sua primeira candidatura pela plataforma",
            "icone": "📨",
            "conquistado": total_candidaturas >= 1,
        },
    ]

    total_conquistado = sum(1 for b in badges if b["conquistado"])
    nivel = NIVEIS_CONQUISTA[0][1]
    for minimo, nome_nivel in NIVEIS_CONQUISTA:
        if total_conquistado >= minimo:
            nivel = nome_nivel

    return {"badges": badges, "total_conquistado": total_conquistado, "total": len(badges), "nivel": nivel}


class AlertaEntrada(BaseModel):
    cargo: Optional[str] = None
    categoria: Optional[str] = None
    cidade: Optional[str] = None
    estado: Optional[str] = None


def contar_vagas_do_alerta(alerta: Alerta, db: Session) -> int:
    query = db.query(Vaga)
    if alerta.cargo:
        query = query.filter(Vaga.cargo.ilike(f"%{alerta.cargo}%"))
    if alerta.categoria:
        query = query.filter(Vaga.categoria.ilike(f"%{alerta.categoria}%"))
    if alerta.cidade:
        query = query.filter(Vaga.cidade.ilike(f"%{alerta.cidade}%"))
    if alerta.estado:
        query = query.filter(Vaga.estado.ilike(alerta.estado))
    return query.count()


def contar_vagas_novas_do_alerta(alerta: Alerta, db: Session) -> int:
    query = db.query(Vaga)
    if alerta.cargo:
        query = query.filter(Vaga.cargo.ilike(f"%{alerta.cargo}%"))
    if alerta.categoria:
        query = query.filter(Vaga.categoria.ilike(f"%{alerta.categoria}%"))
    if alerta.cidade:
        query = query.filter(Vaga.cidade.ilike(f"%{alerta.cidade}%"))
    if alerta.estado:
        query = query.filter(Vaga.estado.ilike(alerta.estado))
    if alerta.vistas_em:
        query = query.filter(Vaga.criada_em > alerta.vistas_em)
    return query.count()


def alerta_para_json(alerta: Alerta, db: Session) -> dict:
    return {
        "id": alerta.id,
        "cargo": alerta.cargo,
        "categoria": alerta.categoria,
        "cidade": alerta.cidade,
        "estado": alerta.estado,
        "criado_em": alerta.criado_em.isoformat() if alerta.criado_em else None,
        "total_vagas": contar_vagas_do_alerta(alerta, db),
        "vagas_novas": contar_vagas_novas_do_alerta(alerta, db),
    }


@app.get("/api/alertas")
def listar_alertas(usuario: Usuario = Depends(auth.usuario_atual), db: Session = Depends(get_db)):
    alertas = db.query(Alerta).filter(Alerta.usuario_id == usuario.id).order_by(Alerta.id.desc()).all()
    return [alerta_para_json(a, db) for a in alertas]


@app.post("/api/alertas", status_code=201)
def criar_alerta(dados: AlertaEntrada, usuario: Usuario = Depends(auth.usuario_atual), db: Session = Depends(get_db)):
    if not any([dados.cargo, dados.categoria, dados.cidade, dados.estado]):
        raise HTTPException(status_code=400, detail="Preencha pelo menos um critério para o alerta")

    total_alertas = db.query(Alerta).filter(Alerta.usuario_id == usuario.id).count()
    if total_alertas >= 10:
        raise HTTPException(status_code=400, detail="Limite de 10 alertas por conta")

    alerta = Alerta(usuario_id=usuario.id, **dados.model_dump())
    db.add(alerta)
    db.commit()
    db.refresh(alerta)
    return alerta_para_json(alerta, db)


@app.delete("/api/alertas/{alerta_id}")
def remover_alerta(alerta_id: int, usuario: Usuario = Depends(auth.usuario_atual), db: Session = Depends(get_db)):
    alerta = db.query(Alerta).filter(Alerta.id == alerta_id, Alerta.usuario_id == usuario.id).first()
    if alerta:
        db.delete(alerta)
        db.commit()
    return {"mensagem": "Alerta removido"}


@app.post("/api/alertas/{alerta_id}/marcar-visto")
def marcar_alerta_visto(alerta_id: int, usuario: Usuario = Depends(auth.usuario_atual), db: Session = Depends(get_db)):
    alerta = db.query(Alerta).filter(Alerta.id == alerta_id, Alerta.usuario_id == usuario.id).first()
    if not alerta:
        raise HTTPException(status_code=404, detail="Alerta não encontrado")
    alerta.vistas_em = func.now()
    db.commit()
    return {"mensagem": "Alerta marcado como visto"}


@app.get("/api/minhas-candidaturas")
def minhas_candidaturas(usuario: Usuario = Depends(auth.usuario_atual), db: Session = Depends(get_db)):
    candidaturas = (
        db.query(Candidatura)
        .filter(Candidatura.email == usuario.email)
        .order_by(Candidatura.id.desc())
        .all()
    )
    vagas_por_id = {
        v.id: v for v in db.query(Vaga).filter(Vaga.id.in_([c.vaga_id for c in candidaturas])).all()
    }

    return [
        {
            "id": c.id,
            "vaga_id": c.vaga_id,
            "cargo": vagas_por_id[c.vaga_id].cargo if c.vaga_id in vagas_por_id else None,
            "empresa": vagas_por_id[c.vaga_id].empresa if c.vaga_id in vagas_por_id else None,
            "criada_em": c.criada_em.isoformat() if c.criada_em else None,
        }
        for c in candidaturas
    ]


def verificar_empresa(usuario: Usuario = Depends(auth.usuario_atual)) -> Usuario:
    if usuario.tipo != "empresa":
        raise HTTPException(status_code=403, detail="Recurso disponível apenas para contas de empresa")
    return usuario


@app.get("/api/empresa/vagas")
def empresa_listar_vagas(
    q: Optional[str] = None,
    status: Optional[str] = None,  # "ativa" | "pausada"
    usuario: Usuario = Depends(verificar_empresa),
    db: Session = Depends(get_db),
):
    query = db.query(Vaga).filter(Vaga.usuario_id == usuario.id)
    if q:
        query = query.filter((Vaga.cargo.ilike(f"%{q}%")) | (Vaga.cidade.ilike(f"%{q}%")))
    if status == "ativa":
        query = query.filter((Vaga.pausada.is_(None)) | (Vaga.pausada == 0))
    elif status == "pausada":
        query = query.filter(Vaga.pausada == 1)
    vagas = query.order_by(Vaga.id.desc()).all()

    candidaturas_por_vaga = dict(
        db.query(Candidatura.vaga_id, func.count(Candidatura.id))
        .filter(Candidatura.vaga_id.in_([v.id for v in vagas]))
        .group_by(Candidatura.vaga_id)
        .all()
    )
    return [
        {**vaga_admin_para_json(v), "total_candidaturas": candidaturas_por_vaga.get(v.id, 0)}
        for v in vagas
    ]


@app.post("/api/empresa/vagas", status_code=201)
def empresa_criar_vaga(dados: VagaEntrada, usuario: Usuario = Depends(verificar_empresa), db: Session = Depends(get_db)):
    vaga = Vaga(**dados.model_dump(), fonte="empresa", usuario_id=usuario.id)
    db.add(vaga)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Já existe uma vaga com esse cargo, empresa e cidade")
    db.refresh(vaga)
    return vaga_admin_para_json(vaga)


@app.patch("/api/empresa/vagas/{vaga_id}")
def empresa_editar_vaga(
    vaga_id: int, dados: VagaAtualizacao, usuario: Usuario = Depends(verificar_empresa), db: Session = Depends(get_db)
):
    vaga = db.query(Vaga).filter(Vaga.id == vaga_id, Vaga.usuario_id == usuario.id).first()
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


@app.delete("/api/empresa/vagas/{vaga_id}")
def empresa_excluir_vaga(vaga_id: int, usuario: Usuario = Depends(verificar_empresa), db: Session = Depends(get_db)):
    vaga = db.query(Vaga).filter(Vaga.id == vaga_id, Vaga.usuario_id == usuario.id).first()
    if not vaga:
        raise HTTPException(status_code=404, detail="Vaga não encontrada")
    db.query(Candidatura).filter(Candidatura.vaga_id == vaga_id).delete()
    db.delete(vaga)
    db.commit()
    return {"mensagem": "Vaga excluída"}


def _buscar_vaga_da_empresa(vaga_id: int, usuario: Usuario, db: Session) -> Vaga:
    vaga = db.query(Vaga).filter(Vaga.id == vaga_id, Vaga.usuario_id == usuario.id).first()
    if not vaga:
        raise HTTPException(status_code=404, detail="Vaga não encontrada")
    return vaga


@app.post("/api/empresa/vagas/{vaga_id}/pausar")
def empresa_pausar_vaga(vaga_id: int, usuario: Usuario = Depends(verificar_empresa), db: Session = Depends(get_db)):
    vaga = _buscar_vaga_da_empresa(vaga_id, usuario, db)
    vaga.pausada = 1
    db.commit()
    db.refresh(vaga)
    return vaga_admin_para_json(vaga)


@app.post("/api/empresa/vagas/{vaga_id}/reativar")
def empresa_reativar_vaga(vaga_id: int, usuario: Usuario = Depends(verificar_empresa), db: Session = Depends(get_db)):
    vaga = _buscar_vaga_da_empresa(vaga_id, usuario, db)
    vaga.pausada = 0
    db.commit()
    db.refresh(vaga)
    return vaga_admin_para_json(vaga)


@app.post("/api/empresa/vagas/{vaga_id}/renovar")
def empresa_renovar_vaga(vaga_id: int, usuario: Usuario = Depends(verificar_empresa), db: Session = Depends(get_db)):
    """"Renovar" republica a vaga: reativa (se estava pausada) e atualiza a data de
    publicação para agora, para que volte a aparecer no topo de "mais recentes"."""
    vaga = _buscar_vaga_da_empresa(vaga_id, usuario, db)
    vaga.pausada = 0
    vaga.criada_em = func.now()
    db.commit()
    db.refresh(vaga)
    return vaga_admin_para_json(vaga)


@app.get("/api/empresa/candidaturas-exportar")
def empresa_exportar_candidaturas(usuario: Usuario = Depends(verificar_empresa), db: Session = Depends(get_db)):
    vagas = db.query(Vaga).filter(Vaga.usuario_id == usuario.id).all()
    vagas_por_id = {v.id: v for v in vagas}
    candidaturas = (
        db.query(Candidatura)
        .filter(Candidatura.vaga_id.in_(vagas_por_id.keys()))
        .order_by(Candidatura.vaga_id, Candidatura.id.desc())
        .all()
    ) if vagas_por_id else []

    linhas = ["Vaga,Cidade/UF,Nome,E-mail,Telefone,Data da candidatura"]
    for c in candidaturas:
        vaga = vagas_por_id.get(c.vaga_id)
        campos = [
            vaga.cargo if vaga else "",
            f"{vaga.cidade}/{vaga.estado}" if vaga else "",
            c.nome,
            c.email,
            c.telefone or "",
            c.criada_em.isoformat() if c.criada_em else "",
        ]
        linhas.append(",".join('"' + campo.replace('"', '""') + '"' for campo in campos))

    csv_texto = "\n".join(linhas)
    return PlainTextResponse(
        csv_texto,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=candidaturas.csv"},
    )


@app.get("/api/empresa/candidaturas/{vaga_id}")
def empresa_listar_candidaturas_da_vaga(
    vaga_id: int, usuario: Usuario = Depends(verificar_empresa), db: Session = Depends(get_db)
):
    vaga = db.query(Vaga).filter(Vaga.id == vaga_id, Vaga.usuario_id == usuario.id).first()
    if not vaga:
        raise HTTPException(status_code=404, detail="Vaga não encontrada")
    candidaturas = db.query(Candidatura).filter(Candidatura.vaga_id == vaga_id).order_by(Candidatura.id.desc()).all()
    return [
        {
            "id": c.id,
            "nome": c.nome,
            "email": c.email,
            "telefone": c.telefone,
            "criada_em": c.criada_em.isoformat() if c.criada_em else None,
        }
        for c in candidaturas
    ]


@app.get("/api/empresa/estatisticas")
def empresa_estatisticas(usuario: Usuario = Depends(verificar_empresa), db: Session = Depends(get_db)):
    vaga_ids = [v.id for v in db.query(Vaga.id).filter(Vaga.usuario_id == usuario.id).all()]
    total_candidaturas = (
        db.query(func.count(Candidatura.id)).filter(Candidatura.vaga_id.in_(vaga_ids)).scalar() if vaga_ids else 0
    )
    candidaturas_novas = 0
    if vaga_ids:
        query_novas = db.query(func.count(Candidatura.id)).filter(Candidatura.vaga_id.in_(vaga_ids))
        if usuario.candidaturas_vistas_em:
            query_novas = query_novas.filter(Candidatura.criada_em > usuario.candidaturas_vistas_em)
        candidaturas_novas = query_novas.scalar()
    return {
        "total_vagas": len(vaga_ids),
        "total_candidaturas": total_candidaturas,
        "candidaturas_novas": candidaturas_novas,
    }


@app.post("/api/empresa/candidaturas/marcar-vistas")
def empresa_marcar_candidaturas_vistas(usuario: Usuario = Depends(verificar_empresa), db: Session = Depends(get_db)):
    # Usa func.now() (o relógio do banco) em vez de datetime.now() do Python: precisa ser a
    # mesma fonte/precisão usada no server_default de Candidatura.criada_em, senão uma
    # candidatura criada no mesmo segundo pode ficar com timestamp "anterior" ao marcador.
    usuario.candidaturas_vistas_em = func.now()
    db.commit()
    return {"mensagem": "Candidaturas marcadas como vistas"}


@app.get("/vagas/{vaga_id}", response_class=HTMLResponse)
def pagina_vaga(vaga_id: int, db: Session = Depends(get_db)):
    vaga = db.query(Vaga).filter(Vaga.id == vaga_id).first()
    if not vaga:
        raise HTTPException(status_code=404, detail="Vaga não encontrada")
    return pagina_vaga_html(vaga)


@app.get("/sitemap.xml", response_class=PlainTextResponse)
def sitemap(db: Session = Depends(get_db)):
    vagas = db.query(Vaga).order_by(Vaga.id.desc()).limit(1000).all()
    artigos = db.query(Artigo).all()
    return PlainTextResponse(pagina_sitemap_xml(vagas, artigos), media_type="application/xml")


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
