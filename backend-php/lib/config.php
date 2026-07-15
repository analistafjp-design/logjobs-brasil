<?php
// Configuração de ambiente. Em hospedagem compartilhada (Hostinger) normalmente não dá
// para setar variáveis de ambiente reais pelo painel — por isso o config real vive em
// config.local.php (fora do git, copiado a partir de config.local.php.example no deploy).
// Nunca commitar config.local.php: ele guarda a senha do banco e a chave secreta do JWT.

declare(strict_types=1);

$local = __DIR__ . '/../config.local.php';
if (!file_exists($local)) {
    http_response_code(500);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode([
        'erro' => 'config.local.php não encontrado. Copie config.local.php.example para '
            . 'config.local.php e preencha com os dados reais do banco MySQL da Hostinger '
            . 'e uma LOGJOBS_SECRET_KEY própria (nunca use o valor de exemplo em produção).',
    ]);
    exit;
}

require $local;

// Getters com o mesmo padrão do os.getenv(..., default) do backend Python original.
function config(string $chave, ?string $padrao = null): ?string
{
    if (defined($chave)) {
        return constant($chave);
    }
    return $padrao;
}
