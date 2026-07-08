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

Candidatos têm campos extras de perfil, só exibidos para `tipo: "candidato"`: habilidades (lista livre separada por vírgula), pretensão salarial, disponibilidade (Imediata/15 dias/30 dias/A combinar) e categoria de CNH — relevantes para a maioria das vagas de logística. As habilidades entram automaticamente no motor de recomendação (próxima seção), somadas ao texto do mini-currículo.

## Recomendação de vagas (IA)

Candidatos com o mini-currículo preenchido recebem uma seção "Vagas recomendadas para você" no perfil, via `GET /api/recomendacoes`. O motor (`backend/recomendacao.py`) é uma correspondência de palavras-chave com pesos por campo (cargo/categoria valem mais que descrição/benefícios) — determinístico e sem depender de nenhuma API externa de IA, já que o projeto não tem chave de LLM configurada. Cada vaga recomendada mostra um percentual de compatibilidade (proporção das palavras-chave do currículo do candidato encontradas na vaga).

## Busca avançada e experiência de listagem

A busca da home (`index.html`) foi expandida além do campo cargo/cidade original:

- **Autocomplete**: os campos "Cargo ou palavra-chave" e "Cidade" sugerem valores reais existentes no banco via `GET /api/sugestoes`, usando `<datalist>` nativo (sem dependências extras de JS).
- **Filtros avançados**: painel expansível (`#filtrosAvancados`) com estado (UF), modalidade, turno, tipo de contratação, faixa salarial (mín./máx.) e benefício — todos aplicados como query params em `GET /api/vagas`. Um contador (`#filtrosAtivosCount`) mostra quantos filtros estão ativos no botão de alternância.
- **Ordenação**: mais recentes, relevância (correspondência com o termo buscado) ou maior salário, via parâmetro `ordenar`.
- **Loading state**: skeleton cards animados (`renderizarSkeletons()`) substituem o texto "Carregando vagas..." enquanto a busca está em andamento.
- **Empty state**: quando nenhuma vaga corresponde aos filtros, é exibido um estado vazio ilustrado com botão "Limpar filtros", em vez de uma lista em branco.
- **Buscas recentes**: continuam salvas em `localStorage` e agora restauram também os filtros avançados usados, não só cargo/cidade.

Nenhum filtro depende de geolocalização/CEP — o banco não tem latitude/longitude nem bairro por vaga, então busca por distância em km não foi implementada (ver seção "Mapa de vagas" abaixo, que usa apenas cidade/UF).

## Mapa de vagas

Disponível em `/mapa.html`: mapa de bolhas do Brasil (uma bolha por estado, tamanho proporcional ao número de vagas), usando coordenadas aproximadas das 27 capitais como ponto representativo — o banco não guarda geolocalização por vaga/cidade, então um mapa de fronteiras reais por estado ficaria fora de escopo. Reaproveita os dados de `/api/dashboard` (por_estado). Passar o mouse mostra o total; clicar filtra as vagas daquele estado na home (`index.html?estado=UF`).

## Alertas de vagas e histórico

**Alertas** (`/api/alertas`, seção "🔔 Alertas de vagas" no perfil): candidatos salvam critérios de busca (cargo/categoria/cidade/estado) e veem, ao vivo, quantas vagas correspondem — sem envio por e-mail/WhatsApp/Telegram, porque o projeto não tem credenciais de nenhum desses serviços configuradas (seria necessário inventar uma integração falsa, o que evitamos). É funcionalmente uma busca salva com contador dinâmico.

**Histórico de candidaturas** (`/api/minhas-candidaturas`): lista as candidaturas do usuário logado, casadas pelo e-mail com a tabela `candidaturas` (que não exige login para se candidatar). O formulário de candidatura agora pré-preenche nome/e-mail/telefone quando o candidato está logado, para que o histórico funcione de forma consistente.

**Histórico de buscas**: as últimas 5 buscas ficam salvas no navegador (`localStorage`, sem backend) e aparecem como chips clicáveis abaixo da busca na home.

## Blog

Disponível em `/blog.html` (lista com filtro por categoria) e `/artigo.html?slug=...` (página individual, com dados estruturados `Article` do schema.org). Conteúdo real (`backend/blog_seed.py`, 4 artigos: documentos para entregador, currículo para logística, perguntas de entrevista, tendências do mercado), semeado automaticamente na primeira execução, via `GET /api/blog` e `GET /api/blog/{slug}`. Artigos entram automaticamente no `sitemap.xml`.

## Gamificação

Candidatos veem uma seção "🏅 Suas conquistas" no perfil (`GET /api/conquistas`), com 4 selos calculados a partir de dados reais já existentes — sem tabela nova: perfil completo, primeira vaga salva, 5+ vagas salvas ("colecionador") e primeira candidatura enviada (correspondência por e-mail com `Candidatura`, já que candidaturas não exigem login). Um "nível" (Iniciante / Em busca ativa / Candidato de destaque) é derivado da quantidade de selos conquistados. As conquistas são recalculadas em tempo real após qualquer ação relevante (salvar perfil, salvar/remover vaga).

## Comparador de salários

Disponível em `/calculadora.html` (link "Salários" na navbar), via `GET /api/salarios`: mínimo, média e máximo por categoria, calculados a partir das vagas com salário informado. Permite comparar até duas categorias lado a lado, além de uma tabela completa ordenada pela maior média.

## PWA (instalável)

O site tem `manifest.json` e um service worker (`frontend/sw.js`) registrado em todas as páginas via `js/app.js`. Ele faz cache do "app shell" (HTML/CSS/JS estáticos e o ícone) com estratégia stale-while-revalidate, permitindo abrir o site rapidamente e até offline — mas **nunca** cacheia `/api/*`, `/vagas/{id}` (gerado dinamicamente) nem `sitemap.xml`/`robots.txt`, para não servir vagas desatualizadas.

O ícone (`frontend/icon.svg`) é SVG em vez de PNG, porque o ambiente de desenvolvimento usado não tinha uma ferramenta de conversão de imagem disponível. Funciona bem para instalação em Chrome/Edge/Android; no iOS Safari a experiência pode ser mais limitada — gerar PNGs reais (192x192, 512x512) a partir do `icon.svg` é uma melhoria futura de baixo esforço.

## Ranking de empresas

Disponível em `/ranking.html` (linkado na navbar e no rodapé), via `GET /api/ranking`: top 15 empresas por número de vagas ativas e top 15 por salário médio informado (exige pelo menos 2 vagas com salário cadastrado para entrar no ranking salarial, evitando que uma única vaga distorça a média). Não há ranking por "avaliação" porque o projeto não tem sistema de avaliações de empresas — não faria sentido inventar dados.

## Painel de empresas (self-service)

Disponível em `/empresa.html` (linkado como "Empresas" na navbar de todas as páginas). Qualquer usuário pode criar uma conta do tipo "empresa" pelo mesmo modal de cadastro usado por candidatos (`tipo: "empresa"`); não há aprovação manual nem cobrança — é honestamente um cadastro livre, sem verificação de CNPJ ou pagamento, já que essas integrações não foram implementadas (ver seção sobre integrações pendentes).

Uma conta de empresa logada pode, via `/api/empresa/*` (protegido por JWT + checagem de `usuario.tipo == "empresa"`, não pelo token de admin):
- Publicar, editar e excluir suas próprias vagas (`GET/POST/PATCH/DELETE /api/empresa/vagas`) — as vagas publicadas aparecem imediatamente na busca pública, com `fonte: "empresa"`.
- Ver quantas candidaturas cada vaga recebeu e os dados de cada candidato (`GET /api/empresa/candidaturas/{vaga_id}`).
- Ver um resumo (`GET /api/empresa/estatisticas`): total de vagas publicadas e total de candidaturas recebidas.

Uma empresa só enxerga e só pode editar/excluir vagas que ela mesma publicou (filtro por `usuario_id` no banco) — vagas importadas do Jooble ou cadastradas pelo admin não aparecem nesse painel. Excluir uma vaga também remove as candidaturas associadas a ela, evitando que uma vaga nova acabe "herdando" candidaturas antigas por reaproveitamento de ID no banco.

## Painel administrativo

Disponível em `/admin.html` (não linkado na navegação pública — acesso direto pela URL). Protegido pelo mesmo `X-Admin-Token` / `ADMIN_TOKEN` usado em `/api/atualizar-agora` (veja abaixo); sem essa variável configurada, o painel fica sempre bloqueado. O token é guardado em `sessionStorage` (não sobrevive ao fechar a aba).

Permite:
- Cadastrar, editar e excluir vagas manualmente (`/api/admin/vagas`).
- Visualizar candidaturas recebidas, a lista de espera e os usuários cadastrados (somente leitura).

## Endpoint administrativo

O endpoint `POST /api/atualizar-agora` (força uma busca de vagas fora do agendamento normal) exige um cabeçalho `X-Admin-Token` com o valor da variável de ambiente `ADMIN_TOKEN`. Sem essa variável configurada, o endpoint fica sempre bloqueado (403). Configure `ADMIN_TOKEN` com um valor secreto próprio caso queira usá-lo — esse mesmo token dá acesso ao painel administrativo (`/admin.html`).

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
