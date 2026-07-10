<?php
declare(strict_types=1);

require_once __DIR__ . '/db.php';

function aplicar_cabecalhos_seguranca(): void
{
    header('X-Content-Type-Options: nosniff');
    header('X-Frame-Options: DENY');
    header('Referrer-Policy: strict-origin-when-cross-origin');
    header('Permissions-Policy: geolocation=(self), camera=(), microphone=()');
    if (!empty($_SERVER['HTTPS'])) {
        header('Strict-Transport-Security: max-age=63072000; includeSubDomains');
    }
    header('Access-Control-Allow-Origin: *');
    header('Access-Control-Allow-Methods: GET, POST, PATCH, DELETE, OPTIONS');
    header('Access-Control-Allow-Headers: Content-Type, Authorization, X-Admin-Token');
}

function json_saida($dados, int $status = 200): void
{
    http_response_code($status);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode($dados, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

function json_erro(int $status, string $detail): void
{
    json_saida(['detail' => $detail], $status);
}

/** @return array<string,mixed> */
function corpo_json(): array
{
    $raw = file_get_contents('php://input');
    if ($raw === false || $raw === '') {
        return [];
    }
    $dados = json_decode($raw, true);
    return is_array($dados) ? $dados : [];
}

function campo_obrigatorio(array $dados, string $chave): mixed
{
    if (!isset($dados[$chave]) || $dados[$chave] === '') {
        json_erro(422, "Campo obrigatório ausente: {$chave}");
    }
    return $dados[$chave];
}

function ip_cliente(): string
{
    return $_SERVER['REMOTE_ADDR'] ?? 'desconhecido';
}

/** Porta de rate_limit.py: mesma janela deslizante, mas persistida em tabela
 * (cada requisição PHP roda num processo novo em hospedagem compartilhada, não
 * dá para guardar isso em memória do processo como no Python original). */
function limitar_por_ip(string $chave, int $maxPedidos = 5, int $janelaSegundos = 600): void
{
    $ip = ip_cliente();
    $agora = time();
    $limite = $agora - $janelaSegundos;

    $pdo = db();
    $pdo->prepare('DELETE FROM limites_taxa WHERE chave = ? AND ip = ? AND criado_em < ?')
        ->execute([$chave, $ip, $limite]);

    $stmt = $pdo->prepare('SELECT COUNT(*) AS total FROM limites_taxa WHERE chave = ? AND ip = ?');
    $stmt->execute([$chave, $ip]);
    $total = (int) $stmt->fetch()['total'];

    if ($total >= $maxPedidos) {
        json_erro(429, 'Muitas tentativas. Aguarde alguns minutos e tente novamente.');
    }

    $pdo->prepare('INSERT INTO limites_taxa (chave, ip, criado_em) VALUES (?, ?, ?)')
        ->execute([$chave, $ip, $agora]);
}

function registrar_auditoria(string $acao, ?string $detalhes = null): void
{
    db()->prepare('INSERT INTO logs_auditoria (acao, detalhes, ip) VALUES (?, ?, ?)')
        ->execute([$acao, $detalhes, ip_cliente()]);
}
