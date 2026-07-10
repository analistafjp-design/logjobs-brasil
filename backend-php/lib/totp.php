<?php
declare(strict_types=1);

// Porta 1:1 de backend/totp.py (TOTP RFC 6238, HMAC-SHA1, sem dependências externas).

const TOTP_PERIODO_SEGUNDOS = 30;
const TOTP_DIGITOS = 6;
const TOTP_JANELA_TOLERANCIA = 1;

function totp_gerar_segredo(): string
{
    return rtrim(base32_encode(random_bytes(20)), '=');
}

function base32_encode(string $data): string
{
    $alfabeto = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
    $bits = '';
    foreach (str_split($data) as $byte) {
        $bits .= str_pad(decbin(ord($byte)), 8, '0', STR_PAD_LEFT);
    }
    $saida = '';
    foreach (str_split($bits, 5) as $grupo) {
        $grupo = str_pad($grupo, 5, '0', STR_PAD_RIGHT);
        $saida .= $alfabeto[bindec($grupo)];
    }
    $resto = strlen($saida) % 8;
    if ($resto !== 0) {
        $saida .= str_repeat('=', 8 - $resto);
    }
    return $saida;
}

function base32_decode(string $segredo): string
{
    $alfabeto = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
    $segredo = rtrim(strtoupper($segredo), '=');
    $bits = '';
    foreach (str_split($segredo) as $char) {
        $pos = strpos($alfabeto, $char);
        if ($pos === false) {
            continue;
        }
        $bits .= str_pad(decbin($pos), 5, '0', STR_PAD_LEFT);
    }
    $bytes = '';
    foreach (str_split($bits, 8) as $byte) {
        if (strlen($byte) === 8) {
            $bytes .= chr(bindec($byte));
        }
    }
    return $bytes;
}

function totp_hotp(string $segredo, int $contador): string
{
    $chave = base32_decode($segredo);
    $msg = pack('J', $contador); // 64-bit big-endian
    $digest = hash_hmac('sha1', $msg, $chave, true);
    $offset = ord($digest[19]) & 0x0F;
    $codigo = (
        ((ord($digest[$offset]) & 0x7F) << 24)
        | (ord($digest[$offset + 1]) << 16)
        | (ord($digest[$offset + 2]) << 8)
        | ord($digest[$offset + 3])
    ) % (10 ** TOTP_DIGITOS);
    return str_pad((string) $codigo, TOTP_DIGITOS, '0', STR_PAD_LEFT);
}

function totp_verificar(string $segredo, string $codigo, ?int $tempo = null): bool
{
    if (!$segredo || !$codigo || !ctype_digit($codigo) || strlen($codigo) !== TOTP_DIGITOS) {
        return false;
    }
    $tempo = $tempo ?? time();
    $contadorAtual = intdiv($tempo, TOTP_PERIODO_SEGUNDOS);
    for ($delta = -TOTP_JANELA_TOLERANCIA; $delta <= TOTP_JANELA_TOLERANCIA; $delta++) {
        if (hash_equals(totp_hotp($segredo, $contadorAtual + $delta), $codigo)) {
            return true;
        }
    }
    return false;
}

function totp_uri_otpauth(string $email, string $segredo, string $emissor = 'LogJobs Brasil'): string
{
    $label = rawurlencode("{$emissor}:{$email}");
    $params = http_build_query([
        'secret' => $segredo,
        'issuer' => $emissor,
        'algorithm' => 'SHA1',
        'digits' => TOTP_DIGITOS,
        'period' => TOTP_PERIODO_SEGUNDOS,
    ]);
    return "otpauth://totp/{$label}?{$params}";
}
