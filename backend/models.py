from sqlalchemy import Column, Integer, String, Float, DateTime, UniqueConstraint
from sqlalchemy.sql import func

from database import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    senha_hash = Column(String, nullable=False)
    tipo = Column(String, nullable=False, default="candidato")  # candidato | empresa
    criado_em = Column(DateTime(timezone=True), server_default=func.now())


class Favorito(Base):
    __tablename__ = "favoritos"
    __table_args__ = (
        UniqueConstraint("usuario_id", "vaga_id", name="uq_favorito_usuario_vaga"),
    )

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, nullable=False, index=True)
    vaga_id = Column(Integer, nullable=False, index=True)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())


class Vaga(Base):
    __tablename__ = "vagas"
    __table_args__ = (
        UniqueConstraint("cargo", "empresa", "cidade", name="uq_vaga_cargo_empresa_cidade"),
    )

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
    link = Column(String, nullable=True)
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


class Atualizacao(Base):
    __tablename__ = "atualizacoes"

    id = Column(Integer, primary_key=True, index=True)
    executada_em = Column(DateTime(timezone=True), server_default=func.now())
    jooble_configurado = Column(Integer, default=0)
    vagas_novas = Column(Integer, default=0)
    vagas_totais = Column(Integer, default=0)


class Marcador(Base):
    """Controla correções/migrações de dados que devem rodar só uma vez."""
    __tablename__ = "marcadores"

    id = Column(Integer, primary_key=True, index=True)
    chave = Column(String, unique=True, nullable=False)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())
