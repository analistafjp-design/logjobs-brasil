# Arquitetura — LogJobs Brasil

> Para visão, missão e roadmap de produto, veja [`PVD.md`](./PVD.md). Este documento é técnico: como o sistema é construído por dentro.

## Visão geral

O projeto tem **duas camadas principais**, sem arquitetura paralela:

```
logjobs-brasil/
├── frontend/   HTML5 + CSS3 + JS puro (sem framework, sem build step)
├── backend/    FastAPI (Python) + SQLite (local) / PostgreSQL (produção)
├── docs/       Esta documentação + o PVD
└── render.yaml Deploy (Render: serviço web + banco Postgres)
```

O próprio backend serve o frontend como arquivos estáticos (`StaticFiles` do FastAPI) — não há servidor Node/Nginx separado, nem build/bundler. Um único processo (`uvicorn main:app`) atende tanto `GET /` (HTML) quanto `GET /api/*` (JSON).

## Por que sem framework no frontend

Vagas de logística são majoritariamente acessadas por candidatos em conexões de internet mais lentas, em celulares mais antigos. HTML/CSS/JS puro carrega mais rápido que qualquer SPA com framework, sem sacrificar organização — cada página tem seu próprio `<page>.js`, e código realmente compartilhado (autenticação, tema, toast, modal, `escapeHtml`, `apiFetch`) vive em `app.js`, carregado por todas as páginas antes do script específico.

## Módulos do backend

Cada arquivo tem uma única responsabilidade. `main.py` é o único lugar que define rotas — todo o resto é lógica de suporte importada por ele.

| Arquivo | Responsabilidade |
|---|---|
| `main.py` | Definição de todas as rotas HTTP/WebSocket, orquestra os demais módulos |
| `models.py` | Modelos SQLAlchemy (tabelas do banco) |
| `database.py` | Engine SQLAlchemy, `SessionLocal`, dependência `get_db` |
| `migrations.py` | Migração aditiva simples: adiciona colunas que faltam em bancos já existentes (sem Alembic) |
| `security.py` | Hash de senha (PBKDF2-HMAC-SHA256) e JWT (HS256) — só biblioteca padrão do Python |
| `auth.py` | Emissão/validação de access token, refresh token (opaco, hash em banco, rotação de uso único) |
| `totp.py` | TOTP (RFC 6238) para 2FA — só biblioteca padrão |
| `oauth_google.py` | OAuth 2.0 Authorization Code com Google — só `urllib` da biblioteca padrão |
| `rate_limit.py` | Limitador de pedidos por IP, em memória (sliding window) |
| `jooble_client.py` | Integração com a API do Jooble para buscar vagas reais |
| `recomendacao.py` | Motor de recomendação de vagas por correspondência de palavras-chave |
| `analise_perfil.py` | Análise de perfil do candidato + gerador de currículo em texto |
| `entrevista.py` | Banco de perguntas do simulador de entrevista, por categoria |
| `assistente.py` | Central de ajuda por correspondência de palavras-chave |
| `chat_manager.py` | Gerenciador de conexões WebSocket do chat, em memória |
| `scheduler.py` | Job em segundo plano (a cada 20 min): busca novas vagas no Jooble, expira vagas antigas |
| `seed_data.py` / `blog_seed.py` | Dados de exemplo para banco vazio (primeira execução) |
| `seo.py` | `sitemap.xml`, `robots.txt`, página HTML server-side de uma vaga (para indexação) |

Nenhum desses módulos depende de bibliotecas nativas propensas a quebrar entre plataformas (ex.: evita `passlib[bcrypt]`, `PyJWT` com backend `cryptography`, `authlib`) — tudo que pode ser implementado com a biblioteca padrão do Python, é.

## Autenticação e sessão

```
registro/login ──► access_token (JWT, 7 dias) + refresh_token (opaco, 30 dias)
                              │
                    frontend guarda os dois no localStorage
                              │
        chamada autenticada ──► Authorization: Bearer <access_token>
                              │
              access token expirou (401) ──► POST /api/auth/refresh
                              │
              novo par de tokens, refresh antigo é revogado (uso único)
```

- **Access token**: JWT assinado (HS256), sem estado no servidor — qualquer instância consegue validar sozinha.
- **Refresh token**: valor aleatório opaco (não é JWT), guardado no banco só como hash SHA-256 (tabela `refresh_tokens`). Cada uso gera um novo par e revoga o anterior (rotação de uso único) — se um refresh token vazado for reaproveitado, ele já estará revogado.
- **Frontend**: `apiFetch()` (`frontend/js/app.js`) encapsula `fetch` para chamadas autenticadas — anexa o access token e, se receber 401, tenta `POST /api/auth/refresh` uma vez antes de desistir. Páginas mais antigas (`perfil.js`, `empresa.js`, `admin.js`) ainda usam `fetch` manual com `Authorization: Bearer`; novas funcionalidades (chat, IA) já usam `apiFetch`.

## Chat em tempo real

```
Candidato                                    Empresa
   │                                            │
   │  POST /api/chat/conversas (REST)           │
   │  { vaga_id, mensagem }                     │
   ├───────────────────────────────────────────►│  grava no banco (Mensagem)
   │                                             │  atualiza Conversa.atualizada_em
   │                                             │
   │  WS /ws/chat/{id}?token=...                │  WS /ws/chat/{id}?token=...
   │  (só conecta com a tela aberta)             │  (só conecta com a tela aberta)
   │◄────────────── transmite nova mensagem ────┤
```

- Uma única `Conversa` por par (candidato, empresa) — não por vaga, para não proliferar threads.
- Envio é **sempre via REST** (`POST /api/chat/conversas/{id}/mensagens`); o **WebSocket só entrega em tempo real** para quem está com a tela da conversa aberta. Ninguém conecta ao WebSocket sozinho/automaticamente.
- Autenticação do WebSocket via query string (`?token=`), já que o `WebSocket` nativo do navegador não permite headers customizados no handshake.
- `chat_manager.py` mantém as conexões ativas em memória (`dict[conversa_id, set[WebSocket]]`) — não é distribuído entre instâncias, suficiente para uma única instância (plano free do Render).
- **Dependência importante**: WebSocket no Uvicorn exige a lib `websockets` (ou `wsproto`) instalada — sem ela, o Uvicorn puro responde 404 para qualquer tentativa de upgrade de conexão. Já está em `requirements.txt`.

## IA sob demanda

Nenhum dos recursos de "IA" do projeto depende de uma chave de LLM externa (não há nenhuma configurada). Todos são determinísticos:

| Recurso | Como funciona |
|---|---|
| Recomendação de vagas | Correspondência de palavras-chave com pesos por campo (`recomendacao.py`) |
| Análise de perfil | Checklist de campos preenchidos + heurísticas simples (`analise_perfil.py`) |
| Gerador de currículo | Monta um texto formatado a partir dos dados do perfil (`analise_perfil.py`) |
| Simulador de entrevista | Banco de perguntas fixo por categoria de vaga (`entrevista.py`) |
| Assistente virtual | Correspondência de palavras-chave contra uma lista de intenções (`assistente.py`) |

Todos rodam **só quando o usuário pede** (abre a tela, aperta o botão) — nenhum roda em segundo plano ou automaticamente. Se no futuro uma chave de LLM real for configurada, esses módulos são o ponto de extensão natural (trocar a lógica interna, mantendo os mesmos endpoints e contratos de resposta).

## Banco de dados

Ver [`BANCO_DE_DADOS.md`](./BANCO_DE_DADOS.md) para o esquema completo.

## Referência de API

Ver [`API.md`](./API.md) para a lista de todas as rotas.

## Deploy

Ver [`DEPLOY.md`](./DEPLOY.md).
