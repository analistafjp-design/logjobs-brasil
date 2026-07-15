<?php
declare(strict_types=1);

// Porta 1:1 de backend/assistente.py.

const RESPOSTA_PADRAO_ASSISTENTE = 'Não tenho uma resposta pronta para isso. Tente perguntar de outro jeito, '
    . 'ou fale diretamente com nosso suporte em contato@logjobsbrasil.com.br.';

function intencoes_assistente(): array
{
    return [
        [['obrigado', 'obrigada', 'valeu', 'brigado', 'vlw'], 'De nada! Se tiver mais alguma dúvida, é só perguntar. 😊'],
        [['oi', 'ola', 'bom dia', 'boa tarde', 'boa noite', 'eae'], 'Olá! Como posso ajudar? Pergunte sobre candidaturas, perfil, chat, 2FA e mais.'],
        [['candidatar', 'candidatura', 'aplicar', 'vaga'], 'Para se candidatar, clique em "Candidatar-se" no card da vaga e preencha nome, e-mail e telefone. Se estiver logado, seus dados já vêm preenchidos automaticamente.'],
        [['favorito', 'salvar vaga', 'estrela'], 'Clique no ícone de estrela (☆) no card da vaga para salvá-la. Você vê suas vagas salvas no seu perfil.'],
        [['2fa', 'duas etapas', 'autenticacao', 'verificacao em duas'], 'Ative a verificação em duas etapas na seção "Segurança" do seu perfil, escaneando o código com um app autenticador (Google Authenticator, Authy etc.).'],
        [['senha', 'esqueci', 'recuperar acesso', 'trocar senha'], 'Clique em "Esqueci minha senha" na tela de login — enviamos um link de redefinição para o seu e-mail, válido por 1 hora. Se o link não aparecer no login, a recuperação por e-mail ainda não foi configurada neste servidor; nesse caso, fale com o suporte em contato@logjobsbrasil.com.br.'],
        [['chat', 'mensagem', 'conversar com a empresa', 'falar com o candidato'], 'Você pode enviar uma mensagem para a empresa a partir do modal de candidatura de uma vaga, ou a empresa pode te chamar a partir da lista de candidaturas recebidas. As conversas ficam em "💬 Mensagens".'],
        [['curriculo', 'curriculum', 'cv'], 'No seu perfil, preencha experiências, formação, cursos e habilidades. Depois, use "Gerar currículo" para baixar um currículo formatado a partir desses dados.'],
        [['recomendacao', 'recomendado', 'vaga compativel', 'compatibilidade'], 'Preencha seu mini-currículo e habilidades no perfil — a seção "Vagas recomendadas para você" usa esses dados para sugerir vagas compatíveis.'],
        [['entrevista', 'simulado', 'praticar entrevista'], 'Use o "Simulador de entrevistas" no seu perfil para praticar perguntas comuns da sua área antes de uma entrevista real.'],
        [['anunciar vaga', 'publicar vaga', 'empresa', 'contratar'], 'Empresas podem publicar vagas pelo Painel da Empresa (menu "Empresas"), após criar uma conta do tipo empresa.'],
        [['alerta', 'aviso de vaga', 'notificacao de vaga'], 'Salve uma busca como alerta no seu perfil — mostramos quantas vagas novas compatíveis surgiram desde a última vez que você olhou.'],
        [['google', 'login com google', 'entrar com google'], 'Se disponível, o botão "Continuar com Google" aparece no formulário de login/cadastro. Se não aparecer, o login com Google ainda não foi configurado neste servidor.'],
        [['entregador', 'motorista', 'estoquista', 'conferente', 'auxiliar logistico', 'operador', 'categoria'], 'Você pode filtrar vagas por essa categoria direto na página inicial — clique no botão da categoria logo abaixo da busca, ou digite o cargo no campo de busca.'],
        [['cadastro', 'cadastrar', 'criar conta', 'registrar', 'registro'], 'Clique em "Entrar" no menu e depois na aba "Cadastrar". Escolha se você é candidato ou empresa, preencha nome, e-mail e senha — leva menos de 2 minutos.'],
        [['mapa', 'mapa de vagas', 'vagas no mapa'], 'O "Mapa" (menu principal) mostra o número de vagas por estado em bolhas — clique em um estado para ver as vagas de lá na busca.'],
        [['ranking', 'melhores empresas', 'empresas que mais contratam'], 'O "Ranking" (menu principal) lista as empresas que mais publicam vagas e as com maior salário médio informado.'],
        [['salario', 'comparar salario', 'faixa salarial', 'quanto ganha'], 'Em "Salários" (menu principal) você compara a faixa salarial (mínimo, média e máximo) de até duas categorias lado a lado.'],
        [['blog', 'artigo', 'dicas de carreira'], 'O "Blog" (menu principal) tem artigos sobre documentos, currículo e entrevistas para quem trabalha com logística.'],
        [['meus dados', 'excluir conta', 'excluir minha conta', 'apagar conta', 'apagar minha conta', 'apagar meus dados', 'deletar conta', 'deletar minha conta', 'cancelar conta', 'lgpd', 'privacidade'], 'Na seção "🛡️ Privacidade e meus dados" do seu perfil, você baixa uma cópia de tudo o que guardamos sobre você ou exclui sua conta e os dados associados definitivamente.'],
        [['logo', 'site da empresa', 'instagram da empresa', 'redes sociais'], 'Empresas cadastram logo, site e Instagram na tela de perfil ("Dados da conta", logado como empresa) — a logo aparece no cabeçalho do painel da empresa.'],
        [['compartilhar', 'compartilhar vaga'], 'Clique no ícone 🔗 no card da vaga para compartilhar o link — abre o menu de compartilhamento do celular ou copia o link direto para a área de transferência.'],
        [['conquista', 'selo', 'nivel', 'gamificacao'], 'Em "🏅 Suas conquistas", no seu perfil de candidato, você vê selos por completar o perfil, salvar vagas e enviar candidaturas.'],
        [['exportar candidaturas', 'baixar candidaturas', 'csv'], 'No painel da empresa, o botão de exportar candidaturas gera um CSV com todos os candidatos de todas as suas vagas.'],
        [['pausar vaga', 'renovar vaga', 'reativar vaga'], 'No painel da empresa, cada vaga tem botões para pausar (some da busca pública sem excluir), reativar e renovar (volta ao topo das mais recentes).'],
        [['plano', 'preco', 'quanto custa', 'gratuito', 'pagar'], 'O LogJobs Brasil é gratuito para candidatos. Para planos de empresa, deixe seu contato pelo link "Planos" no rodapé — ainda estamos definindo os valores.'],
    ];
}

function normalizar_texto(string $texto): string
{
    $texto = mb_strtolower(trim($texto));
    $transliterado = iconv('UTF-8', 'ASCII//TRANSLIT//IGNORE', $texto);
    return $transliterado !== false ? $transliterado : $texto;
}

function contem_palavra(string $palavra, string $texto): bool
{
    return preg_match('/\b' . preg_quote($palavra, '/') . 's?\b/', $texto) === 1;
}

function assistente_responder(string $pergunta): array
{
    $perguntaNormalizada = normalizar_texto($pergunta);

    $melhorResposta = null;
    $melhorPontuacao = 0;
    foreach (intencoes_assistente() as [$palavrasChave, $resposta]) {
        $pontuacao = 0;
        foreach ($palavrasChave as $palavra) {
            if (contem_palavra($palavra, $perguntaNormalizada)) {
                $pontuacao += mb_strlen($palavra);
            }
        }
        if ($pontuacao > $melhorPontuacao) {
            $melhorPontuacao = $pontuacao;
            $melhorResposta = $resposta;
        }
    }

    return ['resposta' => $melhorResposta ?? RESPOSTA_PADRAO_ASSISTENTE, 'encontrou' => $melhorResposta !== null];
}
