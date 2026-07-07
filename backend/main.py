from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import Base, SessionLocal, engine, get_db
from jooble_client import JOOBLE_API_KEY, buscar_vagas_todas_regioes
from models import Atualizacao, Candidatura, Interessado, Vaga
from scheduler import atualizar_vagas_periodicamente, iniciar_agendador, parar_agendador, remover_vagas_exemplo_se_ha_reais
from seed_data import VAGAS_EXEMPLO

Base.metadata.create_all(bind=engine)

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
            vagas_reais = buscar_vagas_todas_regioes()

            if vagas_reais:
                for dados in vagas_reais:
                    db.add(Vaga(**dados))
            else:
                for dados in VAGAS_EXEMPLO:
                    db.add(Vaga(**dados, fonte="exemplo"))

            db.commit()
    finally:
        db.close()


@app.on_event("startup")
def on_startup():
    popular_banco_se_vazio()
    remover_vagas_exemplo_se_ha_reais()
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
        "atualizacao": "24h",
    }


@app.get("/api/categorias")
def categorias(db: Session = Depends(get_db)):
    linhas = db.query(Vaga.categoria, func.count(Vaga.id)).group_by(Vaga.categoria).all()
    return [{"categoria": categoria, "total": total} for categoria, total in linhas]


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
def forcar_atualizacao():
    atualizar_vagas_periodicamente()
    return {"mensagem": "Atualização executada."}


class CandidaturaEntrada(BaseModel):
    vaga_id: int
    nome: str
    email: EmailStr
    telefone: Optional[str] = None


@app.post("/api/candidaturas")
def criar_candidatura(dados: CandidaturaEntrada, db: Session = Depends(get_db)):
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


@app.post("/api/interessados")
def criar_interessado(dados: InteressadoEntrada, db: Session = Depends(get_db)):
    interessado = Interessado(nome=dados.nome, email=dados.email, tipo=dados.tipo)
    db.add(interessado)
    db.commit()
    db.refresh(interessado)

    return {"id": interessado.id, "mensagem": "Cadastro recebido! Avisaremos você em breve."}


frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
