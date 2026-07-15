# Migração para hospedagem compartilhada (Hostinger) — PHP + MySQL

Este diretório (`backend-php/`) é uma reescrita completa do backend Python/FastAPI
(`backend/`) em PHP puro + MySQL, para rodar em hospedagem compartilhada comum (a
maioria dos planos da Hostinger só executa PHP/MySQL, não Python).

**O backend Python em `backend/` continua existindo e funcionando normalmente no
Render — nada foi removido de lá.** Esta é uma segunda implementação, lado a lado,
para quem quiser hospedar no plano compartilhado da Hostinger em vez do Render.
O frontend (`frontend/`) é o **mesmo** para os dois — mesmos arquivos HTML/CSS/JS,
mesmos endpoints `/api/...`, sem nenhuma alteração de UI.

## O que foi portado 1:1 (mesmo comportamento, mesmos dados)

- Hash de senha: PBKDF2-HMAC-SHA256, 260 000 iterações, mesmo formato de hash
  (`saltHex$digestHex`) — **as senhas já cadastradas continuam funcionando sem
  nenhuma migração**, porque o algoritmo é idêntico byte a byte.
- Autenticação JWT (HS256, mesma assinatura/formato), refresh token com rotação,
  recuperação de senha por e-mail (token de uso único).
- Verificação em duas etapas (TOTP, RFC 6238) — compatível com Google
  Authenticator/Authy, igual ao original.
- Login com Google (OAuth 2.0).
- Todos os endpoints de vagas, candidaturas, favoritos, alertas, conquistas,
  recomendação de vagas, análise de perfil, gerador de currículo, simulador de
  entrevista, assistente virtual (central de ajuda), blog, painel de empresa,
  painel admin, exportação de dados (LGPD), auditoria.
- Cabeçalhos de segurança (HSTS, CSP, X-Frame-Options etc.), CORS, rate limiting
  por IP (agora persistido em tabela — hospedagem compartilhada não mantém
  estado em memória entre requisições como o processo Python original).
- SEO: `sitemap.xml`, `robots.txt`, página individual de vaga com JSON-LD
  (`JobPosting`) para indexação no Google Vagas.
- Integração com a API do Jooble (busca de vagas reais), se você configurar
  `JOOBLE_API_KEY`.

## O que mudou de verdade (limitações reais da hospedagem compartilhada)

1. **Chat em tempo real (WebSocket) → polling.** Hospedagem compartilhada não
   mantém processos de longa duração, então não dá para manter uma conexão
   WebSocket aberta. As mensagens continuam funcionando normalmente (enviar e
   receber), mas a tela de chat busca mensagens novas a cada 5 segundos em vez
   de receber instantaneamente. `frontend/js/chat.js` foi ajustado para tentar
   WebSocket primeiro (funciona se você mantiver o Render) e usar polling como
   reforço automático sempre — o mesmo arquivo funciona nos dois backends sem
   nenhuma configuração.

2. **Agendador automático (atualização de vagas a cada 20 min) → cron job do
   painel da Hostinger.** Não existe processo em segundo plano em hospedagem
   compartilhada; um Cron Job do hPanel chama `backend-php/cron/atualizar.php`
   periodicamente. Ver seção "Configurar o cron job" abaixo.

3. **Rate limiting** passou de memória do processo para uma tabela
   (`limites_taxa`) no banco — mesmo comportamento, só que agora funciona
   corretamente mesmo que a hospedagem rode múltiplos processos PHP em
   paralelo (o que memória local não garantiria).

4. **Envio de e-mail (recuperação de senha)** foi reimplementado como um
   cliente SMTP mínimo em PHP puro (sem biblioteca externa), já que PHP não
   tem um equivalente embutido ao `smtplib` do Python. Funciona com qualquer
   provedor SMTP padrão (Gmail, Outlook, etc.) — mesma configuração
   (`SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`).

Nada de funcionalidade foi removido — os dois pontos acima (chat e agendador)
continuam fazendo a mesma coisa pelo ponto de vista de quem usa o site, só que
por um mecanismo diferente por trás.

## Passo a passo do deploy na Hostinger

### 1. Criar o banco de dados MySQL

No hPanel: **Bancos de dados → Bancos de dados MySQL** → crie um banco e um
usuário com todas as permissões nesse banco. Anote nome do banco, usuário, senha
e host (geralmente `localhost`).

### 2. Configurar `config.local.php`

Copie `backend-php/config.local.php.example` para `backend-php/config.local.php`
e preencha:

- `DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASS`: dados do banco criado no passo 1.
- `LOGJOBS_SECRET_KEY`: gere um valor aleatório próprio, por exemplo rodando
  localmente `php -r "echo bin2hex(random_bytes(32)), PHP_EOL;"`. **Nunca**
  reaproveite o valor de exemplo do arquivo.
- `ADMIN_TOKEN`: um token seu, para acessar o painel admin e o cron job.
- `SITE_URL`: `https://logjobsbrasil.com.br` (ou o domínio que você configurar).

**`config.local.php` nunca deve ser enviado a lugar nenhum público** (guarda a
senha do banco e a chave secreta) — o `.htaccess` de exemplo já bloqueia acesso
via navegador a esse arquivo, mas cuidado ao fazer backup/versionar o projeto.

### 3. Subir os arquivos

**Opção automática (recomendada):** o workflow
`.github/workflows/deploy-hostinger.yml` gera, a cada push na `main`, uma
branch `hostinger-deploy` já com a estrutura achatada abaixo (conteúdo de
`frontend/` na raiz, `backend-php/` do lado e `.htaccess` prontos). Na tela
"Implante de GitHub" do hPanel, selecione essa branch (`hostinger-deploy`) em
vez da `main` — cada push feito na `main` atualiza o site automaticamente. O
`config.local.php` continua sendo criado à mão direto no servidor (passo 2),
nunca faz parte dessa branch gerada.

**Opção manual:** copiar os arquivos você mesmo, seguindo a estrutura final
dentro de `public_html/` no servidor:

```
public_html/
├── .htaccess              ← copiado de backend-php/htaccess.example
├── index.html, css/, js/, ... (tudo que já está em frontend/)
└── backend-php/
    ├── api/
    ├── lib/
    ├── routes/
    ├── cron/
    ├── seed/
    ├── schema.sql
    ├── setup.php
    └── config.local.php   ← criado no passo 2, NUNCA no repositório público
```

Ou seja: o conteúdo de `frontend/` vai para a raiz do `public_html`, e a pasta
`backend-php/` inteira vai dentro do `public_html`, lado a lado.

### 4. Rodar a instalação do banco

Acesse `https://seudominio.com.br/backend-php/setup.php` no navegador uma
única vez — isso cria as tabelas e popula as vagas/artigos de exemplo. A
página mostra um relatório do que foi feito.

**Depois de rodar com sucesso, apague ou renomeie `setup.php`** — deixá-lo
acessível permite recriar/repovoar as tabelas.

### 5. Ativar o `.htaccess`

Copie `backend-php/htaccess.example` para `public_html/.htaccess` (a raiz do
site). Ele:
- Bloqueia acesso direto às pastas internas do backend (`lib/`, `routes/`,
  `seed/`, `schema.sql`, `config.local.php`, `setup.php`).
- Redireciona `/api/*`, `/sitemap.xml`, `/robots.txt`, `/favicon.ico` e
  `/vagas/{id}` para o roteador PHP.
- Deixa todo o resto (HTML/CSS/JS) sendo servido normalmente como arquivo
  estático, sem nenhuma regra extra.

### 6. Configurar o cron job (atualização automática de vagas)

No hPanel: **Avançado → Cron Jobs**. Duas opções, dependendo do que o plano
contratado permitir:

- **Executar comando PHP diretamente** (mais seguro, preferível):
  ```
  php /home/SEU_USUARIO/public_html/backend-php/cron/atualizar.php
  ```
- **Chamar uma URL** (se só isso estiver disponível): configure `ADMIN_TOKEN`
  em `config.local.php` e agende:
  ```
  curl "https://seudominio.com.br/backend-php/cron/atualizar.php?token=SEU_ADMIN_TOKEN"
  ```

Intervalo recomendado: a cada 20 minutos (ou o mínimo que o plano permitir —
mesmo rodando de hora em hora, o site funciona normalmente, só demora mais
para a "última atualização" avançar).

### 7. Testar

- `https://seudominio.com.br/health` → deve responder `{"status":"ok"}`.
- `https://seudominio.com.br/` → home carregando vagas normalmente.
- Cadastro, login, candidatura, painel admin (com o `ADMIN_TOKEN` configurado).
- `https://seudominio.com.br/backend-php/api/index.php` **não** deve ser
  acessível diretamente por esse caminho depois do `.htaccess` ativo — só
  através de `/api/...`.

## Domínio

Aponte `logjobsbrasil.com.br` para os servidores de nome (nameservers) da
Hostinger, ou apenas os registros DNS do painel de domínios, seguindo as
instruções que aparecem ao vincular o domínio ao plano de hospedagem no
hPanel — isso é feito pelo painel deles, sem nada específico deste projeto.

## E o backend Python/Render?

Continua existindo e funcionando em `backend/` — nada foi apagado ou alterado.
Se você decidir usar a Hostinger, pode desligar o serviço no Render depois de
confirmar que tudo funciona na hospedagem nova; se preferir manter os dois
(por exemplo, um como backup), lembre que são **bancos de dados separados** —
cadastros feitos em um não aparecem automaticamente no outro.
