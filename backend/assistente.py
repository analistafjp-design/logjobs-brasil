"""Assistente virtual: central de ajuda por correspondência de palavras-chave,
sem nenhuma IA generativa/LLM externa (o projeto não tem chave configurada
para isso). É deliberadamente apresentado como "central de ajuda inteligente"
e não como um chat conversacional livre, para não prometer mais do que
entrega — mesma filosofia de recomendacao.py."""
import unicodedata

RESPOSTA_PADRAO = (
    "Não tenho uma resposta pronta para isso. Tente perguntar de outro jeito, "
    "ou fale diretamente com nosso suporte em contato@logjobsbrasil.com.br."
)

# Cada intenção: palavras-chave (já sem acento/minúsculas) -> resposta.
INTENCOES = [
    (
        ("candidatar", "candidatura", "aplicar", "vaga"),
        "Para se candidatar, clique em \"Candidatar-se\" no card da vaga e preencha nome, e-mail e telefone. "
        "Se estiver logado, seus dados já vêm preenchidos automaticamente.",
    ),
    (
        ("favorito", "salvar vaga", "estrela"),
        "Clique no ícone de estrela (☆) no card da vaga para salvá-la. Você vê suas vagas salvas no seu perfil.",
    ),
    (
        ("2fa", "duas etapas", "autenticacao", "verificacao em duas"),
        "Ative a verificação em duas etapas na seção \"Segurança\" do seu perfil, escaneando o código com um "
        "app autenticador (Google Authenticator, Authy etc.).",
    ),
    (
        ("senha", "esqueci", "recuperar acesso", "trocar senha"),
        "No momento a recuperação de senha é feita entrando em contato com o suporte "
        "(contato@logjobsbrasil.com.br) — em breve teremos recuperação automática por e-mail.",
    ),
    (
        ("chat", "mensagem", "conversar com a empresa", "falar com o candidato"),
        "Você pode enviar uma mensagem para a empresa a partir do modal de candidatura de uma vaga, "
        "ou a empresa pode te chamar a partir da lista de candidaturas recebidas. As conversas ficam em \"💬 Mensagens\".",
    ),
    (
        ("curriculo", "curriculum", "cv"),
        "No seu perfil, preencha experiências, formação, cursos e habilidades. Depois, use \"Gerar currículo\" "
        "para baixar um currículo formatado a partir desses dados.",
    ),
    (
        ("recomendacao", "recomendado", "vaga compativel", "compatibilidade"),
        "Preencha seu mini-currículo e habilidades no perfil — a seção \"Vagas recomendadas para você\" usa "
        "esses dados para sugerir vagas compatíveis.",
    ),
    (
        ("entrevista", "simulado", "praticar entrevista"),
        "Use o \"Simulador de entrevistas\" no seu perfil para praticar perguntas comuns da sua área antes de uma entrevista real.",
    ),
    (
        ("anunciar vaga", "publicar vaga", "empresa", "contratar"),
        "Empresas podem publicar vagas pelo Painel da Empresa (menu \"Empresas\"), após criar uma conta do tipo empresa.",
    ),
    (
        ("alerta", "aviso de vaga", "notificacao de vaga"),
        "Salve uma busca como alerta no seu perfil — mostramos quantas vagas novas compatíveis surgiram desde a última vez que você olhou.",
    ),
    (
        ("google", "login com google", "entrar com google"),
        "Se disponível, o botão \"Continuar com Google\" aparece no formulário de login/cadastro. "
        "Se não aparecer, o login com Google ainda não foi configurado neste servidor.",
    ),
]


def _normalizar(texto: str) -> str:
    texto = texto.lower().strip()
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return texto


def responder(pergunta: str) -> dict:
    pergunta_normalizada = _normalizar(pergunta)

    melhor_resposta = None
    melhor_pontuacao = 0
    for palavras_chave, resposta in INTENCOES:
        pontuacao = sum(1 for palavra in palavras_chave if palavra in pergunta_normalizada)
        if pontuacao > melhor_pontuacao:
            melhor_pontuacao = pontuacao
            melhor_resposta = resposta

    return {
        "resposta": melhor_resposta or RESPOSTA_PADRAO,
        "encontrou": melhor_resposta is not None,
    }
