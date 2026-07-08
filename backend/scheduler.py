import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.exc import IntegrityError

from database import SessionLocal
from jooble_client import JOOBLE_API_KEY, buscar_vagas_proxima_categoria, classificar_categoria
from models import Atualizacao, Marcador, Vaga

logger = logging.getLogger("logjobs.scheduler")

INTERVALO_MINUTOS = 20
DIAS_EXPIRACAO_VAGA = 60
CHAVE_CORRECAO_GEOGRAFICA = "correcao_geografica_pais_v1"


def aplicar_correcao_geografica_uma_vez():
    """Correção pontual: antes da busca especificar 'Brasil' explicitamente,
    siglas de estado brasileiro (MT, PA, MS, SC, AL) colidiam com códigos
    postais dos EUA, e o Jooble devolveu vagas americanas (ex.: "Maquinista"
    na Montana, EUA) marcadas como se fossem brasileiras. Isso remove, uma
    única vez, todas as vagas do Jooble buscadas antes dessa correção, para
    que a próxima coleta (já corrigida) repovoe o banco do zero."""
    db = SessionLocal()
    try:
        if db.query(Marcador).filter(Marcador.chave == CHAVE_CORRECAO_GEOGRAFICA).first():
            return
        removidas = db.query(Vaga).filter(Vaga.fonte == "jooble").delete()
        db.add(Marcador(chave=CHAVE_CORRECAO_GEOGRAFICA))
        db.commit()
        if removidas:
            logger.warning("Correção geográfica: removidas %s vagas buscadas antes da correção.", removidas)
    finally:
        db.close()


def reclassificar_vagas_sem_categoria():
    """Corrige vagas do Jooble com categoria genérica ('Importado (Jooble)' do
    código antigo, ou 'Logística' quando nenhuma palavra-chave bateu na época),
    tentando de novo com os padrões de classificação mais atuais."""
    db = SessionLocal()
    try:
        vagas = (
            db.query(Vaga)
            .filter(Vaga.categoria.in_(["Importado (Jooble)", "Logística"]))
            .all()
        )
        atualizadas = 0
        for vaga in vagas:
            nova_categoria = classificar_categoria(vaga.cargo)
            if nova_categoria != vaga.categoria:
                vaga.categoria = nova_categoria
                atualizadas += 1
        if atualizadas:
            db.commit()
            logger.info("Reclassificadas %s vagas com categoria genérica.", atualizadas)
    finally:
        db.close()


def remover_vagas_expiradas():
    """Remove vagas reais (fonte='jooble') com mais de DIAS_EXPIRACAO_VAGA dias.
    Vagas de logística têm alta rotatividade; sem isso, o banco acumularia
    para sempre anúncios que a empresa provavelmente já fechou."""
    limite = datetime.utcnow() - timedelta(days=DIAS_EXPIRACAO_VAGA)
    db = SessionLocal()
    try:
        removidas = (
            db.query(Vaga)
            .filter(Vaga.fonte == "jooble", Vaga.criada_em < limite)
            .delete(synchronize_session=False)
        )
        if removidas:
            db.commit()
            logger.info("Removidas %s vagas expiradas (mais de %s dias).", removidas, DIAS_EXPIRACAO_VAGA)
    finally:
        db.close()


def remover_vagas_exemplo_se_ha_reais():
    """Remove as vagas de exemplo assim que houver pelo menos uma vaga real (fonte='jooble') no banco,
    para não misturar dados ilustrativos com vagas de verdade."""
    db = SessionLocal()
    try:
        tem_vagas_reais = db.query(Vaga).filter(Vaga.fonte == "jooble").first() is not None
        if tem_vagas_reais:
            removidas = db.query(Vaga).filter(Vaga.fonte == "exemplo").delete()
            if removidas:
                db.commit()
                logger.info("Removidas %s vagas de exemplo (vagas reais já disponíveis).", removidas)
    finally:
        db.close()


def atualizar_vagas_periodicamente():
    """Busca vagas novas no Jooble (uma categoria por execução, alternando entre
    elas) e insere apenas as que ainda não existem. Sem JOOBLE_API_KEY
    configurada, apenas registra que a execução foi pulada."""
    db = SessionLocal()
    vagas_novas = 0

    try:
        indice_categoria = db.query(Atualizacao).count()
        vagas_encontradas = buscar_vagas_proxima_categoria(indice_categoria)

        chaves_existentes = {
            (v.cargo, v.empresa, v.cidade)
            for v in db.query(Vaga.cargo, Vaga.empresa, Vaga.cidade).all()
        }

        for dados in vagas_encontradas:
            chave = (dados["cargo"], dados["empresa"], dados["cidade"])
            if chave in chaves_existentes:
                continue
            chaves_existentes.add(chave)

            # Insert individualmente: a constraint única no banco protege contra
            # duplicatas mesmo se outra instância inserir a mesma vaga em paralelo.
            db.add(Vaga(**dados))
            try:
                db.commit()
                vagas_novas += 1
            except IntegrityError:
                db.rollback()

        db.add(Atualizacao(
            jooble_configurado=1 if JOOBLE_API_KEY else 0,
            vagas_novas=vagas_novas,
            vagas_totais=db.query(Vaga).count(),
        ))
        db.commit()
        logger.info("Atualização concluída: %s vagas novas.", vagas_novas)
    except Exception:
        db.rollback()
        logger.exception("Falha ao atualizar vagas periodicamente")
    finally:
        db.close()

    remover_vagas_exemplo_se_ha_reais()
    remover_vagas_expiradas()


scheduler = BackgroundScheduler()


def iniciar_agendador():
    if not scheduler.running:
        # IMPORTANTE: não passar next_run_time=None aqui. O APScheduler trata isso
        # como "cria o job já pausado" — ele nunca dispara sozinho, mesmo com o
        # scheduler rodando. Foi assim desde a criação do agendador (commit
        # b138702) e nunca disparou em produção: as vagas nunca eram atualizadas
        # nem expiradas automaticamente. Sem passar o parâmetro, o job roda
        # normalmente a cada INTERVALO_MINUTOS, como o resto do código já assume.
        scheduler.add_job(
            atualizar_vagas_periodicamente,
            trigger="interval",
            minutes=INTERVALO_MINUTOS,
            id="atualizar_vagas",
            replace_existing=True,
        )
        scheduler.start()


def parar_agendador():
    if scheduler.running:
        scheduler.shutdown(wait=False)
