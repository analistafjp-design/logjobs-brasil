import logging

from apscheduler.schedulers.background import BackgroundScheduler

from database import SessionLocal
from jooble_client import JOOBLE_API_KEY, buscar_vagas_todas_regioes
from models import Atualizacao, Vaga

logger = logging.getLogger("logjobs.scheduler")

INTERVALO_MINUTOS = 20


def atualizar_vagas_periodicamente():
    """Busca vagas novas no Jooble em várias regiões e insere apenas as que ainda não existem.
    Sem JOOBLE_API_KEY configurada, apenas registra que a execução foi pulada."""
    db = SessionLocal()
    vagas_novas = 0

    try:
        vagas_encontradas = buscar_vagas_todas_regioes()

        chaves_existentes = {
            (v.cargo, v.empresa, v.cidade)
            for v in db.query(Vaga.cargo, Vaga.empresa, Vaga.cidade).all()
        }

        for dados in vagas_encontradas:
            chave = (dados["cargo"], dados["empresa"], dados["cidade"])
            if chave in chaves_existentes:
                continue
            db.add(Vaga(**dados))
            chaves_existentes.add(chave)
            vagas_novas += 1

        db.add(Atualizacao(
            jooble_configurado=1 if JOOBLE_API_KEY else 0,
            vagas_novas=vagas_novas,
            vagas_totais=db.query(Vaga).count() + vagas_novas,
        ))
        db.commit()
        logger.info("Atualização concluída: %s vagas novas.", vagas_novas)
    except Exception:
        db.rollback()
        logger.exception("Falha ao atualizar vagas periodicamente")
    finally:
        db.close()


scheduler = BackgroundScheduler()


def iniciar_agendador():
    if not scheduler.running:
        scheduler.add_job(
            atualizar_vagas_periodicamente,
            trigger="interval",
            minutes=INTERVALO_MINUTOS,
            id="atualizar_vagas",
            replace_existing=True,
            next_run_time=None,
        )
        scheduler.start()


def parar_agendador():
    if scheduler.running:
        scheduler.shutdown(wait=False)
