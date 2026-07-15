<?php
declare(strict_types=1);

// Porta de backend/oauth_google.py (OAuth 2.0 Authorization Code flow), usando cURL
// (extensão padrão do PHP em qualquer hospedagem, inclusive Hostinger).

const GOOGLE_AUTORIZACAO_URL = 'https://accounts.google.com/o/oauth2/v2/auth';
const GOOGLE_TOKEN_URL = 'https://oauth2.googleapis.com/token';
const GOOGLE_USERINFO_URL = 'https://www.googleapis.com/oauth2/v3/userinfo';

class ErroTrocaGoogle extends Exception {}

function google_configurado(): bool
{
    return (bool) (config('GOOGLE_CLIENT_ID') && config('GOOGLE_CLIENT_SECRET'));
}

function google_redirect_uri(): string
{
    return config('GOOGLE_REDIRECT_URI', 'http://localhost:8000/api/auth/google/callback');
}

function google_url_autorizacao(string $state): string
{
    $params = [
        'client_id' => config('GOOGLE_CLIENT_ID'),
        'redirect_uri' => google_redirect_uri(),
        'response_type' => 'code',
        'scope' => 'openid email profile',
        'state' => $state,
        'prompt' => 'select_account',
    ];
    return GOOGLE_AUTORIZACAO_URL . '?' . http_build_query($params);
}

function curl_json(string $url, ?array $postFields = null, ?string $bearer = null): array
{
    $ch = curl_init($url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 10);
    if ($postFields !== null) {
        curl_setopt($ch, CURLOPT_POST, true);
        curl_setopt($ch, CURLOPT_POSTFIELDS, http_build_query($postFields));
        curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: application/x-www-form-urlencoded']);
    }
    if ($bearer !== null) {
        curl_setopt($ch, CURLOPT_HTTPHEADER, ["Authorization: Bearer {$bearer}"]);
    }
    $resposta = curl_exec($ch);
    $erro = curl_error($ch);
    curl_close($ch);
    if ($resposta === false) {
        throw new ErroTrocaGoogle($erro);
    }
    $dados = json_decode($resposta, true);
    if (!is_array($dados)) {
        throw new ErroTrocaGoogle('Resposta inválida do Google');
    }
    return $dados;
}

function google_trocar_codigo_por_perfil(string $code): array
{
    $tokens = curl_json(GOOGLE_TOKEN_URL, [
        'client_id' => config('GOOGLE_CLIENT_ID'),
        'client_secret' => config('GOOGLE_CLIENT_SECRET'),
        'code' => $code,
        'redirect_uri' => google_redirect_uri(),
        'grant_type' => 'authorization_code',
    ]);
    if (!isset($tokens['access_token'])) {
        throw new ErroTrocaGoogle('Google não retornou access_token');
    }
    return curl_json(GOOGLE_USERINFO_URL, null, $tokens['access_token']);
}
