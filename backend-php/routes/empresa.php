<?php
declare(strict_types=1);

function verificar_empresa(): array
{
    $usuario = usuario_atual();
    if ($usuario['tipo'] !== 'empresa') {
        json_erro(403, 'Recurso disponível apenas para contas de empresa');
    }
    return $usuario;
}

function buscar_vaga_da_empresa(int $vagaId, int $usuarioId): array
{
    $stmt = db()->prepare('SELECT * FROM vagas WHERE id = ? AND usuario_id = ?');
    $stmt->execute([$vagaId, $usuarioId]);
    $vaga = $stmt->fetch();
    if (!$vaga) {
        json_erro(404, 'Vaga não encontrada');
    }
    return $vaga;
}

rota('GET', '/api/empresa/vagas', function () {
    $usuario = verificar_empresa();
    $where = ['usuario_id = ?'];
    $params = [$usuario['id']];
    if (!empty($_GET['q'])) {
        $where[] = '(cargo LIKE ? OR cidade LIKE ?)';
        $params[] = '%' . $_GET['q'] . '%';
        $params[] = '%' . $_GET['q'] . '%';
    }
    if (($_GET['status'] ?? '') === 'ativa') {
        $where[] = '(pausada IS NULL OR pausada = 0)';
    } elseif (($_GET['status'] ?? '') === 'pausada') {
        $where[] = 'pausada = 1';
    }
    $stmt = db()->prepare('SELECT * FROM vagas WHERE ' . implode(' AND ', $where) . ' ORDER BY id DESC');
    $stmt->execute($params);
    $vagas = $stmt->fetchAll();

    $vagaIds = array_column($vagas, 'id');
    $candidaturasPorVaga = [];
    if ($vagaIds) {
        $in = implode(',', array_fill(0, count($vagaIds), '?'));
        $stmt = db()->prepare("SELECT vaga_id, COUNT(id) AS total FROM candidaturas WHERE vaga_id IN ({$in}) GROUP BY vaga_id");
        $stmt->execute($vagaIds);
        foreach ($stmt->fetchAll() as $l) {
            $candidaturasPorVaga[$l['vaga_id']] = (int) $l['total'];
        }
    }

    json_saida(array_map(fn ($v) => array_merge(vaga_admin_para_json($v), [
        'total_candidaturas' => $candidaturasPorVaga[$v['id']] ?? 0,
    ]), $vagas));
});

rota('POST', '/api/empresa/vagas', function () {
    $usuario = verificar_empresa();
    $dados = validar_vaga_entrada(corpo_json(), true);
    $id = inserir_vaga($dados, 'empresa', $usuario['id']);
    json_saida(vaga_admin_para_json(buscar_vaga($id)), 201);
});

rota('PATCH', '/api/empresa/vagas/{id}', function ($p) {
    $usuario = verificar_empresa();
    buscar_vaga_da_empresa((int) $p['id'], $usuario['id']);
    $dados = corpo_json();
    $camposPermitidos = array_merge(CAMPOS_VAGA_ENTRADA, ['pausada']);
    $limpo = array_intersect_key($dados, array_flip($camposPermitidos));
    atualizar_vaga((int) $p['id'], $limpo);
    json_saida(vaga_admin_para_json(buscar_vaga((int) $p['id'])));
});

rota('DELETE', '/api/empresa/vagas/{id}', function ($p) {
    $usuario = verificar_empresa();
    buscar_vaga_da_empresa((int) $p['id'], $usuario['id']);
    db()->prepare('DELETE FROM candidaturas WHERE vaga_id = ?')->execute([$p['id']]);
    db()->prepare('DELETE FROM vagas WHERE id = ?')->execute([$p['id']]);
    json_saida(['mensagem' => 'Vaga excluída']);
});

rota('POST', '/api/empresa/vagas/{id}/pausar', function ($p) {
    $usuario = verificar_empresa();
    buscar_vaga_da_empresa((int) $p['id'], $usuario['id']);
    db()->prepare('UPDATE vagas SET pausada = 1 WHERE id = ?')->execute([$p['id']]);
    json_saida(vaga_admin_para_json(buscar_vaga((int) $p['id'])));
});

rota('POST', '/api/empresa/vagas/{id}/reativar', function ($p) {
    $usuario = verificar_empresa();
    buscar_vaga_da_empresa((int) $p['id'], $usuario['id']);
    db()->prepare('UPDATE vagas SET pausada = 0 WHERE id = ?')->execute([$p['id']]);
    json_saida(vaga_admin_para_json(buscar_vaga((int) $p['id'])));
});

rota('POST', '/api/empresa/vagas/{id}/renovar', function ($p) {
    $usuario = verificar_empresa();
    buscar_vaga_da_empresa((int) $p['id'], $usuario['id']);
    db()->prepare('UPDATE vagas SET pausada = 0, criada_em = ? WHERE id = ?')->execute([gmdate('Y-m-d H:i:s'), $p['id']]);
    json_saida(vaga_admin_para_json(buscar_vaga((int) $p['id'])));
});

rota('GET', '/api/empresa/candidaturas-exportar', function () {
    $usuario = verificar_empresa();
    $stmt = db()->prepare('SELECT * FROM vagas WHERE usuario_id = ?');
    $stmt->execute([$usuario['id']]);
    $vagas = $stmt->fetchAll();
    $vagasPorId = [];
    foreach ($vagas as $v) {
        $vagasPorId[$v['id']] = $v;
    }

    $candidaturas = [];
    if ($vagasPorId) {
        $in = implode(',', array_fill(0, count($vagasPorId), '?'));
        $stmt = db()->prepare("SELECT * FROM candidaturas WHERE vaga_id IN ({$in}) ORDER BY vaga_id, id DESC");
        $stmt->execute(array_keys($vagasPorId));
        $candidaturas = $stmt->fetchAll();
    }

    $linhas = ['Vaga,Cidade/UF,Nome,E-mail,Telefone,Data da candidatura'];
    foreach ($candidaturas as $c) {
        $vaga = $vagasPorId[$c['vaga_id']] ?? null;
        $campos = [
            $vaga['cargo'] ?? '', $vaga ? "{$vaga['cidade']}/{$vaga['estado']}" : '',
            $c['nome'], $c['email'], $c['telefone'] ?? '',
            $c['criada_em'] ? date('c', strtotime($c['criada_em'])) : '',
        ];
        $linhas[] = implode(',', array_map(fn ($campo) => '"' . str_replace('"', '""', (string) $campo) . '"', $campos));
    }

    header('Content-Type: text/csv; charset=utf-8');
    header('Content-Disposition: attachment; filename=candidaturas.csv');
    echo implode("\n", $linhas);
    exit;
});

rota('GET', '/api/empresa/candidaturas/{id}', function ($p) {
    $usuario = verificar_empresa();
    buscar_vaga_da_empresa((int) $p['id'], $usuario['id']);
    $stmt = db()->prepare('SELECT * FROM candidaturas WHERE vaga_id = ? ORDER BY id DESC');
    $stmt->execute([$p['id']]);
    json_saida(array_map(fn ($c) => [
        'id' => (int) $c['id'], 'nome' => $c['nome'], 'email' => $c['email'], 'telefone' => $c['telefone'],
        'criada_em' => $c['criada_em'] ? date('c', strtotime($c['criada_em'])) : null,
    ], $stmt->fetchAll()));
});

rota('GET', '/api/empresa/estatisticas', function () {
    $usuario = verificar_empresa();
    $stmt = db()->prepare('SELECT * FROM vagas WHERE usuario_id = ?');
    $stmt->execute([$usuario['id']]);
    $vagas = $stmt->fetchAll();
    $vagaIds = array_column($vagas, 'id');

    $totalCandidaturas = 0;
    $candidaturasNovas = 0;
    $porVaga = [];
    if ($vagaIds) {
        $in = implode(',', array_fill(0, count($vagaIds), '?'));
        $stmt = db()->prepare("SELECT COUNT(id) AS t FROM candidaturas WHERE vaga_id IN ({$in})");
        $stmt->execute($vagaIds);
        $totalCandidaturas = (int) $stmt->fetch()['t'];

        $sqlNovas = "SELECT COUNT(id) AS t FROM candidaturas WHERE vaga_id IN ({$in})";
        $paramsNovas = $vagaIds;
        if (!empty($usuario['candidaturas_vistas_em'])) {
            $sqlNovas .= ' AND criada_em > ?';
            $paramsNovas[] = $usuario['candidaturas_vistas_em'];
        }
        $stmt = db()->prepare($sqlNovas);
        $stmt->execute($paramsNovas);
        $candidaturasNovas = (int) $stmt->fetch()['t'];

        $stmt = db()->prepare("SELECT vaga_id, COUNT(id) AS total FROM candidaturas WHERE vaga_id IN ({$in}) GROUP BY vaga_id");
        $stmt->execute($vagaIds);
        foreach ($stmt->fetchAll() as $l) {
            $porVaga[$l['vaga_id']] = (int) $l['total'];
        }
    }

    $candidaturasPorVaga = [];
    foreach ($vagas as $v) {
        $total = $porVaga[$v['id']] ?? 0;
        if ($total > 0) {
            $candidaturasPorVaga[] = ['cargo' => "{$v['cargo']} ({$v['cidade']})", 'total' => $total];
        }
    }
    usort($candidaturasPorVaga, fn ($a, $b) => $b['total'] <=> $a['total']);
    $candidaturasPorVaga = array_slice($candidaturasPorVaga, 0, 10);

    $vagasAtivas = count(array_filter($vagas, fn ($v) => !$v['pausada']));
    $vagasPausadas = count(array_filter($vagas, fn ($v) => $v['pausada']));

    json_saida([
        'total_vagas' => count($vagaIds), 'vagas_ativas' => $vagasAtivas, 'vagas_pausadas' => $vagasPausadas,
        'total_candidaturas' => $totalCandidaturas, 'candidaturas_novas' => $candidaturasNovas,
        'candidaturas_por_vaga' => $candidaturasPorVaga,
    ]);
});

rota('POST', '/api/empresa/candidaturas/marcar-vistas', function () {
    $usuario = verificar_empresa();
    db()->prepare('UPDATE usuarios SET candidaturas_vistas_em = ? WHERE id = ?')->execute([gmdate('Y-m-d H:i:s'), $usuario['id']]);
    json_saida(['mensagem' => 'Candidaturas marcadas como vistas']);
});
