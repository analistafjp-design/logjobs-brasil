"""Envio de e-mail via SMTP, usando só a biblioteca padrão do Python
(smtplib/email) — mesma filosofia de oauth_google.py/security.py/totp.py:
sem depender de serviços de terceiros (SendGrid, Mailgun, SES...) que
exigiriam mais uma chave de API e mais uma conta para configurar.

Funciona com qualquer provedor SMTP (Gmail, Outlook, um servidor próprio,
ou o relay SMTP de um SendGrid/Mailgun se o usuário preferir usar um).
Sem as variáveis de ambiente configuradas, `configurado()` retorna False e
quem chama deve tratar a funcionalidade como indisponível — mesmo padrão
usado para o login com Google."""
import os
import smtplib
from email.mime.text import MIMEText

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", SMTP_USER)


def configurado() -> bool:
    return bool(SMTP_HOST and SMTP_USER and SMTP_PASSWORD)


class ErroEnvioEmail(Exception):
    pass


def enviar_email(destinatario: str, assunto: str, corpo_texto: str) -> None:
    if not configurado():
        raise ErroEnvioEmail("SMTP não configurado neste servidor")

    mensagem = MIMEText(corpo_texto, "plain", "utf-8")
    mensagem["Subject"] = assunto
    mensagem["From"] = SMTP_FROM_EMAIL
    mensagem["To"] = destinatario

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as servidor:
            servidor.starttls()
            servidor.login(SMTP_USER, SMTP_PASSWORD)
            servidor.sendmail(SMTP_FROM_EMAIL, [destinatario], mensagem.as_string())
    except (smtplib.SMTPException, OSError) as erro:
        raise ErroEnvioEmail(str(erro)) from erro
