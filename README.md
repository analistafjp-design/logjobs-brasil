# 🚚 LogJobs Brasil

Portal inteligente de vagas para logística.

📄 Documento oficial do projeto (visão, missão, arquitetura, roadmap e padrão de qualidade): [`docs/PVD.md`](./docs/PVD.md)

## Estrutura

```
logjobs-brasil/
├── docs/
│   └── PVD.md          # Project Vision Document
├── frontend/           # HTML5 + CSS3 + JS (consome a API do backend)
├── backend/            # FastAPI + SQLite
└── render.yaml         # Configuração de deploy (Render)
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

## Deploy (Render)

O `render.yaml` já está configurado para subir o backend (que também serve o frontend). Basta conectar o repositório no [Render](https://render.com) e configurar a variável `JOOBLE_API_KEY` (opcional) no painel.
