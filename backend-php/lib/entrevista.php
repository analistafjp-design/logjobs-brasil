<?php
declare(strict_types=1);

// Porta 1:1 de backend/entrevista.py.

const PERGUNTAS_COMPORTAMENTAIS = [
    'Fale um pouco sobre você e sua experiência profissional.',
    'Por que você quer trabalhar nesta empresa?',
    'Conte sobre uma situação difícil no trabalho e como você resolveu.',
    'Como você lida com pressão e prazos apertados?',
    'Onde você se vê profissionalmente daqui a alguns anos?',
    'Por que devemos te contratar?',
];

const PERGUNTAS_POR_CATEGORIA = [
    'Motorista' => [
        'Há quanto tempo você tem CNH e em quais categorias?',
        'Já teve algum acidente ou multa grave? Como lidou com a situação?',
        'Como você organiza uma rota com várias entregas e prazos diferentes?',
        'O que você faz se o veículo apresenta um problema mecânico no meio do trajeto?',
        'Como você garante a segurança da carga durante o transporte?',
    ],
    'Entregador' => [
        'Como você organiza suas entregas para otimizar o tempo?',
        'O que você faz se um cliente não está no endereço na hora da entrega?',
        'Como lida com trânsito ou condições climáticas ruins durante as entregas?',
        'Já teve algum problema com um cliente insatisfeito? Como resolveu?',
    ],
    'Estoquista' => [
        'Como você organiza o controle de estoque e evita divergências?',
        'Já usou algum sistema de gestão de estoque (WMS/ERP)? Qual?',
        'Como você prioriza tarefas quando há várias demandas ao mesmo tempo no estoque?',
        'Como lida com produtos danificados ou com validade próxima do vencimento?',
    ],
    'Conferente' => [
        'Como você garante precisão na conferência de mercadorias?',
        'O que você faz ao identificar uma divergência entre nota fiscal e mercadoria recebida?',
        'Como você lida com um volume grande de conferências em pouco tempo?',
    ],
    'Auxiliar Logístico' => [
        'Descreva sua experiência com separação e organização de mercadorias.',
        'Como você lida com tarefas repetitivas ao longo do dia?',
        'Já trabalhou em equipe para cumprir metas de produtividade? Como foi?',
    ],
    'Operador' => [
        'Você tem experiência operando empilhadeira ou outros equipamentos? Quais certificações possui?',
        'Como você garante a segurança ao operar equipamentos pesados?',
        'O que você faz ao perceber uma falha em um equipamento durante a operação?',
    ],
];

const DICA_GERAL = 'Use o método STAR (Situação, Tarefa, Ação, Resultado) para estruturar suas respostas: '
    . 'descreva o contexto, o que precisava ser feito, o que você fez e qual foi o resultado.';

function gerar_simulado(?string $categoria = null, int $quantidade = 5): array
{
    $especificas = $categoria ? (PERGUNTAS_POR_CATEGORIA[$categoria] ?? []) : [];
    $banco = array_merge($especificas, PERGUNTAS_COMPORTAMENTAIS);
    $quantidade = max(1, min($quantidade, count($banco)));
    $indices = array_rand($banco, $quantidade);
    $indices = is_array($indices) ? $indices : [$indices];
    $perguntas = array_map(fn ($i) => $banco[$i], $indices);
    shuffle($perguntas);
    return ['categoria' => $categoria, 'perguntas' => $perguntas, 'dica' => DICA_GERAL];
}

function categorias_disponiveis(): array
{
    $categorias = array_keys(PERGUNTAS_POR_CATEGORIA);
    sort($categorias);
    return $categorias;
}
