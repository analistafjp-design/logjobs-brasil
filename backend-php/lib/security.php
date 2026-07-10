<?php
declare(strict_types=1);

// Porta 1:1 de backend/security.py (PBKDF2-HMAC-SHA256 + JWT HS256 hand-rolled).
// Mesmo formato de hash ("saltHex$digestHex", 260 000 iterações) e mesmo layout de
// JWT (header.payload.signature em base64url) — por isso as senhas e a lógica de
// verificação continuam idênticas, sem precisar de nenhuma migração de dado.

const PBKDF2_ITERATIONS = 260000;

function hash_password(string $password): string
{
    $salt = random_bytes(16);
    $digest = hash_pbkdf2('sha256', $password, $salt, PBKDF2_ITERATIONS, 32, true);
    return bin2hex($salt) . '$' . bin2hex($digest);
}

function verify_password(string $password, string $passwordHash): bool
{
    $partes = explode('$', $passwordHash);
    if (count($partes) !== 2) {
        return false;
    }
    [$saltHex, $digestHex] = $partes;
    $salt = hex2bin($saltHex);
    if ($salt === false) {
        return false;
    }
    $digest = hash_pbkdf2('sha256', $password, $salt, PBKDF2_ITERATIONS, 32, true);
    return hash_equals($digestHex, bin2hex($digest));
}

function b64url_encode(string $data): string
{
    return rtrim(strtr(base64_encode($data), '+/', '-_'), '=');
}

function b64url_decode(string $data): string
{
    $padded = $data . str_repeat('=', (4 - strlen($data) % 4) % 4);
    return base64_decode(strtr($padded, '-_', '+/'));
}

function encode_jwt(array $payload, string $secret): string
{
    $header = ['alg' => 'HS256', 'typ' => 'JWT'];
    $headerB64 = b64url_encode(json_encode($header, JSON_UNESCAPED_SLASHES));
    $payloadB64 = b64url_encode(json_encode($payload, JSON_UNESCAPED_SLASHES));
    $signingInput = "{$headerB64}.{$payloadB64}";
    $signature = hash_hmac('sha256', $signingInput, $secret, true);
    return "{$signingInput}." . b64url_encode($signature);
}

function decode_jwt(string $token, string $secret): ?array
{
    $partes = explode('.', $token);
    if (count($partes) !== 3) {
        return null;
    }
    [$headerB64, $payloadB64, $signatureB64] = $partes;
    $signingInput = "{$headerB64}.{$payloadB64}";
    $expected = hash_hmac('sha256', $signingInput, $secret, true);
    if (!hash_equals(b64url_encode($expected), $signatureB64)) {
        return null;
    }
    $payload = json_decode(b64url_decode($payloadB64), true);
    if (!is_array($payload)) {
        return null;
    }
    if (isset($payload['exp']) && time() > $payload['exp']) {
        return null;
    }
    return $payload;
}
