from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import Base, SessionLocal, engine, get_db
from jooble_client import buscar_vagas_jooble
from models import Vaga
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
            for dados in VAGAS_EXEMPLO:
                db.add(Vaga(**dados, fonte="exemplo"))

            for dados in buscar_vagas_jooble():
                db.add(Vaga(**dados))

            db.commit()
    finally:
        db.close()


@app.on_event("startup")
def on_startup():
    popular_banco_se_vazio()


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


frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
