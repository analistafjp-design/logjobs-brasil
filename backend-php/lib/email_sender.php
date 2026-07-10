<?php
declare(strict_types=1);

// Porta de backend/email_sender.py. Python usa smtplib da lib padrão; PHP não tem
// equivalente embutido, então isso implementa um cliente SMTP mínimo (EHLO/STARTTLS/
// AUTH LOGIN/MAIL FROM/RCPT TO/DATA) via sockets — funciona com qualquer provedor
// SMTP padrão (Gmail, Outlook, etc.) na porta 587 com STARTTLS, sem nenhuma lib externa.

class ErroEnvioEmail extends Exception {}

function email_configurado(): bool
{
    return (bool) (config('SMTP_HOST') && config('SMTP_USER') && config('SMTP_PASSWORD'));
}

function smtp_ler_resposta($socket): string
{
    $resposta = '';
    while ($linha = fgets($socket, 515)) {
        $resposta .= $linha;
        if (isset($linha[3]) && $linha[3] === ' ') {
            break;
        }
    }
    return $resposta;
}

function smtp_comando($socket, string $comando, int $codigoEsperado): string
{
    fwrite($socket, $comando . "\r\n");
    $resposta = smtp_ler_resposta($socket);
    if ((int) substr($resposta, 0, 3) !== $codigoEsperado) {
        throw new ErroEnvioEmail("Resposta SMTP inesperada para \"{$comando}\": {$resposta}");
    }
    return $resposta;
}

function enviar_email(string $destinatario, string $assunto, string $corpoTexto): void
{
    if (!email_configurado()) {
        throw new ErroEnvioEmail('SMTP não configurado neste servidor');
    }

    $host = config('SMTP_HOST');
    $porta = (int) config('SMTP_PORT', '587');
    $usuario = config('SMTP_USER');
    $senha = config('SMTP_PASSWORD');
    $remetente = config('SMTP_FROM_EMAIL') ?: $usuario;

    $socket = @stream_socket_client("tcp://{$host}:{$porta}", $errno, $errstr, 10);
    if (!$socket) {
        throw new ErroEnvioEmail("Não foi possível conectar ao SMTP: {$errstr}");
    }

    try {
        smtp_ler_resposta($socket); // banner 220
        smtp_comando($socket, "EHLO logjobsbrasil.com.br", 250);
        smtp_comando($socket, "STARTTLS", 220);
        if (!stream_socket_enable_crypto($socket, true, STREAM_CRYPTO_METHOD_TLS_CLIENT)) {
            throw new ErroEnvioEmail('Falha ao iniciar TLS com o servidor SMTP');
        }
        smtp_comando($socket, "EHLO logjobsbrasil.com.br", 250);
        smtp_comando($socket, "AUTH LOGIN", 334);
        smtp_comando($socket, base64_encode($usuario), 334);
        smtp_comando($socket, base64_encode($senha), 235);
        smtp_comando($socket, "MAIL FROM:<{$remetente}>", 250);
        smtp_comando($socket, "RCPT TO:<{$destinatario}>", 250);
        smtp_comando($socket, "DATA", 354);

        $cabecalhos = "Subject: {$assunto}\r\n"
            . "From: {$remetente}\r\n"
            . "To: {$destinatario}\r\n"
            . "MIME-Version: 1.0\r\n"
            . "Content-Type: text/plain; charset=utf-8\r\n";
        $corpoEscapado = preg_replace('/^\./m', '..', $corpoTexto);
        smtp_comando($socket, $cabecalhos . "\r\n" . $corpoEscapado . "\r\n.", 250);
        smtp_comando($socket, "QUIT", 221);
    } catch (ErroEnvioEmail $e) {
        fclose($socket);
        throw $e;
    }
    fclose($socket);
}
