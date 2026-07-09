# Banco de Dados — LogJobs Brasil

SQLAlchemy ORM (`backend/models.py`). SQLite em desenvolvimento (`logjobs.db`, criado e populado automaticamente na primeira execução), PostgreSQL em produção (Render provisiona junto com o serviço web via `render.yaml`).

Não há um sistema de migrações completo (tipo Alembic): `backend/migrations.py` só adiciona colunas que faltam em bancos já existentes (`ALTER TABLE ... ADD COLUMN`), rodado uma vez no startup. Tabelas novas são criadas automaticamente por `Base.metadata.create_all(bind=engine)`.

## Tabelas

### `usuarios` (`Usuario`)

Candidatos e empresas na mesma tabela, diferenciados por `tipo`.

| Coluna | Tipo | Notas |
|---|---|---|
| `id` | Integer | PK |
| `nome` | String | |
| `email` | String | único |
| `senha_hash` | String | PBKDF2-HMAC-SHA256, formato `salt_hex$digest_hex` |
| `tipo` | String | `"candidato"` \| `"empresa"` |
| `telefone`, `cidade` | String | opcionais |
| `resumo` | String | mini-currículo (candidato) ou descrição (empresa) |
| `habilidades` | String | lista separada por vírgula |
| `pretensao_salarial` | Float | candidato |
| `disponibilidade` | String | candidato: Imediata / 15 dias / 30 dias / A combinar |
| `possui_cnh` | String | categoria da CNH, ou vazio |
| `veiculo_proprio` | String | `"sim"` \| `"nao"` |
| `portfolio_url`, `linkedin_url`, `github_url` | String | opcionais |
| `experiencias_json`, `formacoes_json`, `cursos_json`, `certificados_json`, `idiomas_json` | String | listas serializadas em JSON (evita 5 tabelas para listas curtas) |
| `totp_secret`, `totp_ativado` | String, Integer | 2FA |
| `oauth_provider`, `oauth_id` | String | preenchidos quando a conta é criada/vinculada via Google |
| `candidaturas_vistas_em` | DateTime | empresa: última vez que abriu a lista de candidaturas |
| `criado_em` | DateTime | `server_default=func.now()` |

### `vagas` (`Vaga`)

| Coluna | Tipo | Notas |
|---|---|---|
| `id` | Integer | PK |
| `cargo`, `empresa`, `cidade`, `estado`, `categoria` | String | obrigatórios, indexados |
| `salario` | Float | opcional |
| `modalidade`, `turno`, `tipo_contratacao`, `veiculo` | String | opcionais |
| `descricao`, `beneficios`, `requisitos` | String | opcionais |
| `link` | String | URL externa (vaga do Jooble) |
| `fonte` | String | `"exemplo"` \| `"jooble"` \| `"manual"` \| `"empresa"` |
| `usuario_id` | Integer | dono da vaga (empresa), `NULL` para vagas de exemplo/Jooble/admin |
| `pausada` | Integer | `1` = some da busca pública, continua no painel da empresa |
| `criada_em` | DateTime | |

Constraint única: `(cargo, empresa, cidade)` — evita duplicatas.

### `favoritos` (`Favorito`)

Vagas salvas por um candidato. `(usuario_id, vaga_id)` único.

### `candidaturas` (`Candidatura`)

Candidatura a uma vaga. **Não tem FK para `Usuario`** — guarda `nome`/`email`/`telefone` como contato avulso (permite candidatura sem conta). Isso importa para o chat: a empresa só consegue iniciar uma conversa se existir uma conta com o mesmo e-mail da candidatura.

### `interessados` (`Interessado`)

Lista de espera (candidato ou empresa "quero ser avisado").

### `atualizacoes` (`Atualizacao`)

Histórico de execuções do job periódico do Jooble (quantas vagas novas, total).

### `marcadores` (`Marcador`)

Controla correções/migrações de dados que devem rodar só uma vez (ex.: `correcao_geografica_pais_v1`).

### `artigos` (`Artigo`)

Posts do blog.

### `alertas` (`Alerta`)

Busca salva de um candidato (cargo/categoria/cidade/estado). Sem envio por e-mail — o "alerta" é a contagem de vagas novas compatíveis, calculada ao vivo.

### `refresh_tokens` (`RefreshToken`)

| Coluna | Tipo | Notas |
|---|---|---|
| `id` | Integer | PK |
| `usuario_id` | Integer | dono do token |
| `token_hash` | String | SHA-256 do token — o valor original nunca é guardado |
| `criado_em`, `expira_em` | DateTime | expira em 30 dias |
| `revogado_em` | DateTime | `NULL` = ainda válido; setado no uso (rotação) ou no logout |

### `conversas` (`Conversa`)

Uma conversa por par `(candidato_id, empresa_id)` — não por vaga. `vaga_id` só guarda contexto (qual vaga originou a conversa).

### `mensagens` (`Mensagem`)

| Coluna | Tipo | Notas |
|---|---|---|
| `id` | Integer | PK |
| `conversa_id` | Integer | FK lógica para `Conversa` |
| `remetente_id` | Integer | quem enviou |
| `texto` | String | até 2000 caracteres (validado na API) |
| `lida_em` | DateTime | `NULL` até o destinatário abrir a conversa |
| `criada_em` | DateTime | |

## Relacionamentos (lógicos, não todos com FK física)

```
Usuario 1───N Vaga            (usuario_id, empresa dona)
Usuario 1───N Favorito        (usuario_id)
Vaga    1───N Favorito        (vaga_id)
Vaga    1───N Candidatura     (vaga_id — SEM FK para Usuario)
Usuario 1───N RefreshToken    (usuario_id)
Usuario 1───N Alerta          (usuario_id)
Usuario 1───N Conversa        (candidato_id E empresa_id — dois FKs lógicos)
Vaga    1───N Conversa        (vaga_id, opcional — contexto)
Conversa 1───N Mensagem       (conversa_id)
Usuario 1───N Mensagem        (remetente_id)
```
