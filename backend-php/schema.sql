-- Schema MySQL do LogJobs Brasil — espelha backend/models.py (SQLAlchemy/Python) 1:1.
-- Charset utf8mb4 em tudo (acentos, emojis nos textos de vaga/blog).

SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS usuarios (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nome VARCHAR(255) NOT NULL,
  email VARCHAR(255) NOT NULL,
  senha_hash VARCHAR(255) NOT NULL,
  tipo VARCHAR(32) NOT NULL DEFAULT 'candidato',
  telefone VARCHAR(64) NULL,
  cidade VARCHAR(255) NULL,
  resumo TEXT NULL,
  habilidades TEXT NULL,
  pretensao_salarial DOUBLE NULL,
  disponibilidade VARCHAR(64) NULL,
  possui_cnh VARCHAR(8) NULL,
  candidaturas_vistas_em DATETIME NULL,
  totp_secret VARCHAR(64) NULL,
  totp_ativado TINYINT NULL DEFAULT 0,
  veiculo_proprio VARCHAR(8) NULL,
  portfolio_url VARCHAR(512) NULL,
  linkedin_url VARCHAR(512) NULL,
  github_url VARCHAR(512) NULL,
  logo_url VARCHAR(512) NULL,
  site_url VARCHAR(512) NULL,
  instagram_url VARCHAR(512) NULL,
  experiencias_json TEXT NULL,
  formacoes_json TEXT NULL,
  cursos_json TEXT NULL,
  certificados_json TEXT NULL,
  idiomas_json TEXT NULL,
  oauth_provider VARCHAR(32) NULL,
  oauth_id VARCHAR(255) NULL,
  criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_usuarios_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS refresh_tokens (
  id INT AUTO_INCREMENT PRIMARY KEY,
  usuario_id INT NOT NULL,
  token_hash VARCHAR(64) NOT NULL,
  criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  expira_em DATETIME NOT NULL,
  revogado_em DATETIME NULL,
  UNIQUE KEY uq_refresh_token_hash (token_hash),
  KEY ix_refresh_usuario (usuario_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS tokens_recuperacao_senha (
  id INT AUTO_INCREMENT PRIMARY KEY,
  usuario_id INT NOT NULL,
  token_hash VARCHAR(64) NOT NULL,
  criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  expira_em DATETIME NOT NULL,
  usado_em DATETIME NULL,
  UNIQUE KEY uq_recuperacao_token_hash (token_hash),
  KEY ix_recuperacao_usuario (usuario_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS favoritos (
  id INT AUTO_INCREMENT PRIMARY KEY,
  usuario_id INT NOT NULL,
  vaga_id INT NOT NULL,
  criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_favorito_usuario_vaga (usuario_id, vaga_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS vagas (
  id INT AUTO_INCREMENT PRIMARY KEY,
  cargo VARCHAR(255) NOT NULL,
  empresa VARCHAR(255) NOT NULL,
  cidade VARCHAR(255) NOT NULL,
  estado VARCHAR(8) NOT NULL,
  salario DOUBLE NULL,
  modalidade VARCHAR(64) NULL,
  turno VARCHAR(64) NULL,
  tipo_contratacao VARCHAR(64) NULL,
  veiculo VARCHAR(64) NULL,
  descricao TEXT NULL,
  beneficios TEXT NULL,
  requisitos TEXT NULL,
  categoria VARCHAR(128) NOT NULL,
  link VARCHAR(1024) NULL,
  fonte VARCHAR(32) DEFAULT 'exemplo',
  usuario_id INT NULL,
  pausada TINYINT NULL DEFAULT 0,
  criada_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_vaga_cargo_empresa_cidade (cargo, empresa, cidade),
  KEY ix_vagas_cidade (cidade),
  KEY ix_vagas_estado (estado),
  KEY ix_vagas_categoria (categoria),
  KEY ix_vagas_usuario (usuario_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS candidaturas (
  id INT AUTO_INCREMENT PRIMARY KEY,
  vaga_id INT NOT NULL,
  nome VARCHAR(255) NOT NULL,
  email VARCHAR(255) NOT NULL,
  telefone VARCHAR(64) NULL,
  criada_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY ix_candidaturas_vaga (vaga_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS interessados (
  id INT AUTO_INCREMENT PRIMARY KEY,
  nome VARCHAR(255) NOT NULL,
  email VARCHAR(255) NOT NULL,
  tipo VARCHAR(64) NOT NULL,
  criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS atualizacoes (
  id INT AUTO_INCREMENT PRIMARY KEY,
  executada_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  jooble_configurado TINYINT DEFAULT 0,
  vagas_novas INT DEFAULT 0,
  vagas_totais INT DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS logs_auditoria (
  id INT AUTO_INCREMENT PRIMARY KEY,
  acao VARCHAR(128) NOT NULL,
  detalhes TEXT NULL,
  ip VARCHAR(64) NULL,
  criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS marcadores (
  id INT AUTO_INCREMENT PRIMARY KEY,
  chave VARCHAR(128) NOT NULL,
  criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_marcador_chave (chave)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS artigos (
  id INT AUTO_INCREMENT PRIMARY KEY,
  slug VARCHAR(255) NOT NULL,
  titulo VARCHAR(255) NOT NULL,
  resumo TEXT NOT NULL,
  conteudo LONGTEXT NOT NULL,
  categoria VARCHAR(128) NOT NULL,
  autor VARCHAR(255) DEFAULT 'Equipe LogJobs Brasil',
  publicado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_artigo_slug (slug)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS alertas (
  id INT AUTO_INCREMENT PRIMARY KEY,
  usuario_id INT NOT NULL,
  cargo VARCHAR(255) NULL,
  categoria VARCHAR(128) NULL,
  cidade VARCHAR(255) NULL,
  estado VARCHAR(8) NULL,
  vistas_em DATETIME NULL,
  criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY ix_alertas_usuario (usuario_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS conversas (
  id INT AUTO_INCREMENT PRIMARY KEY,
  candidato_id INT NOT NULL,
  empresa_id INT NOT NULL,
  vaga_id INT NULL,
  criada_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  atualizada_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_conversa_par_usuarios (candidato_id, empresa_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Sem equivalente em models.py: o rate limiter original (backend/rate_limit.py) guarda
-- as tentativas em memória do processo Python, o que não existe em PHP (cada requisição
-- roda num processo novo em hospedagem compartilhada) — por isso vira uma tabela.
CREATE TABLE IF NOT EXISTS limites_taxa (
  id INT AUTO_INCREMENT PRIMARY KEY,
  chave VARCHAR(64) NOT NULL,
  ip VARCHAR(64) NOT NULL,
  criado_em INT NOT NULL,
  KEY ix_limites_chave_ip (chave, ip)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS mensagens (
  id INT AUTO_INCREMENT PRIMARY KEY,
  conversa_id INT NOT NULL,
  remetente_id INT NOT NULL,
  texto TEXT NOT NULL,
  lida_em DATETIME NULL,
  criada_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY ix_mensagens_conversa (conversa_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
