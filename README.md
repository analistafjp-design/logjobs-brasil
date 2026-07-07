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

## Endpoint administrativo

O endpoint `POST /api/atualizar-agora` (força uma busca de vagas fora do agendamento normal) exige um cabeçalho `X-Admin-Token` com o valor da variável de ambiente `ADMIN_TOKEN`. Sem essa variável configurada, o endpoint fica sempre bloqueado (403). Configure `ADMIN_TOKEN` com um valor secreto próprio caso queira usá-lo.

## Deploy (Render)

O `render.yaml` já está configurado como *Blueprint*: sobe o backend (que também serve o frontend) e provisiona o banco Postgres automaticamente. Basta conectar o repositório no [Render](https://render.com) via **New → Blueprint** e configurar as variáveis `JOOBLE_API_KEY` e `ADMIN_TOKEN` (opcionais) no painel.
