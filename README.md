# 🚚 LogJobs Brasil

Portal inteligente de vagas para logística.

📄 Documento oficial do projeto (visão, missão, roadmap e padrão de qualidade): [`docs/PVD.md`](./docs/PVD.md)

📚 Documentação técnica: [Arquitetura](./docs/ARQUITETURA.md) · [Banco de dados](./docs/BANCO_DE_DADOS.md) · [Referência de API](./docs/API.md) · [Deploy e variáveis de ambiente](./docs/DEPLOY.md) · [Manual do desenvolvedor](./docs/MANUAL_DESENVOLVEDOR.md) · [Manual do administrador](./docs/MANUAL_ADMINISTRADOR.md)

## Estrutura

```
logjobs-brasil/
├── docs/
│   ├── PVD.md                    # Project Vision Document (visão de produto)
│   ├── ARQUITETURA.md            # Como o sistema é construído por dentro
│   ├── BANCO_DE_DADOS.md         # Esquema completo das tabelas
│   ├── API.md                    # Referência de todas as rotas
│   ├── DEPLOY.md                 # Deploy no Render + variáveis de ambiente
│   ├── MANUAL_DESENVOLVEDOR.md   # Convenções, como adicionar endpoints/páginas, testes
│   └── MANUAL_ADMINISTRADOR.md   # Painel admin, moderação, LGPD
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

## Testes automatizados

```bash
cd backend
pip install -r requirements-dev.txt
pytest
```

Os testes (`backend/tests/`) usam um banco SQLite temporário próprio, isolado do `logjobs.db` de desenvolvimento — cobrem o fluxo de autenticação (registro, login, refresh token, logout, 2FA) e os endpoints públicos principais (vagas, estatísticas, favoritos, rate limit, proteção do painel admin).

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

## Privacidade e dados pessoais (LGPD)

Na seção "🛡️ Privacidade e meus dados" do perfil, qualquer usuário logado pode:

- **Baixar seus dados** (`GET /api/auth/meus-dados`): exporta em JSON o perfil, favoritos, alertas, candidaturas e (para empresas) vagas publicadas — portabilidade de dados (art. 18 da LGPD).
- **Excluir a própria conta** (`DELETE /api/auth/me`): exige confirmação da senha atual (dispensada para contas criadas via Google), revoga todas as sessões (refresh tokens) e remove em cascata favoritos, alertas e, se for empresa, as vagas publicadas e candidaturas recebidas — mesma lógica de cascata já usada na exclusão de usuários pelo painel administrativo.

## Contas de usuário (candidato / empresa)

Login e cadastro reais estão disponíveis: botão "Entrar" na navbar abre um modal com abas de Entrar/Cadastrar. O cadastro aceita tipo "candidato" ou "empresa" (`POST /api/auth/registro`), login em `POST /api/auth/login`, e `GET /api/auth/me` retorna o usuário autenticado a partir do token.

Senhas são armazenadas com hash PBKDF2-HMAC-SHA256 (salt por usuário) e o token de sessão é um JWT HS256 — ambos implementados só com a biblioteca padrão do Python (`backend/security.py`), sem depender de `passlib[bcrypt]`/`cryptography`, que têm extensões nativas propensas a quebrar entre plataformas diferentes de desenvolvimento/deploy. Configure `LOGJOBS_SECRET_KEY` em produção (sem isso, usa uma chave de desenvolvimento fixa).

O access token (JWT) dura 7 dias, mas a sessão pode durar bem mais que isso: registro, login e login com Google também devolvem um **refresh token** opaco (não é JWT — só um valor aleatório, guardado no banco só como hash SHA-256, nunca em texto puro). `POST /api/auth/refresh` troca um refresh token válido por um novo par (access + refresh) e revoga o antigo — rotação de uso único, então um refresh token vazado/reaproveitado já não funciona mais depois do primeiro uso legítimo. `POST /api/auth/logout` revoga o refresh token da sessão atual. No frontend, o `apiFetch()` (`frontend/js/app.js`) encapsula chamadas autenticadas e renova a sessão sozinho, sem exigir login de novo, sempre que o access token expira.

Usuários logados podem salvar vagas (favoritos): botão de estrela em cada card, endpoints `GET/POST/DELETE /api/favoritos`.

### Recuperação de senha

Link "Esqueci minha senha" no modal de login (`POST /api/auth/recuperar-senha`, e-mail) envia um link de redefinição válido por 1 hora, e `POST /api/auth/redefinir-senha` (página `redefinir-senha.html`) troca a senha a partir desse token. Token opaco de uso único, guardado no banco só como hash SHA-256 (`backend/models.py: TokenRecuperacaoSenha`) — mesmo raciocínio do refresh token. Redefinir a senha revoga todas as sessões ativas (refresh tokens) do usuário, por segurança.

A resposta de `POST /api/auth/recuperar-senha` é sempre a mesma, exista ou não uma conta com aquele e-mail — evita que alguém descubra quais e-mails têm conta testando o endpoint.

Envio de e-mail via SMTP, implementado só com `smtplib`/`email` da biblioteca padrão do Python (`backend/email_sender.py`) — sem depender de SendGrid/Mailgun/SES. Fica **desativado automaticamente** se `SMTP_HOST`/`SMTP_USER`/`SMTP_PASSWORD` não estiverem configurados: `GET /api/auth/recuperar-senha/configurado` retorna `{"configurado": false}` e o link nem aparece no modal de login — mesmo padrão do login com Google, abaixo.

### Login com Google

Implementado em `backend/oauth_google.py` como um fluxo OAuth 2.0 Authorization Code manual, usando só `urllib` da biblioteca padrão (sem `authlib`/`google-auth`) — mesma filosofia do resto da autenticação do projeto. Fica **desativado automaticamente** se as variáveis de ambiente não estiverem configuradas: `GET /api/auth/google/configurado` retorna `{"configurado": false}` e o botão "Continuar com Google" nem aparece no modal de login/cadastro.

Para ativar, configure no servidor:
- `GOOGLE_CLIENT_ID` e `GOOGLE_CLIENT_SECRET` — gerados em [console.cloud.google.com](https://console.cloud.google.com), em "APIs e Serviços → Credenciais → Criar credenciais → ID do cliente OAuth" (tipo "Aplicativo da Web").
- `GOOGLE_REDIRECT_URI` — a URL completa de `GET /api/auth/google/callback` no seu domínio (ex.: `https://logjobs-brasil.onrender.com/api/auth/google/callback`), que também precisa estar cadastrada como "URI de redirecionamento autorizado" no Google Cloud Console.

Fluxo: `GET /api/auth/google/login` redireciona para a tela de consulta do Google com um `state` assinado (JWT curto, `security.encode_jwt`) para proteção contra CSRF — sem precisar guardar nada em sessão/banco entre os dois redirecionamentos. O Google chama de volta `GET /api/auth/google/callback`, que valida o `state`, troca o `code` por um perfil (via `GET https://www.googleapis.com/oauth2/v3/userinfo`), cria a conta se o e-mail ainda não existir (como `tipo: "candidato"`, com uma senha aleatória — a conta só entra por Google até o candidato decidir definir uma senha própria) ou faz login na conta existente com o mesmo e-mail, e redireciona para `frontend/oauth-callback.html#token=...`, que salva a sessão e manda para o perfil.

### Perfil estruturado do candidato

Além do mini-currículo em texto livre, candidatos podem cadastrar: experiências profissionais, formação acadêmica, cursos, certificados, idiomas, CNH, veículo próprio, LinkedIn/GitHub/portfólio. As cinco listas (experiências, formações, cursos, certificados, idiomas) são guardadas como JSON serializado em colunas de texto no `Usuario` (`backend/models.py`) — evita criar cinco tabelas quase idênticas só para listas curtas que ninguém precisa consultar via SQL, e a API continua ergonômica porque o backend faz o `json.dumps`/`json.loads`; quem chama `PATCH /api/auth/me` manda e recebe listas de verdade, não texto.

O frontend (`frontend/js/perfil.js`) usa um único padrão genérico (`CONFIG_LISTAS_CANDIDATO`) para renderizar, adicionar e remover itens das cinco seções, em vez de repetir a mesma lógica cinco vezes — cada remoção/adição reenvia a lista inteira via `PATCH /api/auth/me`.

Um indicador de **completude do perfil** (`GET /api/auth/me` retorna `perfil_completude`, 0–100%) é calculado a partir de quantos desses campos estão preenchidos, e alimenta uma barra de progresso na página de perfil. O texto de experiências e formações também passou a entrar no motor de recomendação de vagas.

### Verificação em duas etapas (2FA)

Qualquer conta pode ativar 2FA por TOTP (o mesmo padrão do Google Authenticator, Authy etc.) na seção "Segurança" do perfil. Implementado só com a biblioteca padrão do Python (`backend/totp.py`, mesma filosofia de `security.py`) — sem SMS/e-mail e sem depender de nenhum serviço externo, então funciona mesmo sem credenciais de terceiros configuradas. A implementação foi validada contra os vetores de teste oficiais do RFC 4226.

Fluxo: `POST /api/auth/2fa/iniciar` gera um segredo e devolve a chave (texto) e a URI `otpauth://` para importar no app autenticador; `POST /api/auth/2fa/confirmar` com o primeiro código de 6 dígitos ativa; a partir daí, `POST /api/auth/login` sem `codigo_totp` responde `{"requer_totp": true}` em vez de emitir o token, e o modal de login pede o código antes de tentar de novo. `POST /api/auth/2fa/desativar` exige a senha atual.

Existe uma página de perfil (`frontend/perfil.html`, acessível pelo nome do usuário na navbar) onde candidatos e empresas editam nome/telefone/cidade/mini-currículo (`PATCH /api/auth/me`) e veem/removem suas vagas salvas.

Candidatos têm campos extras de perfil, só exibidos para `tipo: "candidato"`: habilidades (lista livre separada por vírgula), pretensão salarial, disponibilidade (Imediata/15 dias/30 dias/A combinar) e categoria de CNH — relevantes para a maioria das vagas de logística. As habilidades entram automaticamente no motor de recomendação (próxima seção), somadas ao texto do mini-currículo.

## Recomendação de vagas (IA)

Candidatos com o mini-currículo preenchido recebem uma seção "Vagas recomendadas para você" no perfil, via `GET /api/recomendacoes`. O motor (`backend/recomendacao.py`) é uma correspondência de palavras-chave com pesos por campo (cargo/categoria valem mais que descrição/benefícios) — determinístico e sem depender de nenhuma API externa de IA, já que o projeto não tem chave de LLM configurada. Cada vaga recomendada mostra um percentual de compatibilidade (proporção das palavras-chave do currículo do candidato encontradas na vaga).

### IA sob demanda: análise de perfil, currículo, entrevista e assistente

Mesma filosofia determinística acima, em quatro recursos novos, todos na seção "🤖 IA para você" do perfil (menos o assistente, que é um widget flutuante em todas as páginas) — nenhum roda em segundo plano, só quando o candidato pede:

- **Análise de perfil** (`GET /api/ia/analise-perfil`, `backend/analise_perfil.py`): lista pontos fortes e sugestões de melhoria a partir de um checklist de campos preenchidos (mini-currículo, habilidades, experiências, formação, CNH, idiomas, links, disponibilidade).
- **Gerador de currículo** (`GET /api/ia/gerar-curriculo`): monta um currículo em texto plano a partir dos dados já cadastrados no perfil, pronto para copiar ou imprimir (`Ctrl+P` do navegador) — sem depender de nenhuma biblioteca de PDF no cliente.
- **Simulador de entrevista** (`GET /api/ia/simulador-entrevista?categoria=`, `backend/entrevista.py`): banco de perguntas fixo por categoria de vaga (Motorista, Entregador, Estoquista, Conferente, Auxiliar Logístico, Operador) + perguntas comportamentais gerais, com uma dica sobre o método STAR. É um simulador de prática — não há avaliação automática de respostas, isso exigiria uma IA de verdade.
- **Assistente virtual** (`POST /api/ia/assistente`, `backend/assistente.py`): widget flutuante (💬, canto inferior direito, em qualquer página) que responde dúvidas comuns por correspondência de palavras-chave contra uma lista de intenções (candidatura, favoritos, 2FA, chat, currículo, recomendações, entrevista, anunciar vaga, alertas, login com Google). Deliberadamente descrito como central de ajuda, não como um chat conversacional livre.

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

Cada alerta também mostra um badge "+N novas" com as vagas que passaram a corresponder ao critério desde a última vez que o candidato clicou em "Ver vagas" (`POST /api/alertas/{id}/marcar-visto`) — mesma abordagem usada na notificação de candidaturas do painel de empresas, calculada ao vivo a partir do timestamp da vaga, sem nenhum serviço externo de notificação.

**Histórico de candidaturas** (`/api/minhas-candidaturas`): lista as candidaturas do usuário logado, casadas pelo e-mail com a tabela `candidaturas` (que não exige login para se candidatar). O formulário de candidatura agora pré-preenche nome/e-mail/telefone quando o candidato está logado, para que o histórico funcione de forma consistente.

**Histórico de buscas**: as últimas 5 buscas ficam salvas no navegador (`localStorage`, sem backend) e aparecem como chips clicáveis abaixo da busca na home.

## Chat entre candidato e empresa

Disponível em `/chat.html` (link 💬 na navbar quando logado). Uma única conversa por par (candidato, empresa) — não por vaga, para não proliferar threads quando o candidato se candidata a várias vagas da mesma empresa.

Quem pode iniciar uma conversa:
- **Candidato**, a partir do modal de candidatura de uma vaga com empresa dona (botão "💬 Enviar mensagem para a empresa", só aparece quando a vaga foi publicada pelo painel de empresas, não para vagas de exemplo/Jooble/admin).
- **Empresa**, a partir da lista de candidaturas recebidas de uma vaga (botão "💬 Mensagem"), resolvendo o candidato pelo e-mail da candidatura — como `Candidatura` não tem vínculo direto com `Usuario` (permite candidatura sem conta), se não existir uma conta com esse e-mail, a empresa recebe um aviso de que o candidato ainda não tem conta na plataforma.

Envio de mensagem é sempre via REST (`POST /api/chat/conversas/{id}/mensagens`); um WebSocket (`/ws/chat/{id}`) entrega em tempo real para quem estiver com a tela da conversa aberta — nunca conecta sozinho/automaticamente. Autenticado via token JWT na query string, já que o `WebSocket` nativo do navegador não permite headers customizados no handshake. Requer a dependência `websockets` no `requirements.txt` (Uvicorn sem ela responde 404 a qualquer tentativa de conexão).

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

A empresa recebe uma notificação em painel (badge "+N novas" ao lado de "Candidaturas recebidas") quando há candidaturas mais recentes que a última vez que ela abriu a lista de candidatos de alguma vaga. Não há e-mail/push — é a mesma abordagem honesta usada nos alertas de vaga do candidato: um contador calculado ao vivo, sem depender de nenhum serviço externo de notificação. O timestamp "visto em" (`POST /api/empresa/candidaturas/marcar-vistas`) usa o relógio do próprio banco (`func.now()`), não o do servidor Python, para não ficar "à frente" do timestamp de uma candidatura criada no mesmo instante.

Uma empresa só enxerga e só pode editar/excluir vagas que ela mesma publicou (filtro por `usuario_id` no banco) — vagas importadas do Jooble ou cadastradas pelo admin não aparecem nesse painel. Excluir uma vaga também remove as candidaturas associadas a ela, evitando que uma vaga nova acabe "herdando" candidaturas antigas por reaproveitamento de ID no banco.

Além disso, o painel permite:
- **Pausar/reativar** uma vaga (`POST /api/empresa/vagas/{id}/pausar` e `/reativar`): uma vaga pausada some da busca pública (`GET /api/vagas` filtra `pausada`) mas continua no painel da empresa, sem precisar excluir e recriar.
- **Renovar** uma vaga (`POST /api/empresa/vagas/{id}/renovar`): reativa (se estava pausada) e atualiza a data de publicação para agora, fazendo a vaga voltar ao topo da ordenação por "mais recentes".
- **Filtrar** a lista de vagas por texto (cargo/cidade) e por status (ativa/pausada) (`GET /api/empresa/vagas?q=...&status=...`).
- **Exportar candidaturas em CSV** de todas as vagas da empresa (`GET /api/empresa/candidaturas-exportar`).

## Painel administrativo

Disponível em `/admin.html` (não linkado na navegação pública — acesso direto pela URL). Protegido pelo mesmo `X-Admin-Token` / `ADMIN_TOKEN` usado em `/api/atualizar-agora` (veja abaixo); sem essa variável configurada, o painel fica sempre bloqueado. O token é guardado em `sessionStorage` (não sobrevive ao fechar a aba).

Permite:
- Cadastrar, editar e excluir vagas manualmente (`/api/admin/vagas`).
- Visualizar candidaturas recebidas e a lista de espera (somente leitura).
- Buscar e excluir contas de usuário (`GET/DELETE /api/admin/usuarios`) — útil para remover contas falsas/spam. Excluir uma empresa também remove as vagas que ela publicou e as candidaturas dessas vagas, para não deixar vagas "órfãs" na busca pública.

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
