import os
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import Base, SessionLocal, engine, get_db
from jooble_client import JOOBLE_API_KEY, buscar_vagas_todas_categorias
from migrations import adicionar_colunas_faltantes
from models import Atualizacao, Candidatura, Interessado, Vaga
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
from seo import ROBOTS_TXT, pagina_sitemap_xml, pagina_vaga_html

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")

Base.metadata.create_all(bind=engine)
adicionar_colunas_faltantes(engine, Base)

app = FastAPI(title="LogJobs Brasil")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


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


@app.post("/api/atualizar-agora")
def forcar_atualizacao(x_admin_token: Optional[str] = Header(default=None)):
    if not ADMIN_TOKEN or x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Acesso negado")

    atualizar_vagas_periodicamente()
    return {"mensagem": "Atualização executada."}


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


frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
