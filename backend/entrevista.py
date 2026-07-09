"""Simulador de entrevistas: banco de perguntas determinístico por categoria de
vaga, sem depender de nenhuma IA generativa externa. "Simular" aqui significa
apresentar perguntas realistas para o candidato praticar sozinho — não há
avaliação automática de respostas (isso exigiria uma IA de verdade, que o
projeto não tem configurada)."""
import random

PERGUNTAS_COMPORTAMENTAIS = [
    "Fale um pouco sobre você e sua experiência profissional.",
    "Por que você quer trabalhar nesta empresa?",
    "Conte sobre uma situação difícil no trabalho e como você resolveu.",
    "Como você lida com pressão e prazos apertados?",
    "Onde você se vê profissionalmente daqui a alguns anos?",
    "Por que devemos te contratar?",
]

PERGUNTAS_POR_CATEGORIA = {
    "Motorista": [
        "Há quanto tempo você tem CNH e em quais categorias?",
        "Já teve algum acidente ou multa grave? Como lidou com a situação?",
        "Como você organiza uma rota com várias entregas e prazos diferentes?",
        "O que você faz se o veículo apresenta um problema mecânico no meio do trajeto?",
        "Como você garante a segurança da carga durante o transporte?",
    ],
    "Entregador": [
        "Como você organiza suas entregas para otimizar o tempo?",
        "O que você faz se um cliente não está no endereço na hora da entrega?",
        "Como lida com trânsito ou condições climáticas ruins durante as entregas?",
        "Já teve algum problema com um cliente insatisfeito? Como resolveu?",
    ],
    "Estoquista": [
        "Como você organiza o controle de estoque e evita divergências?",
        "Já usou algum sistema de gestão de estoque (WMS/ERP)? Qual?",
        "Como você prioriza tarefas quando há várias demandas ao mesmo tempo no estoque?",
        "Como lida com produtos danificados ou com validade próxima do vencimento?",
    ],
    "Conferente": [
        "Como você garante precisão na conferência de mercadorias?",
        "O que você faz ao identificar uma divergência entre nota fiscal e mercadoria recebida?",
        "Como você lida com um volume grande de conferências em pouco tempo?",
    ],
    "Auxiliar Logístico": [
        "Descreva sua experiência com separação e organização de mercadorias.",
        "Como você lida com tarefas repetitivas ao longo do dia?",
        "Já trabalhou em equipe para cumprir metas de produtividade? Como foi?",
    ],
    "Operador": [
        "Você tem experiência operando empilhadeira ou outros equipamentos? Quais certificações possui?",
        "Como você garante a segurança ao operar equipamentos pesados?",
        "O que você faz ao perceber uma falha em um equipamento durante a operação?",
    ],
}

DICA_GERAL = (
    "Use o método STAR (Situação, Tarefa, Ação, Resultado) para estruturar suas respostas: "
    "descreva o contexto, o que precisava ser feito, o que você fez e qual foi o resultado."
)


def gerar_simulado(categoria: str = None, quantidade: int = 5) -> dict:
    especificas = PERGUNTAS_POR_CATEGORIA.get(categoria, []) if categoria else []
    banco = especificas + PERGUNTAS_COMPORTAMENTAIS
    quantidade = max(1, min(quantidade, len(banco)))
    perguntas = random.sample(banco, quantidade)
    return {
        "categoria": categoria,
        "perguntas": perguntas,
        "dica": DICA_GERAL,
    }


def categorias_disponiveis() -> list:
    return sorted(PERGUNTAS_POR_CATEGORIA.keys())
