<?php
declare(strict_types=1);

// Front controller único: todas as requisições /api/*, /sitemap.xml, /robots.txt e
// /vagas/{id} são reescritas para cá pelo .htaccess da raiz do site (ver .htaccess.example).

require_once __DIR__ . '/../lib/config.php';
require_once __DIR__ . '/../lib/db.php';
require_once __DIR__ . '/../lib/security.php';
require_once __DIR__ . '/../lib/helpers.php';
require_once __DIR__ . '/../lib/auth.php';
require_once __DIR__ . '/../lib/totp.php';
require_once __DIR__ . '/../lib/email_sender.php';
require_once __DIR__ . '/../lib/oauth_google.php';
require_once __DIR__ . '/../lib/jooble_client.php';
require_once __DIR__ . '/../lib/recomendacao.php';
require_once __DIR__ . '/../lib/analise_perfil.php';
require_once __DIR__ . '/../lib/entrevista.php';
require_once __DIR__ . '/../lib/assistente.php';
require_once __DIR__ . '/../lib/seo.php';
require_once __DIR__ . '/../lib/router.php';

aplicar_cabecalhos_seguranca();

if (($_SERVER['REQUEST_METHOD'] ?? '') === 'OPTIONS') {
    http_response_code(204);
    exit;
}

require_once __DIR__ . '/../routes/publico.php';
require_once __DIR__ . '/../routes/admin.php';
require_once __DIR__ . '/../routes/candidaturas.php';
require_once __DIR__ . '/../routes/auth.php';
require_once __DIR__ . '/../routes/candidato.php';
require_once __DIR__ . '/../routes/empresa.php';
require_once __DIR__ . '/../routes/chat.php';

$caminho = parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH);
$metodo = $_SERVER['REQUEST_METHOD'] ?? 'GET';

try {
    despachar($metodo, $caminho);
} catch (Throwable $e) {
    error_log((string) $e);
    json_erro(500, 'Erro interno do servidor');
}
