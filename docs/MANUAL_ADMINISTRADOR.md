# Manual do Administrador — LogJobs Brasil

## Acessando o painel administrativo

1. Configure a variável de ambiente `ADMIN_TOKEN` (veja [`DEPLOY.md`](./DEPLOY.md)) — sem ela, os endpoints `/api/admin/*` ficam permanentemente bloqueados (`403`), mesmo para quem sabe a URL.
2. Acesse `/admin.html` e informe o token quando solicitado. O painel guarda o token localmente no navegador para as próximas visitas.

⚠️ **Trate o `ADMIN_TOKEN` como uma senha mestra.** Qualquer pessoa com ele tem acesso total: pode ver e excluir usuários, editar/excluir qualquer vaga, ver todas as candidaturas e interessados. Nunca compartilhe o token por canais inseguros nem o deixe em código versionado.

## O que o painel administrativo permite

| Ação | Onde |
|---|---|
| Ver estatísticas gerais (usuários, vagas, candidaturas) | Painel principal |
| Criar, editar, pausar e excluir qualquer vaga | Aba de vagas |
| Ver todas as candidaturas recebidas na plataforma | Aba de candidaturas |
| Ver a lista de espera (interessados) | Aba de interessados |
| Ver e excluir contas de usuário | Aba de usuários |
| Forçar uma busca de vagas no Jooble imediatamente | Botão "Atualizar agora" |

**Excluir uma conta de empresa também exclui todas as vagas publicadas por ela e as candidaturas recebidas nessas vagas** — não há como desfazer essa ação pelo painel; se precisar recuperar dados, restaure a partir de um backup do banco.

## Painel da empresa (para quem gerencia contas de empresa)

Diferente do painel administrativo, o painel da empresa (`/empresa.html`) é acessado com uma conta normal do tipo "empresa" (sem token especial) e permite à própria empresa:

- Publicar, editar, pausar, reativar e renovar suas vagas.
- Ver e exportar (CSV) as candidaturas recebidas.
- Enviar mensagem para um candidato que se candidatou (abre uma conversa no chat).
- Ver estatísticas próprias (candidaturas novas desde a última visita).

Se um usuário perdeu acesso à própria conta de empresa (esqueceu a senha, por exemplo), hoje a única forma de recuperar é pelo suporte diretamente no banco de dados — não há fluxo de "esqueci minha senha" implementado ainda (veja `contato@logjobsbrasil.com.br` no rodapé do site).

## Moderação de conteúdo

Não há fila de moderação automática — vagas publicadas por empresas ficam visíveis imediatamente. Para remover uma vaga inadequada:

1. Acesse `/admin.html` → aba de vagas.
2. Localize a vaga (busca por cargo/empresa/cidade) e exclua ou pause.

Para banir uma empresa que publica conteúdo abusivo repetidamente, exclua a conta dela na aba de usuários (isso já remove as vagas publicadas por ela).

## Privacidade e dados pessoais (LGPD)

Dados pessoais armazenados: nome, e-mail, telefone, cidade e, para candidatos, dados de currículo (experiências, formação, habilidades). Senhas nunca são armazenadas em texto puro (hash PBKDF2-HMAC-SHA256 com salt por usuário).

Para atender a um pedido de exclusão de dados (direito do titular sob a LGPD):

1. Localize o usuário em `/admin.html` → aba de usuários.
2. Exclua a conta — isso remove o registro do `Usuario`, seus favoritos e alertas. Se for uma conta de empresa, também remove as vagas publicadas e as candidaturas recebidas nelas.
3. **Atenção:** candidaturas enviadas por essa pessoa a vagas de *outras* empresas continuam existindo na tabela `candidaturas` (não têm vínculo direto com a conta, só nome/e-mail/telefone informados no momento da candidatura) — para uma exclusão completa, é preciso também localizar e remover manualmente essas candidaturas pelo e-mail, via acesso direto ao banco.
4. Não há logs de acesso/auditoria automatizados hoje além dos logs padrão do servidor (stdout, capturados pelo Render) — para uma trilha de auditoria formal, isso precisaria ser implementado.

## Variáveis de ambiente relevantes para administração

Ver a tabela completa em [`DEPLOY.md`](./DEPLOY.md#variáveis-de-ambiente). As mais relevantes para quem administra (em vez de desenvolve):

- `ADMIN_TOKEN` — acesso ao painel administrativo.
- `JOOBLE_API_KEY` — se ausente, o site funciona só com vagas de exemplo (nenhuma vaga real é buscada).
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` — se ausentes, o botão de login com Google simplesmente não aparece (não é um erro, é o comportamento esperado sem essas credenciais configuradas).
