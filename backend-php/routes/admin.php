<?php
declare(strict_types=1);

function vaga_admin_para_json(array $v): array
{
    return [
        'id' => (int) $v['id'], 'cargo' => $v['cargo'], 'empresa' => $v['empresa'],
        'cidade' => $v['cidade'], 'estado' => $v['estado'],
        'salario' => $v['salario'] !== null ? (float) $v['salario'] : null,
        'modalidade' => $v['modalidade'], 'turno' => $v['turno'],
        'tipo_contratacao' => $v['tipo_contratacao'], 'veiculo' => $v['veiculo'],
        'categoria' => $v['categoria'], 'descricao' => $v['descricao'],
        'beneficios' => $v['beneficios'], 'requisitos' => $v['requisitos'],
        'link' => $v['link'], 'fonte' => $v['fonte'], 'pausada' => (bool) $v['pausada'],
        'criada_em' => $v['criada_em'] ? date('c', strtotime($v['criada_em'])) : null,
    ];
}

const CAMPOS_VAGA_ENTRADA = ['cargo', 'empresa', 'cidade', 'estado', 'categoria', 'salario', 'modalidade', 'turno', 'tipo_contratacao', 'veiculo', 'descricao', 'beneficios', 'requisitos', 'link'];
const CAMPOS_VAGA_OBRIGATORIOS = ['cargo', 'empresa', 'cidade', 'estado', 'categoria'];

function validar_vaga_entrada(array $dados, bool $exigirObrigatorios): array
{
    $limpo = [];
    foreach (CAMPOS_VAGA_ENTRADA as $campo) {
        if (array_key_exists($campo, $dados)) {
            $limpo[$campo] = $dados[$campo];
        }
    }
    if ($exigirObrigatorios) {
        foreach (CAMPOS_VAGA_OBRIGATORIOS as $campo) {
            if (empty($limpo[$campo])) {
                json_erro(422, "Campo obrigatório ausente: {$campo}");
            }
        }
    }
    return $limpo;
}

function inserir_vaga(array $dados, string $fonte, ?int $usuarioId = null): int
{
    $colunas = array_keys($dados);
    $colunas[] = 'fonte';
    $dados['fonte'] = $fonte;
    if ($usuarioId !== null) {
        $colunas[] = 'usuario_id';
        $dados['usuario_id'] = $usuarioId;
    }
    $placeholders = implode(', ', array_fill(0, count($colunas), '?'));
    $sql = 'INSERT INTO vagas (' . implode(', ', $colunas) . ") VALUES ({$placeholders})";
    try {
        db()->prepare($sql)->execute(array_values($dados));
    } catch (PDOException $e) {
        if ($e->getCode() === '23000') {
            json_erro(400, 'Já existe uma vaga com esse cargo, empresa e cidade');
        }
        throw $e;
    }
    return (int) db()->lastInsertId();
}

function buscar_vaga(int $id): ?array
{
    $stmt = db()->prepare('SELECT * FROM vagas WHERE id = ?');
    $stmt->execute([$id]);
    return $stmt->fetch() ?: null;
}

function atualizar_vaga(int $id, array $dados): void
{
    if (!$dados) {
        return;
    }
    $sets = implode(', ', array_map(fn ($c) => "{$c} = ?", array_keys($dados)));
    $valores = array_values($dados);
    $valores[] = $id;
    try {
        db()->prepare("UPDATE vagas SET {$sets} WHERE id = ?")->execute($valores);
    } catch (PDOException $e) {
        if ($e->getCode() === '23000') {
            json_erro(400, 'Já existe uma vaga com esse cargo, empresa e cidade');
        }
        throw $e;
    }
}

rota('GET', '/api/admin/verificar', function () {
    verificar_admin();
    json_saida(['ok' => true]);
});

rota('GET', '/api/admin/vagas', function () {
    verificar_admin();
    $q = $_GET['q'] ?? '';
    $limit = min((int) ($_GET['limit'] ?? 50), 200);
    $offset = max((int) ($_GET['offset'] ?? 0), 0);
    if ($q !== '') {
        $where = '(cargo LIKE ? OR empresa LIKE ? OR cidade LIKE ?)';
        $params = ["%{$q}%", "%{$q}%", "%{$q}%"];
    } else {
        $where = '1=1';
        $params = [];
    }
    $total = db()->prepare("SELECT COUNT(*) AS t FROM vagas WHERE {$where}");
    $total->execute($params);
    $total = (int) $total->fetch()['t'];

    $stmt = db()->prepare("SELECT * FROM vagas WHERE {$where} ORDER BY id DESC LIMIT {$limit} OFFSET {$offset}");
    $stmt->execute($params);
    json_saida(['total' => $total, 'vagas' => array_map('vaga_admin_para_json', $stmt->fetchAll())]);
});

rota('POST', '/api/admin/vagas', function () {
    verificar_admin();
    $dados = validar_vaga_entrada(corpo_json(), true);
    $id = inserir_vaga($dados, 'manual');
    $vaga = buscar_vaga($id);
    registrar_auditoria('criar_vaga', "vaga_id={$id} cargo=" . json_encode($vaga['cargo']) . ' empresa=' . json_encode($vaga['empresa']));
    json_saida(vaga_admin_para_json($vaga), 201);
});

rota('PATCH', '/api/admin/vagas/{id}', function ($p) {
    verificar_admin();
    $vaga = buscar_vaga((int) $p['id']);
    if (!$vaga) {
        json_erro(404, 'Vaga não encontrada');
    }
    $dados = corpo_json();
    $camposPermitidos = array_merge(CAMPOS_VAGA_ENTRADA, ['pausada']);
    $limpo = array_intersect_key($dados, array_flip($camposPermitidos));
    atualizar_vaga((int) $p['id'], $limpo);
    registrar_auditoria('editar_vaga', "vaga_id={$p['id']}");
    json_saida(vaga_admin_para_json(buscar_vaga((int) $p['id'])));
});

rota('DELETE', '/api/admin/vagas/{id}', function ($p) {
    verificar_admin();
    $vaga = buscar_vaga((int) $p['id']);
    if (!$vaga) {
        json_erro(404, 'Vaga não encontrada');
    }
    db()->prepare('DELETE FROM candidaturas WHERE vaga_id = ?')->execute([$p['id']]);
    db()->prepare('DELETE FROM vagas WHERE id = ?')->execute([$p['id']]);
    registrar_auditoria('excluir_vaga', "vaga_id={$p['id']} cargo=" . json_encode($vaga['cargo']) . ' empresa=' . json_encode($vaga['empresa']));
    json_saida(['mensagem' => 'Vaga excluída']);
});

rota('GET', '/api/admin/candidaturas', function () {
    verificar_admin();
    $limit = min((int) ($_GET['limit'] ?? 50), 200);
    $candidaturas = db()->query("SELECT * FROM candidaturas ORDER BY id DESC LIMIT {$limit}")->fetchAll();
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
            'id' => (int) $c['id'], 'nome' => $c['nome'], 'email' => $c['email'], 'telefone' => $c['telefone'],
            'vaga_id' => (int) $c['vaga_id'], 'vaga_cargo' => $v['cargo'] ?? null, 'vaga_empresa' => $v['empresa'] ?? null,
            'criada_em' => $c['criada_em'] ? date('c', strtotime($c['criada_em'])) : null,
        ];
    }, $candidaturas));
});

rota('GET', '/api/admin/interessados', function () {
    verificar_admin();
    $limit = min((int) ($_GET['limit'] ?? 50), 200);
    $interessados = db()->query("SELECT * FROM interessados ORDER BY id DESC LIMIT {$limit}")->fetchAll();
    json_saida(array_map(fn ($i) => [
        'id' => (int) $i['id'], 'nome' => $i['nome'], 'email' => $i['email'], 'tipo' => $i['tipo'],
        'criado_em' => $i['criado_em'] ? date('c', strtotime($i['criado_em'])) : null,
    ], $interessados));
});

rota('GET', '/api/admin/usuarios', function () {
    verificar_admin();
    $q = $_GET['q'] ?? '';
    $limit = min((int) ($_GET['limit'] ?? 50), 200);
    if ($q !== '') {
        $stmt = db()->prepare("SELECT * FROM usuarios WHERE nome LIKE ? OR email LIKE ? ORDER BY id DESC LIMIT {$limit}");
        $stmt->execute(["%{$q}%", "%{$q}%"]);
    } else {
        $stmt = db()->query("SELECT * FROM usuarios ORDER BY id DESC LIMIT {$limit}");
    }
    json_saida(array_map(fn ($u) => [
        'id' => (int) $u['id'], 'nome' => $u['nome'], 'email' => $u['email'], 'tipo' => $u['tipo'],
        'cidade' => $u['cidade'], 'criado_em' => $u['criado_em'] ? date('c', strtotime($u['criado_em'])) : null,
    ], $stmt->fetchAll()));
});

rota('DELETE', '/api/admin/usuarios/{id}', function ($p) {
    verificar_admin();
    $usuario = buscar_usuario_por_id((int) $p['id']);
    if (!$usuario) {
        json_erro(404, 'Usuário não encontrado');
    }
    excluir_usuario_em_cascata((int) $p['id']);
    registrar_auditoria('excluir_usuario', "usuario_id={$usuario['id']} email=" . json_encode($usuario['email']) . " tipo={$usuario['tipo']}");
    json_saida(['mensagem' => 'Usuário excluído']);
});

rota('GET', '/api/admin/dashboard', function () {
    verificar_admin();
    $usuariosPorTipo = [];
    foreach (db()->query('SELECT tipo, COUNT(id) AS total FROM usuarios GROUP BY tipo')->fetchAll() as $l) {
        $usuariosPorTipo[$l['tipo']] = (int) $l['total'];
    }
    $vagasPorFonte = db()->query('SELECT fonte, COUNT(id) AS total FROM vagas GROUP BY fonte')->fetchAll();

    json_saida([
        'total_usuarios' => array_sum($usuariosPorTipo),
        'candidatos' => $usuariosPorTipo['candidato'] ?? 0,
        'empresas' => $usuariosPorTipo['empresa'] ?? 0,
        'total_vagas' => (int) db()->query('SELECT COUNT(id) AS t FROM vagas')->fetch()['t'],
        'vagas_por_fonte' => array_map(fn ($l) => ['fonte' => $l['fonte'], 'total' => (int) $l['total']], $vagasPorFonte),
        'total_candidaturas' => (int) db()->query('SELECT COUNT(id) AS t FROM candidaturas')->fetch()['t'],
        'total_interessados' => (int) db()->query('SELECT COUNT(id) AS t FROM interessados')->fetch()['t'],
    ]);
});

rota('GET', '/api/admin/auditoria', function () {
    verificar_admin();
    $limit = min((int) ($_GET['limit'] ?? 100), 500);
    $logs = db()->query("SELECT * FROM logs_auditoria ORDER BY id DESC LIMIT {$limit}")->fetchAll();
    json_saida(['logs' => array_map(fn ($l) => [
        'id' => (int) $l['id'], 'acao' => $l['acao'], 'detalhes' => $l['detalhes'], 'ip' => $l['ip'],
        'criado_em' => $l['criado_em'] ? date('c', strtotime($l['criado_em'])) : null,
    ], $logs)]);
});

function excluir_usuario_em_cascata(int $usuarioId): void
{
    $pdo = db();
    $pdo->prepare('DELETE FROM favoritos WHERE usuario_id = ?')->execute([$usuarioId]);
    $pdo->prepare('DELETE FROM alertas WHERE usuario_id = ?')->execute([$usuarioId]);

    $stmt = $pdo->prepare('SELECT id FROM vagas WHERE usuario_id = ?');
    $stmt->execute([$usuarioId]);
    $vagaIds = array_column($stmt->fetchAll(), 'id');
    if ($vagaIds) {
        $in = implode(',', array_fill(0, count($vagaIds), '?'));
        $pdo->prepare("DELETE FROM candidaturas WHERE vaga_id IN ({$in})")->execute($vagaIds);
        $pdo->prepare('DELETE FROM vagas WHERE usuario_id = ?')->execute([$usuarioId]);
    }
    $pdo->prepare('DELETE FROM usuarios WHERE id = ?')->execute([$usuarioId]);
}
