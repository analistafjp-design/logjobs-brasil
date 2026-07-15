<?php
declare(strict_types=1);

// Porta 1:1 de backend/recomendacao.py.

const STOPWORDS_PT = [
    'a', 'o', 'as', 'os', 'de', 'da', 'do', 'das', 'dos', 'e', 'em', 'um', 'uma',
    'uns', 'umas', 'para', 'com', 'sem', 'por', 'que', 'sou', 'eu', 'me', 'meu',
    'minha', 'meus', 'minhas', 'tenho', 'trabalho', 'trabalhei', 'trabalhar',
    'anos', 'ano', 'no', 'na', 'nos', 'nas', 'ao', 'aos', 'às', 'sobre', 'mais',
    'muito', 'muita', 'já', 'também', 'como', 'ser', 'está', 'foi', 'sua', 'seu',
];

const PESOS_CAMPO = ['cargo' => 3, 'categoria' => 3, 'requisitos' => 2, 'beneficios' => 1, 'descricao' => 1];

function tokenizar(string $texto): array
{
    if (!$texto) {
        return [];
    }
    preg_match_all('/[a-zà-ú]+/u', mb_strtolower($texto), $matches);
    $palavras = array_filter($matches[0], fn ($p) => mb_strlen($p) >= 3 && !in_array($p, STOPWORDS_PT, true));
    return array_fill_keys($palavras, true);
}

function pontuar_vaga(array $tokensUsuario, array $vaga): array
{
    if (!$tokensUsuario) {
        return [0, 0];
    }
    $campos = [
        'cargo' => $vaga['cargo'] ?? '',
        'categoria' => $vaga['categoria'] ?? '',
        'requisitos' => $vaga['requisitos'] ?? '',
        'beneficios' => $vaga['beneficios'] ?? '',
        'descricao' => $vaga['descricao'] ?? '',
    ];
    $tokensEncontrados = [];
    $pontuacao = 0;
    foreach ($campos as $campo => $texto) {
        $tokensCampo = tokenizar((string) $texto);
        $interseccao = array_intersect_key($tokensUsuario, $tokensCampo);
        if ($interseccao) {
            $pontuacao += count($interseccao) * PESOS_CAMPO[$campo];
            $tokensEncontrados += $interseccao;
        }
    }
    $percentual = (int) round(min(1.0, count($tokensEncontrados) / count($tokensUsuario)) * 100);
    return [$pontuacao, $percentual];
}

/** @param array<array> $vagas */
function recomendar_vagas(string $resumoUsuario, array $vagas, int $limite = 6): array
{
    $tokensUsuario = tokenizar($resumoUsuario);
    if (!$tokensUsuario) {
        return [];
    }
    $pontuadas = [];
    foreach ($vagas as $vaga) {
        [$pontuacao, $percentual] = pontuar_vaga($tokensUsuario, $vaga);
        if ($pontuacao > 0) {
            $pontuadas[] = ['pontuacao' => $pontuacao, 'percentual' => $percentual, 'vaga' => $vaga];
        }
    }
    usort($pontuadas, fn ($a, $b) => $b['pontuacao'] <=> $a['pontuacao']);
    return array_slice($pontuadas, 0, $limite);
}
