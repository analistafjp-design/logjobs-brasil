<?php
declare(strict_types=1);

rota('GET', '/api/favoritos', function () {
    $usuario = usuario_atual();
    $stmt = db()->prepare('SELECT vaga_id FROM favoritos WHERE usuario_id = ?');
    $stmt->execute([$usuario['id']]);
    $ids = array_column($stmt->fetchAll(), 'vaga_id');
    if (!$ids) {
        json_saida(['vagas' => []]);
    }
    $in = implode(',', array_fill(0, count($ids), '?'));
    $stmt = db()->prepare("SELECT * FROM vagas WHERE id IN ({$in})");
    $stmt->execute($ids);
    $vagas = array_map(fn ($v) => [
        'id' => (int) $v['id'], 'cargo' => $v['cargo'], 'empresa' => $v['empresa'], 'cidade' => $v['cidade'],
        'estado' => $v['estado'], 'salario' => $v['salario'] !== null ? (float) $v['salario'] : null,
        'modalidade' => $v['modalidade'], 'categoria' => $v['categoria'], 'link' => $v['link'],
    ], $stmt->fetchAll());
    json_saida(['vagas' => $vagas]);
});

rota('POST', '/api/favoritos/{id}', function ($p) {
    $usuario = usuario_atual();
    if (!buscar_vaga((int) $p['id'])) {
        json_erro(404, 'Vaga não encontrada');
    }
    $stmt = db()->prepare('SELECT id FROM favoritos WHERE usuario_id = ? AND vaga_id = ?');
    $stmt->execute([$usuario['id'], $p['id']]);
    if ($stmt->fetch()) {
        json_saida(['mensagem' => 'Vaga já estava salva']);
    }
    db()->prepare('INSERT INTO favoritos (usuario_id, vaga_id) VALUES (?, ?)')->execute([$usuario['id'], $p['id']]);
    json_saida(['mensagem' => 'Vaga salva'], 201);
});

rota('DELETE', '/api/favoritos/{id}', function ($p) {
    $usuario = usuario_atual();
    db()->prepare('DELETE FROM favoritos WHERE usuario_id = ? AND vaga_id = ?')->execute([$usuario['id'], $p['id']]);
    json_saida(['mensagem' => 'Vaga removida dos salvos']);
});

rota('GET', '/api/recomendacoes', function () {
    $usuario = usuario_atual();
    if (empty(trim($usuario['resumo'] ?? ''))) {
        json_saida(['vagas' => [], 'motivo' => 'perfil_incompleto']);
    }
    $textoExperiencias = implode(' ', array_map(fn ($e) => ($e['cargo'] ?? '') . ' ' . ($e['descricao'] ?? ''), lista_json($usuario['experiencias_json'])));
    $textoFormacoes = implode(' ', array_map(fn ($f) => $f['curso'] ?? '', lista_json($usuario['formacoes_json'])));
    $textoPerfil = implode(' ', array_filter([$usuario['resumo'], $usuario['habilidades'], $textoExperiencias, $textoFormacoes]));

    $vagas = db()->query('SELECT * FROM vagas ORDER BY id DESC LIMIT 500')->fetchAll();
    $recomendadas = recomendar_vagas($textoPerfil, $vagas, 6);

    json_saida(['vagas' => array_map(function ($item) {
        $v = $item['vaga'];
        return [
            'id' => (int) $v['id'], 'cargo' => $v['cargo'], 'empresa' => $v['empresa'], 'cidade' => $v['cidade'],
            'estado' => $v['estado'], 'salario' => $v['salario'] !== null ? (float) $v['salario'] : null,
            'categoria' => $v['categoria'], 'link' => $v['link'], 'compatibilidade' => $item['percentual'],
        ];
    }, $recomendadas)]);
});

rota('GET', '/api/ia/analise-perfil', function () {
    $usuario = usuario_atual();
    if ($usuario['tipo'] !== 'candidato') {
        json_erro(403, 'Análise de perfil disponível apenas para candidatos');
    }
    json_saida(analisar_perfil($usuario));
});

rota('GET', '/api/ia/gerar-curriculo', function () {
    $usuario = usuario_atual();
    if ($usuario['tipo'] !== 'candidato') {
        json_erro(403, 'Geração de currículo disponível apenas para candidatos');
    }
    header('Content-Type: text/plain; charset=utf-8');
    header('Content-Disposition: attachment; filename=curriculo.txt');
    echo gerar_curriculo_texto($usuario);
    exit;
});

rota('GET', '/api/ia/simulador-entrevista', function () {
    usuario_atual();
    $categoria = $_GET['categoria'] ?? null;
    $quantidade = max(1, min((int) ($_GET['quantidade'] ?? 5), 10));
    json_saida(gerar_simulado($categoria, $quantidade));
});

rota('GET', '/api/ia/simulador-entrevista/categorias', function () {
    json_saida(['categorias' => categorias_disponiveis()]);
});

rota('POST', '/api/ia/assistente', function () {
    limitar_por_ip('ia-assistente', 30, 600);
    $dados = corpo_json();
    $pergunta = campo_obrigatorio($dados, 'pergunta');
    json_saida(assistente_responder($pergunta));
});

const NIVEIS_CONQUISTA = [[0, 'Iniciante'], [2, 'Em busca ativa'], [4, 'Candidato de destaque']];

rota('GET', '/api/conquistas', function () {
    $usuario = usuario_atual();
    $perfilCompleto = !empty($usuario['telefone']) && !empty($usuario['cidade']) && !empty($usuario['resumo']);

    $stmt = db()->prepare('SELECT COUNT(id) AS t FROM favoritos WHERE usuario_id = ?');
    $stmt->execute([$usuario['id']]);
    $totalFavoritos = (int) $stmt->fetch()['t'];

    $stmt = db()->prepare('SELECT COUNT(id) AS t FROM candidaturas WHERE email = ?');
    $stmt->execute([$usuario['email']]);
    $totalCandidaturas = (int) $stmt->fetch()['t'];

    $badges = [
        ['chave' => 'perfil_completo', 'titulo' => 'Perfil completo', 'descricao' => 'Preencheu nome, telefone, cidade e mini-currículo', 'icone' => '🧑‍💼', 'conquistado' => $perfilCompleto],
        ['chave' => 'primeira_vaga_salva', 'titulo' => 'Primeira vaga salva', 'descricao' => 'Salvou pelo menos uma vaga nos favoritos', 'icone' => '⭐', 'conquistado' => $totalFavoritos >= 1],
        ['chave' => 'colecionador', 'titulo' => 'Colecionador de oportunidades', 'descricao' => 'Salvou 5 ou mais vagas', 'icone' => '📌', 'conquistado' => $totalFavoritos >= 5],
        ['chave' => 'primeira_candidatura', 'titulo' => 'Primeira candidatura', 'descricao' => 'Enviou sua primeira candidatura pela plataforma', 'icone' => '📨', 'conquistado' => $totalCandidaturas >= 1],
    ];

    $totalConquistado = count(array_filter($badges, fn ($b) => $b['conquistado']));
    $nivel = NIVEIS_CONQUISTA[0][1];
    foreach (NIVEIS_CONQUISTA as [$minimo, $nomeNivel]) {
        if ($totalConquistado >= $minimo) {
            $nivel = $nomeNivel;
        }
    }

    json_saida(['badges' => $badges, 'total_conquistado' => $totalConquistado, 'total' => count($badges), 'nivel' => $nivel]);
});

function montar_where_alerta(array $alerta): array
{
    $where = [];
    $params = [];
    foreach (['cargo' => 'cargo', 'categoria' => 'categoria', 'cidade' => 'cidade'] as $campo => $coluna) {
        if (!empty($alerta[$campo])) {
            $where[] = "{$coluna} LIKE ?";
            $params[] = '%' . $alerta[$campo] . '%';
        }
    }
    if (!empty($alerta['estado'])) {
        $where[] = 'estado LIKE ?';
        $params[] = $alerta['estado'];
    }
    return [$where, $params];
}

function contar_vagas_do_alerta(array $alerta): int
{
    [$where, $params] = montar_where_alerta($alerta);
    $sql = 'SELECT COUNT(id) AS t FROM vagas' . ($where ? ' WHERE ' . implode(' AND ', $where) : '');
    $stmt = db()->prepare($sql);
    $stmt->execute($params);
    return (int) $stmt->fetch()['t'];
}

function contar_vagas_novas_do_alerta(array $alerta): int
{
    [$where, $params] = montar_where_alerta($alerta);
    if (!empty($alerta['vistas_em'])) {
        $where[] = 'criada_em > ?';
        $params[] = $alerta['vistas_em'];
    }
    $sql = 'SELECT COUNT(id) AS t FROM vagas' . ($where ? ' WHERE ' . implode(' AND ', $where) : '');
    $stmt = db()->prepare($sql);
    $stmt->execute($params);
    return (int) $stmt->fetch()['t'];
}

function alerta_para_json(array $a): array
{
    return [
        'id' => (int) $a['id'], 'cargo' => $a['cargo'], 'categoria' => $a['categoria'],
        'cidade' => $a['cidade'], 'estado' => $a['estado'],
        'criado_em' => $a['criado_em'] ? date('c', strtotime($a['criado_em'])) : null,
        'total_vagas' => contar_vagas_do_alerta($a), 'vagas_novas' => contar_vagas_novas_do_alerta($a),
    ];
}

rota('GET', '/api/alertas', function () {
    $usuario = usuario_atual();
    $stmt = db()->prepare('SELECT * FROM alertas WHERE usuario_id = ? ORDER BY id DESC');
    $stmt->execute([$usuario['id']]);
    json_saida(array_map('alerta_para_json', $stmt->fetchAll()));
});

rota('POST', '/api/alertas', function () {
    $usuario = usuario_atual();
    $dados = corpo_json();
    if (!array_filter([$dados['cargo'] ?? null, $dados['categoria'] ?? null, $dados['cidade'] ?? null, $dados['estado'] ?? null])) {
        json_erro(400, 'Preencha pelo menos um critério para o alerta');
    }
    $stmt = db()->prepare('SELECT COUNT(id) AS t FROM alertas WHERE usuario_id = ?');
    $stmt->execute([$usuario['id']]);
    if ((int) $stmt->fetch()['t'] >= 10) {
        json_erro(400, 'Limite de 10 alertas por conta');
    }
    db()->prepare('INSERT INTO alertas (usuario_id, cargo, categoria, cidade, estado) VALUES (?, ?, ?, ?, ?)')
        ->execute([$usuario['id'], $dados['cargo'] ?? null, $dados['categoria'] ?? null, $dados['cidade'] ?? null, $dados['estado'] ?? null]);
    $stmt = db()->prepare('SELECT * FROM alertas WHERE id = ?');
    $stmt->execute([db()->lastInsertId()]);
    json_saida(alerta_para_json($stmt->fetch()), 201);
});

rota('DELETE', '/api/alertas/{id}', function ($p) {
    $usuario = usuario_atual();
    db()->prepare('DELETE FROM alertas WHERE id = ? AND usuario_id = ?')->execute([$p['id'], $usuario['id']]);
    json_saida(['mensagem' => 'Alerta removido']);
});

rota('POST', '/api/alertas/{id}/marcar-visto', function ($p) {
    $usuario = usuario_atual();
    $stmt = db()->prepare('SELECT id FROM alertas WHERE id = ? AND usuario_id = ?');
    $stmt->execute([$p['id'], $usuario['id']]);
    if (!$stmt->fetch()) {
        json_erro(404, 'Alerta não encontrado');
    }
    db()->prepare('UPDATE alertas SET vistas_em = ? WHERE id = ?')->execute([gmdate('Y-m-d H:i:s'), $p['id']]);
    json_saida(['mensagem' => 'Alerta marcado como visto']);
});

rota('GET', '/api/minhas-candidaturas', function () {
    $usuario = usuario_atual();
    $stmt = db()->prepare('SELECT * FROM candidaturas WHERE email = ? ORDER BY id DESC');
    $stmt->execute([$usuario['email']]);
    $candidaturas = $stmt->fetchAll();
    $vagaIds = array_unique(array_column($candidaturas, 'vaga_id'));
    $vagasPorId = [];
    if ($vagaIds) {
        $in = implode(',', array_fill(0, count($vagaIds), '?'));
        $stmt = db()->prepare("SELECT * FROM vagas WHERE id IN ({$in})");
        $stmt->execute($vagaIds);
        foreach ($stmt->fetchAll() as $v) {
            $vagasPorId[$v['id']] = $v;
        }
    }
    json_saida(array_map(function ($c) use ($vagasPorId) {
        $v = $vagasPorId[$c['vaga_id']] ?? null;
        return [
            'id' => (int) $c['id'], 'vaga_id' => (int) $c['vaga_id'],
            'cargo' => $v['cargo'] ?? null, 'empresa' => $v['empresa'] ?? null,
            'criada_em' => $c['criada_em'] ? date('c', strtotime($c['criada_em'])) : null,
        ];
    }, $candidaturas));
});
