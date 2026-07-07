from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func

from database import Base


class Vaga(Base):
    __tablename__ = "vagas"

    id = Column(Integer, primary_key=True, index=True)
    cargo = Column(String, nullable=False, index=True)
    empresa = Column(String, nullable=False, index=True)
    cidade = Column(String, nullable=False, index=True)
    estado = Column(String, nullable=False, index=True)
    salario = Column(Float, nullable=True)
    modalidade = Column(String, nullable=True)
    veiculo = Column(String, nullable=True)
    descricao = Column(String, nullable=True)
    beneficios = Column(String, nullable=True)
    requisitos = Column(String, nullable=True)
    categoria = Column(String, nullable=False, index=True)
    fonte = Column(String, default="exemplo")
    criada_em = Column(DateTime(timezone=True), server_default=func.now())
