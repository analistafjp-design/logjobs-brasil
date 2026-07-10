"""Assistente virtual: central de ajuda por correspondência de palavras-chave,
sem nenhuma IA generativa/LLM externa (o projeto não tem chave configurada
para isso). É deliberadamente apresentado como "central de ajuda inteligente"
e não como um chat conversacional livre, para não prometer mais do que
entrega — mesma filosofia de recomendacao.py."""
import re
import unicodedata

RESPOSTA_PADRAO = (
    "Não tenho uma resposta pronta para isso. Tente perguntar de outro jeito, "
    "ou fale diretamente com nosso suporte em contato@logjobsbrasil.com.br."
)

# Cada intenção: palavras-chave (já sem acento/minúsculas) -> resposta. As
# palavras/frases são casadas por palavra inteira (não substring) — sem isso,
# "chat" combinaria com "chateado", "cv" com qualquer palavra que contivesse
# "cv", etc.
INTENCOES = [
    (
        ("obrigado", "obrigada", "valeu", "brigado", "vlw"),
        "De nada! Se tiver mais alguma dúvida, é só perguntar. 😊",
    ),
    (
        ("oi", "ola", "bom dia", "boa tarde", "boa noite", "eae"),
        "Olá! Como posso ajudar? Pergunte sobre candidaturas, perfil, chat, 2FA e mais.",
    ),
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
        "Clique em \"Esqueci minha senha\" na tela de login — enviamos um link de redefinição para o seu "
        "e-mail, válido por 1 hora. Se o link não aparecer no login, a recuperação por e-mail ainda não foi "
        "configurada neste servidor; nesse caso, fale com o suporte em contato@logjobsbrasil.com.br.",
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
    (
        ("entregador", "motorista", "estoquista", "conferente", "auxiliar logistico", "operador", "categoria"),
        "Você pode filtrar vagas por essa categoria direto na página inicial — clique no botão da categoria "
        "logo abaixo da busca, ou digite o cargo no campo de busca.",
    ),
    (
        ("cadastro", "cadastrar", "criar conta", "registrar", "registro"),
        "Clique em \"Entrar\" no menu e depois na aba \"Cadastrar\". Escolha se você é candidato ou empresa, "
        "preencha nome, e-mail e senha — leva menos de 2 minutos.",
    ),
    (
        ("mapa", "mapa de vagas", "vagas no mapa"),
        "O \"Mapa\" (menu principal) mostra o número de vagas por estado em bolhas — clique em um estado para "
        "ver as vagas de lá na busca.",
    ),
    (
        ("ranking", "melhores empresas", "empresas que mais contratam"),
        "O \"Ranking\" (menu principal) lista as empresas que mais publicam vagas e as com maior salário médio "
        "informado.",
    ),
    (
        ("salario", "comparar salario", "faixa salarial", "quanto ganha"),
        "Em \"Salários\" (menu principal) você compara a faixa salarial (mínimo, média e máximo) de até duas "
        "categorias lado a lado.",
    ),
    (
        ("blog", "artigo", "dicas de carreira"),
        "O \"Blog\" (menu principal) tem artigos sobre documentos, currículo e entrevistas para quem trabalha "
        "com logística.",
    ),
    (
        (
            "meus dados", "excluir conta", "excluir minha conta", "apagar conta", "apagar minha conta",
            "apagar meus dados", "deletar conta", "deletar minha conta", "cancelar conta", "lgpd", "privacidade",
        ),
        "Na seção \"🛡️ Privacidade e meus dados\" do seu perfil, você baixa uma cópia de tudo o que guardamos "
        "sobre você ou exclui sua conta e os dados associados definitivamente.",
    ),
    (
        ("logo", "site da empresa", "instagram da empresa", "redes sociais"),
        "Empresas cadastram logo, site e Instagram na tela de perfil (\"Dados da conta\", logado como empresa) — "
        "a logo aparece no cabeçalho do painel da empresa.",
    ),
    (
        ("compartilhar", "compartilhar vaga"),
        "Clique no ícone 🔗 no card da vaga para compartilhar o link — abre o menu de compartilhamento do "
        "celular ou copia o link direto para a área de transferência.",
    ),
    (
        ("conquista", "selo", "nivel", "gamificacao"),
        "Em \"🏅 Suas conquistas\", no seu perfil de candidato, você vê selos por completar o perfil, salvar "
        "vagas e enviar candidaturas.",
    ),
    (
        ("exportar candidaturas", "baixar candidaturas", "csv"),
        "No painel da empresa, o botão de exportar candidaturas gera um CSV com todos os candidatos de todas "
        "as suas vagas.",
    ),
    (
        ("pausar vaga", "renovar vaga", "reativar vaga"),
        "No painel da empresa, cada vaga tem botões para pausar (some da busca pública sem excluir), reativar "
        "e renovar (volta ao topo das mais recentes).",
    ),
    (
        ("plano", "preco", "quanto custa", "gratuito", "pagar"),
        "O LogJobs Brasil é gratuito para candidatos. Para planos de empresa, deixe seu contato pelo link "
        "\"Planos\" no rodapé — ainda estamos definindo os valores.",
    ),
]


def _normalizar(texto: str) -> str:
    texto = texto.lower().strip()
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode("ascii")
    return texto


def _contem_palavra(palavra: str, texto: str) -> bool:
    # "s?" no final: casa também o plural regular (vaga/vagas, candidatura/candidaturas),
    # sem o que uma pergunta como "quais vagas vocês têm?" não batia com a intenção de "vaga".
    return re.search(rf"\b{re.escape(palavra)}s?\b", texto) is not None


def responder(pergunta: str) -> dict:
    pergunta_normalizada = _normalizar(pergunta)

    melhor_resposta = None
    melhor_pontuacao = 0
    for palavras_chave, resposta in INTENCOES:
        # Pontua pelo tamanho das palavras-chave casadas, não pela quantidade — senão uma
        # palavra genérica como "vaga" (que aparece em quase toda pergunta sobre o site) empata
        # ou vence uma intenção mais específica só por estar numa lista com mais sinônimos.
        pontuacao = sum(len(palavra) for palavra in palavras_chave if _contem_palavra(palavra, pergunta_normalizada))
        if pontuacao > melhor_pontuacao:
            melhor_pontuacao = pontuacao
            melhor_resposta = resposta

    return {
        "resposta": melhor_resposta or RESPOSTA_PADRAO,
        "encontrou": melhor_resposta is not None,
    }
