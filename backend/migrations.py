import logging

from sqlalchemy import inspect

logger = logging.getLogger("logjobs.migrations")


def adicionar_colunas_faltantes(engine, Base):
    """Rede de segurança simples: Base.metadata.create_all() só cria tabelas que
    não existem, nunca adiciona colunas novas em tabelas já existentes. Como o
    projeto não usa uma ferramenta de migração (Alembic), esta função compara
    os modelos com o banco real e adiciona qualquer coluna que estiver faltando,
    evitando que o site quebre silenciosamente após deploys que mudam o schema.

    Não lida com mudanças mais complexas (renomear coluna, mudar tipo, adicionar
    constraint em tabela já populada) — para isso, uma migração manual ou a
    adoção de Alembic continua sendo necessária."""
    inspetor = inspect(engine)

    for tabela in Base.metadata.sorted_tables:
        if not inspetor.has_table(tabela.name):
            continue

        colunas_existentes = {col["name"] for col in inspetor.get_columns(tabela.name)}

        for coluna in tabela.columns:
            if coluna.name in colunas_existentes:
                continue

            tipo_sql = coluna.type.compile(engine.dialect)
            with engine.begin() as conn:
                conn.exec_driver_sql(
                    f'ALTER TABLE "{tabela.name}" ADD COLUMN "{coluna.name}" {tipo_sql}'
                )
            logger.warning(
                "Coluna '%s' não existia na tabela '%s' — adicionada automaticamente.",
                coluna.name, tabela.name,
            )
