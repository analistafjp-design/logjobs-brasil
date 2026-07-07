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


class Candidatura(Base):
    __tablename__ = "candidaturas"

    id = Column(Integer, primary_key=True, index=True)
    vaga_id = Column(Integer, nullable=False, index=True)
    nome = Column(String, nullable=False)
    email = Column(String, nullable=False)
    telefone = Column(String, nullable=True)
    criada_em = Column(DateTime(timezone=True), server_default=func.now())


class Interessado(Base):
    __tablename__ = "interessados"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    email = Column(String, nullable=False)
    tipo = Column(String, nullable=False)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())
