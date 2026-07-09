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
    telefone = Column(String, nullable=True)
    cidade = Column(String, nullable=True)
    resumo = Column(String, nullable=True)  # candidato: mini-currículo | empresa: descrição
    habilidades = Column(String, nullable=True)  # candidato: habilidades separadas por vírgula (ex.: "Direção defensiva, CNH E")
    pretensao_salarial = Column(Float, nullable=True)  # candidato
    disponibilidade = Column(String, nullable=True)  # candidato: Imediata | 15 dias | 30 dias | A combinar
    possui_cnh = Column(String, nullable=True)  # candidato: categoria da CNH (A, B, C, D, E) ou vazio se não possui
    candidaturas_vistas_em = Column(DateTime(timezone=True), nullable=True)  # empresa: última vez que abriu a lista de candidaturas recebidas
    totp_secret = Column(String, nullable=True)  # segredo da verificação em duas etapas (gerado ao ativar, mantido ao desativar não)
    totp_ativado = Column(Integer, nullable=True, default=0)  # 1 = login exige código TOTP além da senha (colunas adicionadas depois via migrations.py não recebem DEFAULT no banco, então trate None como 0/desativado)
    veiculo_proprio = Column(String, nullable=True)  # candidato: "sim" | "nao"
    portfolio_url = Column(String, nullable=True)
    linkedin_url = Column(String, nullable=True)
    github_url = Column(String, nullable=True)
    # Listas estruturadas (experiências, formação, cursos, certificados, idiomas) guardadas como
    # JSON serializado em texto — evita criar 5 tabelas quase idênticas só para listas curtas que
    # ninguém precisa consultar/filtrar via SQL, e mantém a API ergonômica (o backend faz o
    # json.dumps/loads; quem chama a API manda e recebe listas de verdade).
    experiencias_json = Column(String, nullable=True)
    formacoes_json = Column(String, nullable=True)
    cursos_json = Column(String, nullable=True)
    certificados_json = Column(String, nullable=True)
    idiomas_json = Column(String, nullable=True)
    oauth_provider = Column(String, nullable=True)  # "google", quando a conta foi criada/vinculada via login social
    oauth_id = Column(String, nullable=True)  # id ("sub") do usuário no provedor OAuth
    criado_em = Column(DateTime(timezone=True), server_default=func.now())


class RefreshToken(Base):
    """Refresh token de sessão persistente: opaco para o cliente, guardado aqui
    só como hash (sha256) — nunca em texto puro — para permitir revogação
    (logout, rotação a cada uso) sem depender de estado no JWT de acesso."""
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, nullable=False, index=True)
    token_hash = Column(String, unique=True, nullable=False, index=True)
    criado_em = Column(DateTime(timezone=True), server_default=func.now())
    expira_em = Column(DateTime(timezone=True), nullable=False)
    revogado_em = Column(DateTime(timezone=True), nullable=True)


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
    turno = Column(String, nullable=True)
    tipo_contratacao = Column(String, nullable=True)
    veiculo = Column(String, nullable=True)
    descricao = Column(String, nullable=True)
    beneficios = Column(String, nullable=True)
    requisitos = Column(String, nullable=True)
    categoria = Column(String, nullable=False, index=True)
    link = Column(String, nullable=True)
    fonte = Column(String, default="exemplo")
    usuario_id = Column(Integer, nullable=True, index=True)  # empresa dona da vaga, quando publicada pelo painel de empresas
    pausada = Column(Integer, nullable=True, default=0)  # 1 = empresa pausou a vaga (some da busca pública, mas continua no painel dela)
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


class Artigo(Base):
    __tablename__ = "artigos"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String, unique=True, index=True, nullable=False)
    titulo = Column(String, nullable=False)
    resumo = Column(String, nullable=False)
    conteudo = Column(String, nullable=False)
    categoria = Column(String, nullable=False)
    autor = Column(String, default="Equipe LogJobs Brasil")
    publicado_em = Column(DateTime(timezone=True), server_default=func.now())


class Alerta(Base):
    """Busca salva de um candidato. Sem envio por e-mail/WhatsApp/Telegram
    (o projeto não tem credenciais de nenhum desses serviços configuradas) —
    o "alerta" é o contador de vagas novas compatíveis, calculado ao vivo."""
    __tablename__ = "alertas"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, nullable=False, index=True)
    cargo = Column(String, nullable=True)
    categoria = Column(String, nullable=True)
    cidade = Column(String, nullable=True)
    estado = Column(String, nullable=True)
    vistas_em = Column(DateTime(timezone=True), nullable=True)  # última vez que o candidato abriu a lista de vagas deste alerta
    criado_em = Column(DateTime(timezone=True), server_default=func.now())


class Conversa(Base):
    """Uma conversa por par (candidato, empresa) — não por vaga: manter um único
    fio de conversa entre as mesmas duas contas evita proliferar threads
    quando o candidato se candidata a várias vagas da mesma empresa.
    `vaga_id` só guarda qual vaga deu origem à conversa, para dar contexto."""
    __tablename__ = "conversas"
    __table_args__ = (
        UniqueConstraint("candidato_id", "empresa_id", name="uq_conversa_par_usuarios"),
    )

    id = Column(Integer, primary_key=True, index=True)
    candidato_id = Column(Integer, nullable=False, index=True)
    empresa_id = Column(Integer, nullable=False, index=True)
    vaga_id = Column(Integer, nullable=True, index=True)
    criada_em = Column(DateTime(timezone=True), server_default=func.now())
    atualizada_em = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Mensagem(Base):
    __tablename__ = "mensagens"

    id = Column(Integer, primary_key=True, index=True)
    conversa_id = Column(Integer, nullable=False, index=True)
    remetente_id = Column(Integer, nullable=False, index=True)
    texto = Column(String, nullable=False)
    lida_em = Column(DateTime(timezone=True), nullable=True)
    criada_em = Column(DateTime(timezone=True), server_default=func.now())
