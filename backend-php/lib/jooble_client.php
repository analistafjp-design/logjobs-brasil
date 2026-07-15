<?php
declare(strict_types=1);

// Porta 1:1 de backend/jooble_client.py (usa cURL em vez de requests).

function jooble_api_key(): ?string
{
    $chave = config('JOOBLE_API_KEY');
    return $chave ?: null;
}

const PADROES_CATEGORIA = [
    ['/empilhadeira/i', 'Operador'],
    ['/motoboy/i', 'Motoboy'],
    ['/entregador|entrega\\b|delivery/i', 'Entregador'],
    ['/caminhoneiro|carreteiro|caminh[aã]o/i', 'Caminhoneiro'],
    ['/motorista|condutor/i', 'Motorista'],
    ['/estoquista|estoque|almoxarife/i', 'Estoquista'],
    ['/conferente|confer[eê]ncia/i', 'Conferente'],
    ['/auxiliar|ajudante|separador|expedi[cç][aã]o|embalador/i', 'Auxiliar Logístico'],
    ['/supervisor/i', 'Supervisor'],
    ['/coordenador/i', 'Coordenador'],
    ['/analista/i', 'Analista'],
    ['/gestor|gerente|diretor/i', 'Gestor'],
    ['/operador/i', 'Operador'],
];

function jooble_classificar_categoria(string $cargo): string
{
    foreach (PADROES_CATEGORIA as [$padrao, $categoria]) {
        if (preg_match($padrao, $cargo)) {
            return $categoria;
        }
    }
    return 'Logística';
}

const REGIOES = [
    ['São Paulo', 'SP'], ['Rio de Janeiro', 'RJ'], ['Belo Horizonte', 'MG'], ['Curitiba', 'PR'],
    ['Porto Alegre', 'RS'], ['Salvador', 'BA'], ['Recife', 'PE'], ['Fortaleza', 'CE'],
    ['Brasília', 'DF'], ['Manaus', 'AM'], ['Goiânia', 'GO'], ['Florianópolis', 'SC'],
    ['Vitória', 'ES'], ['Belém', 'PA'], ['Campo Grande', 'MS'], ['Cuiabá', 'MT'],
];

const TERMOS_CATEGORIA = [
    ['entregador', 'Entregador'],
    ['motorista entregas', 'Motorista'],
    ['motorista caminhoneiro carreteiro', 'Caminhoneiro'],
    ['estoquista almoxarife', 'Estoquista'],
    ['conferente de cargas', 'Conferente'],
    ['auxiliar logistica expedicao', 'Auxiliar Logístico'],
    ['operador de empilhadeira', 'Operador'],
    ['motoboy', 'Motoboy'],
];

function jooble_limpar_html(?string $texto): ?string
{
    if (!$texto) {
        return $texto;
    }
    $semTags = preg_replace('/<[^>]+>/', '', $texto);
    return trim(preg_replace('/\s+/', ' ', $semTags));
}

function jooble_buscar_uma_regiao(string $keywords, string $cidadeBusca, string $estado): array
{
    $chave = jooble_api_key();
    $location = "{$cidadeBusca}, Brasil";
    $ch = curl_init("https://jooble.org/api/{$chave}");
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 10);
    curl_setopt($ch, CURLOPT_POST, true);
    curl_setopt($ch, CURLOPT_HTTPHEADER, ['Content-Type: application/json']);
    curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode(['keywords' => $keywords, 'location' => $location]));
    $resposta = curl_exec($ch);
    $codigo = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    if ($resposta === false || $codigo >= 400) {
        return [];
    }
    $dados = json_decode($resposta, true);
    if (!is_array($dados)) {
        return [];
    }

    $vagas = [];
    foreach ($dados['jobs'] ?? [] as $item) {
        $localBruto = $item['location'] ?? '';
        if (preg_match('/\b(Montana|Pennsylvania|Mississippi|South Carolina|Alabama)\b/i', $localBruto)) {
            continue;
        }
        $cidade = trim(explode(',', $localBruto)[0] ?? '') ?: $cidadeBusca;
        $cargo = mb_substr($item['title'] ?? '', 0, 255);
        $vagas[] = [
            'cargo' => $cargo,
            'empresa' => $item['company'] ?? 'Não informado',
            'cidade' => $cidade,
            'estado' => $estado,
            'salario' => null,
            'modalidade' => null,
            'veiculo' => null,
            'categoria' => $cargo,
            'descricao' => jooble_limpar_html($item['snippet'] ?? ''),
            'beneficios' => null,
            'requisitos' => null,
            'link' => $item['link'] ?? null,
            'fonte' => 'jooble',
        ];
    }
    return $vagas;
}

function jooble_categoria_final(string $cargo, string $categoriaDaBusca): string
{
    $detectada = jooble_classificar_categoria($cargo);
    return $detectada !== 'Logística' ? $detectada : $categoriaDaBusca;
}

function jooble_buscar_vagas_por_termo(string $termo, string $categoria): array
{
    if (!jooble_api_key()) {
        return [];
    }
    $vagas = [];
    foreach (REGIOES as [$cidade, $estado]) {
        $encontradas = jooble_buscar_uma_regiao($termo, $cidade, $estado);
        foreach ($encontradas as &$vaga) {
            $vaga['categoria'] = jooble_categoria_final($vaga['cargo'], $categoria);
        }
        unset($vaga);
        $vagas = array_merge($vagas, $encontradas);
    }
    return $vagas;
}

function jooble_buscar_vagas_todas_categorias(): array
{
    if (!jooble_api_key()) {
        return [];
    }
    $vagas = [];
    foreach (TERMOS_CATEGORIA as [$termo, $categoria]) {
        $vagas = array_merge($vagas, jooble_buscar_vagas_por_termo($termo, $categoria));
    }
    return $vagas;
}

function jooble_buscar_vagas_proxima_categoria(int $indice): array
{
    if (!jooble_api_key()) {
        return [];
    }
    [$termo, $categoria] = TERMOS_CATEGORIA[$indice % count(TERMOS_CATEGORIA)];
    return jooble_buscar_vagas_por_termo($termo, $categoria);
}
