<?php
declare(strict_types=1);

function vaga_publica_para_json(array $v): array
{
    return [
        'id' => (int) $v['id'], 'cargo' => $v['cargo'], 'empresa' => $v['empresa'],
        'cidade' => $v['cidade'], 'estado' => $v['estado'],
        'salario' => $v['salario'] !== null ? (float) $v['salario'] : null,
        'modalidade' => $v['modalidade'], 'turno' => $v['turno'],
        'tipo_contratacao' => $v['tipo_contratacao'], 'veiculo' => $v['veiculo'],
        'categoria' => $v['categoria'], 'beneficios' => $v['beneficios'],
        'link' => $v['link'], 'fonte' => $v['fonte'],
        'criada_em' => $v['criada_em'] ? date('c', strtotime($v['criada_em'])) : null,
    ];
}

rota('GET', '/api/vagas', function () {
    $q = $_GET;
    $where = ['(pausada IS NULL OR pausada = 0)'];
    $params = [];

    $filtrosLike = ['cargo' => 'cargo', 'empresa' => 'empresa', 'cidade' => 'cidade', 'estado' => 'estado', 'categoria' => 'categoria', 'beneficio' => 'beneficios'];
    foreach ($filtrosLike as $param => $coluna) {
        if (!empty($q[$param])) {
            $where[] = "{$coluna} LIKE ?";
            $params[] = '%' . $q[$param] . '%';
        }
    }
    foreach (['modalidade' => 'modalidade', 'turno' => 'turno', 'tipo_contratacao' => 'tipo_contratacao'] as $param => $coluna) {
        if (!empty($q[$param])) {
            $where[] = "{$coluna} LIKE ?";
            $params[] = $q[$param];
        }
    }
    if (!empty($q['salario_min'])) {
        $where[] = 'salario >= ?';
        $params[] = (float) $q['salario_min'];
    }
    if (!empty($q['salario_max'])) {
        $where[] = 'salario <= ?';
        $params[] = (float) $q['salario_max'];
    }

    $whereSql = implode(' AND ', $where);
    $total = db()->prepare("SELECT COUNT(*) AS total FROM vagas WHERE {$whereSql}");
    $total->execute($params);
    $total = (int) $total->fetch()['total'];

    $ordenar = $q['ordenar'] ?? 'recentes';
    if ($ordenar === 'relevancia' && !empty($q['cargo'])) {
        $orderSql = "cargo LIKE ? DESC, id DESC";
        $paramsOrdenados = array_merge($params, [$q['cargo'] . '%']);
    } elseif ($ordenar === 'salario') {
        $orderSql = 'salario IS NULL, salario DESC';
        $paramsOrdenados = $params;
    } else {
        $orderSql = 'id DESC';
        $paramsOrdenados = $params;
    }

    $limit = min((int) ($q['limit'] ?? 20), 100);
    $offset = max((int) ($q['offset'] ?? 0), 0);

    $sql = "SELECT * FROM vagas WHERE {$whereSql} ORDER BY {$orderSql} LIMIT {$limit} OFFSET {$offset}";
    $stmt = db()->prepare($sql);
    $stmt->execute($paramsOrdenados);
    $vagas = $stmt->fetchAll();

    json_saida(['total' => $total, 'vagas' => array_map('vaga_publica_para_json', $vagas)]);
});

rota('GET', '/api/sugestoes', function () {
    $tipo = $_GET['tipo'] ?? '';
    $colunas = ['cargo' => 'cargo', 'cidade' => 'cidade', 'empresa' => 'empresa'];
    if (!isset($colunas[$tipo])) {
        json_erro(400, 'Tipo de sugestão inválido');
    }
    $coluna = $colunas[$tipo];
    $q = $_GET['q'] ?? '';
    if ($q !== '') {
        $stmt = db()->prepare("SELECT DISTINCT {$coluna} FROM vagas WHERE {$coluna} LIKE ? ORDER BY {$coluna} LIMIT 8");
        $stmt->execute(['%' . $q . '%']);
    } else {
        $stmt = db()->query("SELECT DISTINCT {$coluna} FROM vagas ORDER BY {$coluna} LIMIT 8");
    }
    json_saida(array_column($stmt->fetchAll(), $coluna));
});

rota('GET', '/api/vagas/{id}', function ($p) {
    $stmt = db()->prepare('SELECT * FROM vagas WHERE id = ?');
    $stmt->execute([$p['id']]);
    $v = $stmt->fetch();
    if (!$v) {
        json_erro(404, 'Vaga não encontrada');
    }
    json_saida([
        'id' => (int) $v['id'], 'cargo' => $v['cargo'], 'empresa' => $v['empresa'],
        'cidade' => $v['cidade'], 'estado' => $v['estado'],
        'salario' => $v['salario'] !== null ? (float) $v['salario'] : null,
        'modalidade' => $v['modalidade'], 'turno' => $v['turno'],
        'tipo_contratacao' => $v['tipo_contratacao'], 'veiculo' => $v['veiculo'],
        'categoria' => $v['categoria'], 'descricao' => $v['descricao'],
        'beneficios' => $v['beneficios'], 'requisitos' => $v['requisitos'],
        'link' => $v['link'], 'fonte' => $v['fonte'],
        'usuario_id' => $v['usuario_id'] !== null ? (int) $v['usuario_id'] : null,
    ]);
});

rota('GET', '/api/estatisticas', function () {
    $vagas = (int) db()->query('SELECT COUNT(*) AS t FROM vagas')->fetch()['t'];
    $empresas = (int) db()->query('SELECT COUNT(DISTINCT empresa) AS t FROM vagas')->fetch()['t'];
    $cidades = (int) db()->query('SELECT COUNT(DISTINCT cidade) AS t FROM vagas')->fetch()['t'];
    json_saida(['vagas' => $vagas, 'empresas' => $empresas, 'cidades' => $cidades]);
});

rota('GET', '/health', function () {
    json_saida(['status' => 'ok']);
});

rota('GET', '/api/salarios', function () {
    $stmt = db()->query(
        'SELECT categoria, MIN(salario) AS minimo, AVG(salario) AS media, MAX(salario) AS maximo, COUNT(id) AS total
         FROM vagas WHERE salario IS NOT NULL GROUP BY categoria ORDER BY AVG(salario) DESC'
    );
    $linhas = array_map(function ($l) {
        return [
            'categoria' => $l['categoria'], 'minimo' => (float) $l['minimo'],
            'media' => round((float) $l['media'], 2), 'maximo' => (float) $l['maximo'],
            'total' => (int) $l['total'],
        ];
    }, $stmt->fetchAll());
    json_saida($linhas);
});

rota('GET', '/api/ranking', function () {
    $porVagas = db()->query(
        'SELECT empresa, COUNT(id) AS total FROM vagas GROUP BY empresa ORDER BY COUNT(id) DESC LIMIT 15'
    )->fetchAll();
    $porSalario = db()->query(
        'SELECT empresa, AVG(salario) AS media, COUNT(id) AS total FROM vagas
         WHERE salario IS NOT NULL GROUP BY empresa HAVING COUNT(id) >= 2 ORDER BY AVG(salario) DESC LIMIT 15'
    )->fetchAll();
    json_saida([
        'por_vagas' => array_map(fn ($l) => ['empresa' => $l['empresa'], 'total' => (int) $l['total']], $porVagas),
        'por_salario' => array_map(fn ($l) => [
            'empresa' => $l['empresa'], 'salario_medio' => round((float) $l['media'], 2), 'total' => (int) $l['total'],
        ], $porSalario),
    ]);
});

function artigo_resumo_para_json(array $a): array
{
    return [
        'slug' => $a['slug'], 'titulo' => $a['titulo'], 'resumo' => $a['resumo'],
        'categoria' => $a['categoria'], 'autor' => $a['autor'],
        'publicado_em' => $a['publicado_em'] ? date('c', strtotime($a['publicado_em'])) : null,
    ];
}

rota('GET', '/api/blog', function () {
    if (!empty($_GET['categoria'])) {
        $stmt = db()->prepare('SELECT * FROM artigos WHERE categoria = ? ORDER BY publicado_em DESC');
        $stmt->execute([$_GET['categoria']]);
    } else {
        $stmt = db()->query('SELECT * FROM artigos ORDER BY publicado_em DESC');
    }
    json_saida(array_map('artigo_resumo_para_json', $stmt->fetchAll()));
});

rota('GET', '/api/blog/{slug}', function ($p) {
    $stmt = db()->prepare('SELECT * FROM artigos WHERE slug = ?');
    $stmt->execute([$p['slug']]);
    $a = $stmt->fetch();
    if (!$a) {
        json_erro(404, 'Artigo não encontrado');
    }
    json_saida(array_merge(artigo_resumo_para_json($a), ['conteudo' => $a['conteudo']]));
});

rota('GET', '/api/categorias', function () {
    $linhas = db()->query('SELECT categoria, COUNT(id) AS total FROM vagas GROUP BY categoria')->fetchAll();
    json_saida(array_map(fn ($l) => ['categoria' => $l['categoria'], 'total' => (int) $l['total']], $linhas));
});

rota('GET', '/api/dashboard', function () {
    $porCategoria = db()->query('SELECT categoria, COUNT(id) AS total FROM vagas GROUP BY categoria ORDER BY COUNT(id) DESC')->fetchAll();
    $porEstado = db()->query('SELECT estado, COUNT(id) AS total FROM vagas GROUP BY estado ORDER BY COUNT(id) DESC')->fetchAll();
    $topEmpresas = db()->query('SELECT empresa, COUNT(id) AS total FROM vagas GROUP BY empresa ORDER BY COUNT(id) DESC LIMIT 10')->fetchAll();
    $salarioPorCategoria = db()->query(
        'SELECT categoria, AVG(salario) AS media FROM vagas WHERE salario IS NOT NULL GROUP BY categoria ORDER BY AVG(salario) DESC'
    )->fetchAll();
    $evolucao = db()->query('SELECT * FROM atualizacoes ORDER BY id DESC LIMIT 30')->fetchAll();

    json_saida([
        'por_categoria' => array_map(fn ($l) => ['categoria' => $l['categoria'], 'total' => (int) $l['total']], $porCategoria),
        'por_estado' => array_map(fn ($l) => ['estado' => $l['estado'] ?: 'Não informado', 'total' => (int) $l['total']], $porEstado),
        'top_empresas' => array_map(fn ($l) => ['empresa' => $l['empresa'], 'total' => (int) $l['total']], $topEmpresas),
        'salario_por_categoria' => array_map(fn ($l) => ['categoria' => $l['categoria'], 'salario_medio' => round((float) $l['media'], 2)], $salarioPorCategoria),
        'evolucao' => array_reverse(array_map(fn ($a) => [
            'executada_em' => date('c', strtotime($a['executada_em'])),
            'vagas_novas' => (int) $a['vagas_novas'], 'vagas_totais' => (int) $a['vagas_totais'],
        ], $evolucao)),
    ]);
});

rota('GET', '/api/status', function () {
    $ultima = db()->query('SELECT * FROM atualizacoes ORDER BY id DESC LIMIT 1')->fetch();
    $porFonte = db()->query('SELECT fonte, COUNT(id) AS total FROM vagas GROUP BY fonte')->fetchAll();
    $totalPorFonte = [];
    foreach ($porFonte as $l) {
        $totalPorFonte[$l['fonte']] = (int) $l['total'];
    }
    json_saida([
        'jooble_configurado' => jooble_api_key() !== null,
        'intervalo_atualizacao_minutos' => 20,
        'ultima_atualizacao' => $ultima ? date('c', strtotime($ultima['executada_em'])) : null,
        'vagas_novas_na_ultima_atualizacao' => $ultima ? (int) $ultima['vagas_novas'] : null,
        'vagas_por_fonte' => $totalPorFonte,
    ]);
});

rota('POST', '/api/atualizar-agora', function () {
    verificar_admin();
    require_once __DIR__ . '/../lib/scheduler.php';
    atualizar_vagas_periodicamente();
    registrar_auditoria('atualizar_vagas_agora');
    json_saida(['mensagem' => 'Atualização executada.']);
});

rota('GET', '/sitemap.xml', function () {
    $vagas = db()->query('SELECT * FROM vagas ORDER BY id DESC LIMIT 1000')->fetchAll();
    $artigos = db()->query('SELECT * FROM artigos')->fetchAll();
    header('Content-Type: application/xml; charset=utf-8');
    echo pagina_sitemap_xml($vagas, $artigos);
    exit;
});

rota('GET', '/robots.txt', function () {
    header('Content-Type: text/plain; charset=utf-8');
    echo robots_txt();
    exit;
});

rota('GET', '/favicon.ico', function () {
    header('Content-Type: image/svg+xml');
    echo "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>🚚</text></svg>";
    exit;
});

rota('GET', '/vagas/{id}', function ($p) {
    $stmt = db()->prepare('SELECT * FROM vagas WHERE id = ?');
    $stmt->execute([$p['id']]);
    $v = $stmt->fetch();
    if (!$v) {
        http_response_code(404);
        header('Content-Type: text/html; charset=utf-8');
        echo pagina_404_html();
        exit;
    }
    header('Content-Type: text/html; charset=utf-8');
    echo pagina_vaga_html($v);
    exit;
});
