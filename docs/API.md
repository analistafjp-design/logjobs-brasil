# Referência de API — LogJobs Brasil

Base URL local: `http://localhost:8000`. Em produção: `https://logjobs-brasil.onrender.com`.

Documentação interativa (Swagger/OpenAPI), gerada automaticamente pelo FastAPI, sempre disponível em `/docs` (Swagger UI) e `/redoc` — útil para testar chamadas na hora. Este documento é um resumo de leitura rápida; o `/docs` tem os schemas exatos de cada request/response.

**Autenticação:** `Authorization: Bearer <access_token>` no header, exceto onde indicado como público. Veja o fluxo completo em [`ARQUITETURA.md`](./ARQUITETURA.md#autenticação-e-sessão).

## Sistema

| Método | Rota | Auth | Descrição |
|---|---|---|---|
| GET | `/health` | público | Health check (`{"status": "ok"}`) |
| GET | `/api/status` | público | Última execução do job do Jooble, contadores |
| GET | `/docs`, `/redoc`, `/openapi.json` | público | Documentação interativa (Swagger/ReDoc) |

## Vagas (público)

| Método | Rota | Auth | Descrição |
|---|---|---|---|
| GET | `/api/vagas` | público | Lista com filtros (cargo, cidade, estado, categoria, modalidade, turno, tipo de contratação, benefício, faixa salarial), ordenação e paginação |
| GET | `/api/vagas/{id}` | público | Detalhe de uma vaga (inclui `usuario_id` — indica se tem empresa dona para chat) |
| GET | `/api/sugestoes?tipo=cargo\|cidade\|empresa&q=` | público | Autocomplete para a busca |
| GET | `/api/categorias` | público | Lista de categorias existentes |
| GET | `/vagas/{id}` | público | Página HTML server-side da vaga (SEO) |
| POST | `/api/candidaturas` | público | Envia candidatura (honeypot anti-bot em `empresa_no_meio`) |
| POST | `/api/interessados` | público | Lista de espera (candidato/empresa) |

## Estatísticas, dashboard e ranking (público)

| Método | Rota | Descrição |
|---|---|---|
| GET | `/api/estatisticas` | Total de vagas, empresas, cidades |
| GET | `/api/dashboard` | Por categoria, por estado, top empresas, salário médio por categoria, evolução |
| GET | `/api/ranking` | Ranking de empresas por número de vagas |
| GET | `/api/salarios` | Estatísticas salariais por categoria |

## Blog (público)

| Método | Rota | Descrição |
|---|---|---|
| GET | `/api/blog` | Lista de artigos |
| GET | `/api/blog/{slug}` | Artigo específico |

## Autenticação

| Método | Rota | Auth | Descrição |
|---|---|---|---|
| POST | `/api/auth/registro` | público | Cria conta (`tipo`: candidato/empresa). Retorna `access_token` + `refresh_token` |
| POST | `/api/auth/login` | público | Login. Se 2FA ativado e sem `codigo_totp`, retorna `{"requer_totp": true}` |
| POST | `/api/auth/refresh` | público (requer refresh token) | Troca refresh token por novo par (rotação de uso único) |
| POST | `/api/auth/logout` | público (requer refresh token) | Revoga o refresh token informado |
| GET | `/api/auth/recuperar-senha/configurado` | público | Se a recuperação de senha por e-mail está disponível neste servidor |
| POST | `/api/auth/recuperar-senha` | público (rate limit) | Envia e-mail com link de redefinição, se o e-mail existir (resposta idêntica em ambos os casos, para não revelar quais e-mails têm conta) |
| POST | `/api/auth/redefinir-senha` | público (token de uso único) | Define nova senha a partir do token do e-mail; revoga todas as sessões ativas do usuário |
| GET | `/api/auth/me` | 🔒 | Dados do usuário autenticado |
| PATCH | `/api/auth/me` | 🔒 | Atualiza perfil (nome, telefone, cidade, resumo, habilidades, experiências, formações, cursos, certificados, idiomas, etc.) |
| GET | `/api/auth/meus-dados` | 🔒 | Exporta em JSON todos os dados pessoais do usuário (LGPD, portabilidade) |
| DELETE | `/api/auth/me` | 🔒 (+ senha) | Exclui a própria conta e dados associados (LGPD, eliminação); revoga todas as sessões |
| GET | `/api/auth/google/configurado` | público | Se o login com Google está disponível neste servidor |
| GET | `/api/auth/google/login` | público | Redireciona para o Google (OAuth) |
| GET | `/api/auth/google/callback` | público | Callback do Google, cria/loga a conta |
| POST | `/api/auth/2fa/iniciar` | 🔒 | Gera segredo TOTP + URI `otpauth://` |
| POST | `/api/auth/2fa/confirmar` | 🔒 | Confirma o primeiro código e ativa o 2FA |
| POST | `/api/auth/2fa/desativar` | 🔒 (+ senha) | Desativa o 2FA |

## Favoritos e candidaturas do candidato

| Método | Rota | Auth | Descrição |
|---|---|---|---|
| GET | `/api/favoritos` | 🔒 | Vagas salvas |
| POST/DELETE | `/api/favoritos/{vaga_id}` | 🔒 | Salvar/remover vaga dos favoritos |
| GET | `/api/minhas-candidaturas` | 🔒 | Histórico de candidaturas (casadas por e-mail) |
| GET | `/api/alertas` | 🔒 | Buscas salvas |
| POST | `/api/alertas` | 🔒 | Cria alerta |
| DELETE | `/api/alertas/{id}` | 🔒 | Remove alerta |
| POST | `/api/alertas/{id}/marcar-visto` | 🔒 | Marca vagas do alerta como vistas |
| GET | `/api/conquistas` | 🔒 | Badges de gamificação do candidato |

## IA sob demanda

Todas determinísticas, sem chave de LLM externa — ver [`ARQUITETURA.md`](./ARQUITETURA.md#ia-sob-demanda).

| Método | Rota | Auth | Descrição |
|---|---|---|---|
| GET | `/api/recomendacoes` | 🔒 (candidato) | Vagas recomendadas por correspondência de palavras-chave com o perfil |
| GET | `/api/ia/analise-perfil` | 🔒 (candidato) | Pontos fortes, lacunas e sugestões de melhoria do perfil |
| GET | `/api/ia/gerar-curriculo` | 🔒 (candidato) | Baixa currículo formatado em texto (`.txt`) |
| GET | `/api/ia/simulador-entrevista?categoria=&quantidade=` | 🔒 | Perguntas de prática para entrevista |
| GET | `/api/ia/simulador-entrevista/categorias` | público | Categorias disponíveis no simulador |
| POST | `/api/ia/assistente` | público (rate limit) | Central de ajuda por palavras-chave (`{"pergunta": "..."}`) |

## Chat

Ver [`ARQUITETURA.md`](./ARQUITETURA.md#chat-em-tempo-real) para o fluxo completo.

| Método | Rota | Auth | Descrição |
|---|---|---|---|
| POST | `/api/chat/conversas` | 🔒 | Inicia/reaproveita conversa. Candidato: `{vaga_id, mensagem}`. Empresa: `{candidatura_id, mensagem}` |
| GET | `/api/chat/conversas` | 🔒 | Lista conversas do usuário (com última mensagem e não lidas) |
| GET | `/api/chat/conversas/{id}/mensagens` | 🔒 (participante) | Histórico da conversa (marca como lidas) |
| POST | `/api/chat/conversas/{id}/mensagens` | 🔒 (participante) | Envia mensagem |
| WS | `/ws/chat/{id}?token=` | 🔒 (participante, token na query string) | Entrega em tempo real enquanto a tela está aberta |

## Painel da empresa

Todas exigem `tipo == "empresa"`.

| Método | Rota | Descrição |
|---|---|---|
| GET | `/api/empresa/vagas?q=&status=` | Vagas da empresa (com contagem de candidaturas) |
| POST | `/api/empresa/vagas` | Cria vaga |
| PATCH/DELETE | `/api/empresa/vagas/{id}` | Edita/exclui vaga |
| POST | `/api/empresa/vagas/{id}/pausar` | Pausa (some da busca pública) |
| POST | `/api/empresa/vagas/{id}/reativar` | Reativa |
| POST | `/api/empresa/vagas/{id}/renovar` | Reativa + volta ao topo de "mais recentes" |
| GET | `/api/empresa/candidaturas/{vaga_id}` | Candidaturas recebidas para uma vaga |
| GET | `/api/empresa/candidaturas-exportar` | Exporta todas as candidaturas em CSV |
| GET | `/api/empresa/estatisticas` | Total de vagas, candidaturas, candidaturas novas |
| POST | `/api/empresa/candidaturas/marcar-vistas` | Marca candidaturas como vistas |

## Painel administrativo

Todas exigem header `X-Admin-Token` igual à variável de ambiente `ADMIN_TOKEN` (ver [`DEPLOY.md`](./DEPLOY.md)).

| Método | Rota | Descrição |
|---|---|---|
| GET | `/api/admin/verificar` | Testa se o token é válido |
| GET | `/api/admin/vagas?q=` | Lista todas as vagas |
| POST | `/api/admin/vagas` | Cria vaga manualmente |
| PATCH/DELETE | `/api/admin/vagas/{id}` | Edita/exclui vaga |
| GET | `/api/admin/candidaturas` | Todas as candidaturas |
| GET | `/api/admin/interessados` | Lista de espera |
| GET | `/api/admin/usuarios?q=` | Todos os usuários |
| DELETE | `/api/admin/usuarios/{id}` | Exclui usuário (e vagas/candidaturas dependentes, se empresa) |
| GET | `/api/admin/auditoria` | Últimas ações administrativas registradas (criar/editar/excluir vaga, excluir usuário, atualizar vagas) |
| POST | `/api/atualizar-agora` | Dispara a busca de vagas do Jooble imediatamente |

## SEO

| Método | Rota | Descrição |
|---|---|---|
| GET | `/sitemap.xml` | Sitemap para motores de busca |
| GET | `/robots.txt` | Robots.txt |
| GET | `/favicon.ico` | Ícone do site |

## Rate limiting

Endpoints sensíveis (login, registro, refresh, candidaturas, chat, assistente, admin) são limitados por IP em memória (`backend/rate_limit.py`) — resposta `429` ao exceder o limite. Não é distribuído entre instâncias; suficiente para uma única instância (plano free).
