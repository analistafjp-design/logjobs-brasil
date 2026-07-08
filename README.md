# 🚚 LogJobs Brasil

Portal inteligente de vagas para logística.

📄 Documento oficial do projeto (visão, missão, arquitetura, roadmap e padrão de qualidade): [`docs/PVD.md`](./docs/PVD.md)

## Estrutura

```
logjobs-brasil/
├── docs/
│   └── PVD.md          # Project Vision Document
├── frontend/           # HTML5 + CSS3 + JS (consome a API do backend)
├── backend/            # FastAPI + SQLite (local) / Postgres (produção)
└── render.yaml         # Configuração de deploy (Render, com banco Postgres incluso)
```

## Rodando localmente

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --app-dir .
```

Acesse `http://localhost:8000` — o próprio backend serve o frontend e a API (`/api/vagas`, `/api/estatisticas`, `/api/categorias`).

Na primeira execução, o banco SQLite é criado e populado automaticamente com vagas de exemplo.

## Conectando dados reais (Jooble)

A busca de vagas reais via [Jooble](https://jooble.org/api/about) já está implementada em `backend/jooble_client.py`, mas depende de uma chave de API:

1. Crie uma conta gratuita em https://jooble.org/api/about e obtenha sua `JOOBLE_API_KEY`.
2. Configure a variável de ambiente `JOOBLE_API_KEY` (localmente via `.env` ou `export`, no Render via **Environment**).
3. Apague o arquivo `logjobs.db` (ou a variável `DATABASE_URL` apontando para um banco novo) para forçar a nova busca na próxima inicialização.

Sem a chave configurada, o sistema funciona normalmente com o conjunto de vagas de exemplo.

## Banco de dados

Localmente, o projeto usa SQLite (`logjobs.db`) por padrão — não precisa configurar nada.

Em produção (Render), o SQLite **não deve ser usado**: o disco do plano free é efêmero e o banco é apagado a cada deploy ou reinício. O `render.yaml` já provisiona um banco **Postgres gratuito** junto com o serviço web e conecta a variável `DATABASE_URL` automaticamente — não precisa configurar nada manualmente.

⚠️ O plano free de Postgres do Render expira em 90 dias (a Render exclui o banco depois disso). Para manter os dados permanentemente, faça upgrade do banco para um plano pago no painel do Render antes do prazo, ou migre para outro provedor com free tier sem expiração (ex: [Neon](https://neon.tech) ou [Supabase](https://supabase.com)) — basta apontar a variável `DATABASE_URL` para o novo banco.

## Contas de usuário (candidato / empresa)

Login e cadastro reais estão disponíveis: botão "Entrar" na navbar abre um modal com abas de Entrar/Cadastrar. O cadastro aceita tipo "candidato" ou "empresa" (`POST /api/auth/registro`), login em `POST /api/auth/login`, e `GET /api/auth/me` retorna o usuário autenticado a partir do token.

Senhas são armazenadas com hash PBKDF2-HMAC-SHA256 (salt por usuário) e o token de sessão é um JWT HS256 — ambos implementados só com a biblioteca padrão do Python (`backend/security.py`), sem depender de `passlib[bcrypt]`/`cryptography`, que têm extensões nativas propensas a quebrar entre plataformas diferentes de desenvolvimento/deploy. Configure `LOGJOBS_SECRET_KEY` em produção (sem isso, usa uma chave de desenvolvimento fixa).

Usuários logados podem salvar vagas (favoritos): botão de estrela em cada card, endpoints `GET/POST/DELETE /api/favoritos`.

Existe uma página de perfil (`frontend/perfil.html`, acessível pelo nome do usuário na navbar) onde candidatos e empresas editam nome/telefone/cidade/mini-currículo (`PATCH /api/auth/me`) e veem/removem suas vagas salvas.

**Pendente:** painel administrativo via UI e módulos de IA ainda não existem.

## Endpoint administrativo

O endpoint `POST /api/atualizar-agora` (força uma busca de vagas fora do agendamento normal) exige um cabeçalho `X-Admin-Token` com o valor da variável de ambiente `ADMIN_TOKEN`. Sem essa variável configurada, o endpoint fica sempre bloqueado (403). Configure `ADMIN_TOKEN` com um valor secreto próprio caso queira usá-lo.

## Mudanças de schema (migrações)

O projeto não usa uma ferramenta de migração como Alembic. Em vez disso, `backend/migrations.py` compara os modelos com o banco real a cada inicialização e adiciona automaticamente qualquer **coluna nova** que estiver faltando (útil para não quebrar o banco já populado em produção quando um campo novo é adicionado ao código).

Isso cobre o caso mais comum (adicionar uma coluna), mas **não** cobre mudanças mais complexas — remover/renomear coluna, mudar tipo, adicionar constraint em tabela já populada. Para esses casos, uma migração manual (ou adotar Alembic) continua sendo necessária.

## Limpeza automática de vagas antigas

Vagas importadas do Jooble com mais de 60 dias são removidas automaticamente a cada execução do agendador (`backend/scheduler.py`), já que vagas de logística têm alta rotatividade e o anúncio original provavelmente já não existe mais depois desse prazo.

## Deploy (Render)

O `render.yaml` já está configurado como *Blueprint*: sobe o backend (que também serve o frontend) e provisiona o banco Postgres automaticamente. Basta conectar o repositório no [Render](https://render.com) via **New → Blueprint** e configurar as variáveis `JOOBLE_API_KEY` e `ADMIN_TOKEN` (opcionais) no painel.

## SEO

- Cada vaga tem uma página própria e indexável em `/vagas/{id}`, com dados estruturados [`JobPosting`](https://schema.org/JobPosting) (schema.org) — o formato que o Google exige para aparecer no Google for Jobs.
- `/sitemap.xml` e `/robots.txt` são gerados automaticamente a partir das vagas no banco.
- A home tem Open Graph e Twitter Card para bom preview ao compartilhar o link.
- As páginas de vaga e o `robots.txt`/`sitemap.xml` usam a variável `RENDER_EXTERNAL_URL` (que o Render define sozinho) para montar URLs absolutas. Se quiser usar um domínio próprio, defina a variável `SITE_URL` manualmente.
- **Atenção:** o `<link rel="canonical">` e as tags Open Graph da página inicial (`frontend/index.html`) estão fixos apontando para `https://logjobs-brasil.onrender.com/`, porque o `index.html` é um arquivo estático (não gerado pelo backend). Se o domínio final for diferente, atualize esses dois valores manualmente nesse arquivo.
