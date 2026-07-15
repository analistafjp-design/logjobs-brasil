<?php
declare(strict_types=1);

require_once __DIR__ . '/security.php';
require_once __DIR__ . '/db.php';

const ACCESS_TOKEN_EXPIRE_SECONDS = 60 * 60 * 24 * 7;   // 7 dias
const REFRESH_TOKEN_EXPIRE_SECONDS = 60 * 60 * 24 * 30;  // 30 dias
const RECUPERACAO_SENHA_EXPIRE_SECONDS = 60 * 60;        // 1 hora

function secret_key(): string
{
    return config('LOGJOBS_SECRET_KEY', 'dev-secret-change-in-production');
}

function criar_token(int $usuarioId): string
{
    return encode_jwt(['sub' => (string) $usuarioId, 'exp' => time() + ACCESS_TOKEN_EXPIRE_SECONDS], secret_key());
}

function hash_token(string $token): string
{
    return hash('sha256', $token);
}

function criar_refresh_token(int $usuarioId): string
{
    $token = bin2hex(random_bytes(36));
    $stmt = db()->prepare(
        'INSERT INTO refresh_tokens (usuario_id, token_hash, expira_em) VALUES (?, ?, ?)'
    );
    $expiraEm = gmdate('Y-m-d H:i:s', time() + REFRESH_TOKEN_EXPIRE_SECONDS);
    $stmt->execute([$usuarioId, hash_token($token), $expiraEm]);
    return $token;
}

/** @return array{0: array, 1: string}|null [usuario, novoRefreshToken] */
function rotacionar_refresh_token(string $token): ?array
{
    $stmt = db()->prepare('SELECT * FROM refresh_tokens WHERE token_hash = ?');
    $stmt->execute([hash_token($token)]);
    $registro = $stmt->fetch();
    if (!$registro || $registro['revogado_em'] !== null) {
        return null;
    }
    if (strtotime($registro['expira_em'] . ' UTC') < time()) {
        return null;
    }

    $usuario = buscar_usuario_por_id((int) $registro['usuario_id']);
    if (!$usuario) {
        return null;
    }

    db()->prepare('UPDATE refresh_tokens SET revogado_em = ? WHERE id = ?')
        ->execute([gmdate('Y-m-d H:i:s'), $registro['id']]);

    $novoToken = criar_refresh_token($usuario['id']);
    return [$usuario, $novoToken];
}

function revogar_refresh_token(string $token): void
{
    $stmt = db()->prepare('SELECT id, revogado_em FROM refresh_tokens WHERE token_hash = ?');
    $stmt->execute([hash_token($token)]);
    $registro = $stmt->fetch();
    if ($registro && $registro['revogado_em'] === null) {
        db()->prepare('UPDATE refresh_tokens SET revogado_em = ? WHERE id = ?')
            ->execute([gmdate('Y-m-d H:i:s'), $registro['id']]);
    }
}

function revogar_todos_refresh_tokens(int $usuarioId): void
{
    db()->prepare('UPDATE refresh_tokens SET revogado_em = ? WHERE usuario_id = ? AND revogado_em IS NULL')
        ->execute([gmdate('Y-m-d H:i:s'), $usuarioId]);
}

function criar_token_recuperacao_senha(int $usuarioId): string
{
    $token = bin2hex(random_bytes(24));
    $expiraEm = gmdate('Y-m-d H:i:s', time() + RECUPERACAO_SENHA_EXPIRE_SECONDS);
    db()->prepare('INSERT INTO tokens_recuperacao_senha (usuario_id, token_hash, expira_em) VALUES (?, ?, ?)')
        ->execute([$usuarioId, hash_token($token), $expiraEm]);
    return $token;
}

function validar_e_consumir_token_recuperacao(string $token): ?array
{
    $stmt = db()->prepare('SELECT * FROM tokens_recuperacao_senha WHERE token_hash = ?');
    $stmt->execute([hash_token($token)]);
    $registro = $stmt->fetch();
    if (!$registro || $registro['usado_em'] !== null) {
        return null;
    }
    if (strtotime($registro['expira_em'] . ' UTC') < time()) {
        return null;
    }
    $usuario = buscar_usuario_por_id((int) $registro['usuario_id']);
    if (!$usuario) {
        return null;
    }
    db()->prepare('UPDATE tokens_recuperacao_senha SET usado_em = ? WHERE id = ?')
        ->execute([gmdate('Y-m-d H:i:s'), $registro['id']]);
    return $usuario;
}

function buscar_usuario_por_id(int $id): ?array
{
    $stmt = db()->prepare('SELECT * FROM usuarios WHERE id = ?');
    $stmt->execute([$id]);
    $usuario = $stmt->fetch();
    return $usuario ?: null;
}

function buscar_usuario_por_email(string $email): ?array
{
    $stmt = db()->prepare('SELECT * FROM usuarios WHERE email = ?');
    $stmt->execute([$email]);
    $usuario = $stmt->fetch();
    return $usuario ?: null;
}

function bearer_token(): ?string
{
    $header = $_SERVER['HTTP_AUTHORIZATION'] ?? '';
    if (stripos($header, 'Bearer ') === 0) {
        return substr($header, 7);
    }
    return null;
}

/** Levanta 401 (via json_erro + exit) se não houver usuário autenticado válido. */
function usuario_atual(): array
{
    $token = bearer_token();
    if (!$token) {
        json_erro(401, 'Credenciais inválidas ou expiradas');
    }
    $payload = decode_jwt($token, secret_key());
    if (!$payload || !isset($payload['sub'])) {
        json_erro(401, 'Credenciais inválidas ou expiradas');
    }
    $usuario = buscar_usuario_por_id((int) $payload['sub']);
    if (!$usuario) {
        json_erro(401, 'Credenciais inválidas ou expiradas');
    }
    return $usuario;
}

function usuario_atual_opcional(): ?array
{
    $token = bearer_token();
    if (!$token) {
        return null;
    }
    $payload = decode_jwt($token, secret_key());
    if (!$payload || !isset($payload['sub'])) {
        return null;
    }
    return buscar_usuario_por_id((int) $payload['sub']);
}

function verificar_admin(): void
{
    limitar_por_ip('admin', 30, 600);
    $esperado = config('ADMIN_TOKEN');
    $recebido = $_SERVER['HTTP_X_ADMIN_TOKEN'] ?? '';
    if (!$esperado || !hash_equals($esperado, $recebido)) {
        json_erro(403, 'Token de administrador inválido ou ausente');
    }
}
