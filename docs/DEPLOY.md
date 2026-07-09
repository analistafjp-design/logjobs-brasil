# Deploy e Variáveis de Ambiente — LogJobs Brasil

## Deploy no Render

O `render.yaml` na raiz do projeto já provisiona tudo automaticamente (Blueprint):

```yaml
databases:
  - name: logjobs-db
    plan: free

services:
  - type: web
    name: logjobs-brasil
    runtime: python
    buildCommand: pip install -r backend/requirements.txt
    startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT --app-dir backend
```

Passos:

1. No painel do Render, **New → Blueprint**, aponte para este repositório.
2. O Render lê o `render.yaml`, cria o banco Postgres e o serviço web, e já conecta a variável `DATABASE_URL` entre os dois — nada a configurar manualmente.
3. Configure as variáveis de ambiente opcionais (tabela abaixo) em **Environment** no painel do serviço web.
4. Todo push no branch conectado (`main`) dispara um redeploy automático.

⚠️ **O plano free do Postgres do Render expira em 90 dias** (a Render exclui o banco depois disso). Antes do prazo, faça upgrade do banco para um plano pago, ou migre para outro provedor com free tier sem expiração (ex.: [Neon](https://neon.tech), [Supabase](https://supabase.com)) apontando `DATABASE_URL` para o novo banco.

## Rodando localmente

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --app-dir .
```

Acesse `http://localhost:8000`. Na primeira execução, o SQLite (`logjobs.db`) é criado e populado com vagas e artigos de exemplo.

## Variáveis de ambiente

| Variável | Obrigatória? | Padrão | Efeito |
|---|---|---|---|
| `DATABASE_URL` | Não (produção: sim, via Render) | `sqlite:///./logjobs.db` | String de conexão do banco. Aceita `postgres://` (reescrito automaticamente para `postgresql://`) |
| `LOGJOBS_SECRET_KEY` | **Sim, em produção** | chave de desenvolvimento fixa | Chave HMAC usada para assinar os JWTs (access token e `state` do OAuth). Sem uma chave própria em produção, qualquer um com o código-fonte poderia forjar tokens |
| `ADMIN_TOKEN` | Sim, para usar o painel admin | nenhum (endpoints admin ficam bloqueados) | Token exigido no header `X-Admin-Token` para todos os endpoints `/api/admin/*` |
| `JOOBLE_API_KEY` | Não | nenhum (usa só vagas de exemplo) | Chave da [API do Jooble](https://jooble.org/api/about) para buscar vagas reais |
| `GOOGLE_CLIENT_ID` | Não | nenhum | ID do cliente OAuth do Google Cloud Console |
| `GOOGLE_CLIENT_SECRET` | Não | nenhum | Secret do cliente OAuth |
| `GOOGLE_REDIRECT_URI` | Não (mas recomendado em produção) | `http://localhost:8000/api/auth/google/callback` | Precisa bater exatamente com a URI cadastrada no Google Cloud Console |
| `SITE_URL` | Não | `RENDER_EXTERNAL_URL` ou a URL de produção padrão | Usada no `sitemap.xml`, meta tags de SEO e no link do e-mail de recuperação de senha |
| `SMTP_HOST` | Não | nenhum (recuperação de senha fica indisponível) | Endereço do servidor SMTP para envio de e-mails |
| `SMTP_PORT` | Não | `587` | Porta do servidor SMTP (STARTTLS) |
| `SMTP_USER` | Não | nenhum | Usuário/e-mail de autenticação no SMTP |
| `SMTP_PASSWORD` | Não | nenhum | Senha (ou senha de app) do SMTP |
| `SMTP_FROM_EMAIL` | Não | mesmo valor de `SMTP_USER` | Endereço de remetente exibido nos e-mails |

### Ativando o login com Google

1. Crie um projeto em [console.cloud.google.com](https://console.cloud.google.com) → **APIs e Serviços → Credenciais → Criar credenciais → ID do cliente OAuth** (tipo "Aplicativo da Web").
2. Cadastre a URI de redirecionamento autorizada: `https://<seu-dominio>/api/auth/google/callback`.
3. Configure `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` e `GOOGLE_REDIRECT_URI` no ambiente do serviço.
4. Sem essas variáveis, o login com Google fica automaticamente desativado — `GET /api/auth/google/configurado` retorna `{"configurado": false}` e o botão nem aparece no modal de login.

### Ativando recuperação de senha por e-mail

1. Configure `SMTP_HOST`, `SMTP_USER` e `SMTP_PASSWORD` (e opcionalmente `SMTP_PORT`/`SMTP_FROM_EMAIL`) no ambiente do serviço — funciona com qualquer provedor SMTP (Gmail, Outlook, um relay do SendGrid/Mailgun, etc.). Para Gmail, use uma [senha de app](https://support.google.com/accounts/answer/185833), não a senha normal da conta.
2. Sem essas variáveis, a funcionalidade fica automaticamente desativada — `GET /api/auth/recuperar-senha/configurado` retorna `{"configurado": false}` e o link "Esqueci minha senha" nem aparece no modal de login, mesmo padrão do login com Google.

### Ativando busca de vagas reais (Jooble)

1. Crie uma conta gratuita em [jooble.org/api/about](https://jooble.org/api/about) e obtenha a `JOOBLE_API_KEY`.
2. Configure a variável de ambiente.
3. Apague o `logjobs.db` (local) ou o banco (produção) para forçar nova busca na próxima inicialização — sem isso, o sistema continua funcionando normalmente só com as vagas de exemplo.

## Testes antes de cada deploy

```bash
cd backend
pip install -r requirements-dev.txt
pytest
```

Não é obrigatório para o deploy funcionar (o Render não roda testes automaticamente), mas é fortemente recomendado antes de dar push em mudanças no backend — ver [`MANUAL_DESENVOLVEDOR.md`](./MANUAL_DESENVOLVEDOR.md#testes).
