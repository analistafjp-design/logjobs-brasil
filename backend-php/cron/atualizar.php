<?php
declare(strict_types=1);

// Substitui o agendador em processo (backend/scheduler.py, BackgroundScheduler) — que não
// existe em hospedagem compartilhada. Configure no hPanel da Hostinger, em "Cron Jobs":
//   - Se a Hostinger oferecer executar comando PHP diretamente (mais seguro, recomendado):
//       php /home/SEU_USUARIO/public_html/backend-php/cron/atualizar.php
//     a cada 20 minutos (ou o intervalo mínimo que o plano permitir — o site funciona mesmo
//     que só rode a cada 1h, só demora mais para "última atualização" mudar).
//   - Se só oferecer chamar uma URL: configure ADMIN_TOKEN em config.local.php e agende
//       curl "https://seudominio.com.br/backend-php/cron/atualizar.php?token=SEU_ADMIN_TOKEN"
//     (o .htaccess de exemplo já bloqueia acesso a outros arquivos de backend-php/, mas cron/
//     fica de fora do bloqueio de propósito, protegido por esse token em vez disso).

require_once __DIR__ . '/../lib/config.php';
require_once __DIR__ . '/../lib/db.php';
require_once __DIR__ . '/../lib/jooble_client.php';
require_once __DIR__ . '/../lib/scheduler.php';

$viaCli = PHP_SAPI === 'cli';

if (!$viaCli) {
    $tokenEsperado = config('ADMIN_TOKEN');
    $tokenRecebido = $_GET['token'] ?? '';
    if (!$tokenEsperado || !hash_equals($tokenEsperado, $tokenRecebido)) {
        http_response_code(403);
        header('Content-Type: text/plain; charset=utf-8');
        echo "Acesso negado.\n";
        exit;
    }
    header('Content-Type: text/plain; charset=utf-8');
}

aplicar_correcao_geografica_uma_vez();
atualizar_vagas_periodicamente();
reclassificar_vagas_sem_categoria();

echo "Atualização executada em " . gmdate('Y-m-d H:i:s') . " UTC.\n";
