<?php
declare(strict_types=1);

// Router minimalista: casa método + caminho contra padrões estilo "/api/vagas/{id}"
// e chama o handler com os parâmetros extraídos. Front controller único
// (api/index.php), com todas as requisições /api/* reescritas para cá via .htaccess —
// mesma ideia do roteamento automático por decorator do FastAPI original, só que
// explícito (hospedagem compartilhada não tem esse luxo).

$GLOBALS['__rotas'] = [];

function rota(string $metodo, string $padrao, callable $handler): void
{
    // Percorre o padrão em pedaços (placeholder {nome} OU texto literal) e escapa só
    // os pedaços literais como regex — senão "." em "/sitemap.xml" viraria "qualquer
    // caractere" na comparação.
    $regexBody = preg_replace_callback('#\{[a-zA-Z_]+\}|[^{]+#', function ($m) {
        $pedaco = $m[0];
        return $pedaco[0] === '{' ? '([^/]+)' : preg_quote($pedaco, '#');
    }, $padrao);
    $regex = '#^' . $regexBody . '$#';
    preg_match_all('#\{([a-zA-Z_]+)\}#', $padrao, $nomes);
    $GLOBALS['__rotas'][] = [$metodo, $regex, $nomes[1], $handler];
}

function despachar(string $metodo, string $caminho): void
{
    foreach ($GLOBALS['__rotas'] as [$metodoRota, $regex, $nomes, $handler]) {
        if ($metodoRota !== $metodo) {
            continue;
        }
        if (preg_match($regex, $caminho, $matches)) {
            array_shift($matches);
            $params = array_combine($nomes, $matches);
            $handler($params);
            return;
        }
    }
    json_erro(404, 'Rota não encontrada');
}
