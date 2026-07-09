# Manual do Desenvolvedor — LogJobs Brasil

## Primeiros passos

```bash
git clone <repositório>
cd logjobs-brasil/backend
pip install -r requirements-dev.txt   # inclui requirements.txt + pytest/httpx
uvicorn main:app --reload --app-dir .
```

Acesse `http://localhost:8000`. O próprio backend serve o frontend (`frontend/`) como arquivos estáticos — não precisa de nenhum servidor separado, build step ou bundler.

## Convenções do projeto

- **Nomes em português** para tudo que é domínio do negócio (variáveis, funções, rotas, mensagens de erro para o usuário) — só nomes de bibliotecas/padrões técnicos ficam em inglês.
- **Sem dependências pesadas quando dá para evitar.** JWT, hash de senha e TOTP são implementados só com a biblioteca padrão do Python (`security.py`, `totp.py`) em vez de `PyJWT`/`passlib[bcrypt]`, que puxam extensões nativas (`cryptography`/`cffi`/`bcrypt`) propensas a quebrar por incompatibilidade de versão entre plataformas de desenvolvimento e deploy. Isso vale como princípio geral: antes de adicionar uma dependência nova, pergunte se dá para resolver com a biblioteca padrão.
- **Um arquivo por responsabilidade** no backend (`security.py`, `totp.py`, `rate_limit.py`, `oauth_google.py`, `chat_manager.py`, `analise_perfil.py`, `entrevista.py`, `assistente.py`...). `main.py` só define rotas; a lógica de suporte vive nesses módulos.
- **Frontend sem framework.** Cada página tem seu próprio `<page>.js`; código realmente compartilhado (autenticação, tema, modal, toast, `escapeHtml`, `apiFetch`) vive em `app.js`, carregado antes do script da página em todo `<page>.html`.
- **Escape sempre no frontend, na hora de renderizar** (`escapeHtml()`), não ao salvar no banco — permite editar o dado depois sem lidar com escaping duplicado.
- **Migração aditiva só quando necessário.** Colunas novas em tabelas existentes precisam de uma entrada em `migrations.py` (`ALTER TABLE ... ADD COLUMN`) para não quebrar bancos já em produção. Tabelas novas não precisam de nada — `Base.metadata.create_all()` cria sozinho.

## Adicionando um novo endpoint

1. Se for um recurso novo (não um endpoint a mais em algo existente), crie um módulo dedicado em `backend/` com a lógica pura (sem FastAPI/rotas) — veja `analise_perfil.py` ou `entrevista.py` como exemplo.
2. Importe o módulo em `main.py` e adicione a rota, seguindo o padrão dos endpoints vizinhos (dependências `Depends(auth.usuario_atual)` para autenticado, `Depends(get_db)` para banco, `limitar_por_ip(...)` para endpoints públicos/sensíveis).
3. Se o endpoint recebe corpo (`POST`/`PATCH`), defina um `BaseModel` do Pydantic com `Field(max_length=...)` nos campos de texto livre — protege contra payload desproporcional. **Cuidado:** um `min_length` no Pydantic dispara *antes* do código do endpoint rodar, então uma validação que hoje tem mensagem de erro amigável (ex.: senha curta) viraria uma lista de erros genérica do FastAPI se movida para o Pydantic. Prefira manter esse tipo de validação no corpo do endpoint quando já existir uma mensagem amigável.
4. Escreva testes em `backend/tests/` (veja a seção Testes abaixo).
5. Se o frontend precisa consumir o endpoint, prefira `apiFetch()` (`app.js`) em vez de `fetch` manual com `Authorization: Bearer` — ele renova a sessão sozinho se o access token tiver expirado.

## Adicionando um novo módulo de página no frontend

1. Crie `frontend/<pagina>.html` seguindo a estrutura de `perfil.html` (mesmo `<head>`, mesma navbar, `<script src="js/app.js">` antes de `<script src="js/<pagina>.js">`).
2. Crie `frontend/js/<pagina>.js` com a lógica específica da página.
3. CSS específico vai em `frontend/css/style.css`, numa seção nova com o cabeçalho `/* ===== Nome ===== */` — não crie um arquivo CSS por página.
4. Se a página precisa aparecer para usuários logados, adicione o link em `renderAreaConta()` (`app.js`) — um único ponto de injeção, evita duplicar HTML de navbar em cada página.

## Chat (WebSocket)

- Envio de mensagem é sempre via `POST /api/chat/conversas/{id}/mensagens` — o WebSocket (`/ws/chat/{id}`) só existe para *entrega* em tempo real a quem está com a tela aberta.
- **Atenção:** WebSocket no Uvicorn exige a lib `websockets` (ou `wsproto`) instalada. Sem ela, o Uvicorn "puro" responde 404 a qualquer tentativa de upgrade — e isso só aparece testando com um servidor real rodando (`TestClient`/`websocket_connect` do FastAPI não passa pelo protocolo HTTP de upgrade de verdade, então testes pytest sozinhos não pegam esse problema). Sempre valide mudanças no chat com o servidor real + navegador, não só com pytest.
- O gerenciador de conexões (`chat_manager.py`) é em memória — não funciona com múltiplas instâncias do backend rodando ao mesmo tempo (não é o caso do plano free do Render, que roda uma única instância).

## Testes

```bash
cd backend
pip install -r requirements-dev.txt
pytest
```

- `backend/tests/conftest.py` cria um banco SQLite temporário isolado (nunca toca no `logjobs.db` de desenvolvimento) e limpa o rate limiter entre testes.
- Os testes compartilham uma única sessão de banco (fixture `client` é `scope="session"`) — sempre gere e-mails/nomes únicos (`uuid.uuid4()`) ao criar usuários/vagas em um teste novo, para não colidir com dados de outro teste.
- Para testar WebSocket: `client.websocket_connect(f"/ws/chat/{id}?token={token}")` funciona no TestClient, mas **não substitui** testar com servidor real (ver seção Chat acima).
- Para mudanças de frontend, rode o servidor local e verifique no navegador (ideal: Playwright headless) — testes de API não garantem que a tela realmente funciona.

## Estrutura de testes existente

| Arquivo | Cobertura |
|---|---|
| `test_auth.py` | Registro, login, refresh token, logout, 2FA |
| `test_api.py` | Vagas, estatísticas, favoritos, rate limit, proteção do admin |
| `test_chat.py` | Iniciar conversa (das duas formas), controle de acesso, não lidas, WebSocket |
| `test_ia.py` | Análise de perfil, gerador de currículo, simulador de entrevista, assistente |

## Checklist antes de abrir um PR / dar push

- [ ] `pytest` passa (todos os testes, não só os do que você mexeu)
- [ ] Testou no navegador (não só via API) se mexeu em frontend
- [ ] Não duplicou uma função/componente que já existe em `app.js`
- [ ] Campos de texto livre novos em endpoints têm `Field(max_length=...)`
- [ ] Não quebrou nenhuma funcionalidade existente (rode as páginas relevantes no navegador)
