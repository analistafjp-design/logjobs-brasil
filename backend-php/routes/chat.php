<?php
declare(strict_types=1);

// Porta REST de main.py (linhas ~1770-1944). O WebSocket original (/ws/chat/{id}), que
// entrega mensagens em tempo real para quem está com a tela aberta, NÃO tem
// equivalente em hospedagem compartilhada (Apache/PHP-FPM não mantém processos de
// longa duração) — por isso o envio/recebimento aqui é só REST, e o frontend
// (frontend/js/chat.js) precisa fazer polling periódico em vez de abrir WebSocket.
// Ver MIGRACAO_HOSTINGER.md para detalhes dessa limitação.

function mensagem_para_json(array $mensagem, int $usuarioId): array
{
    return [
        'id' => (int) $mensagem['id'], 'texto' => $mensagem['texto'],
        'de_mim' => (int) $mensagem['remetente_id'] === $usuarioId,
        'criada_em' => $mensagem['criada_em'] ? date('c', strtotime($mensagem['criada_em'])) : null,
        'lida_em' => $mensagem['lida_em'] ? date('c', strtotime($mensagem['lida_em'])) : null,
    ];
}

function obter_conversa_do_participante(int $conversaId, array $usuario): array
{
    $stmt = db()->prepare('SELECT * FROM conversas WHERE id = ?');
    $stmt->execute([$conversaId]);
    $conversa = $stmt->fetch();
    if (!$conversa || !in_array($usuario['id'], [(int) $conversa['candidato_id'], (int) $conversa['empresa_id']], true)) {
        json_erro(404, 'Conversa não encontrada');
    }
    return $conversa;
}

function registrar_mensagem(int $conversaId, int $remetenteId, string $texto): array
{
    db()->prepare('INSERT INTO mensagens (conversa_id, remetente_id, texto) VALUES (?, ?, ?)')
        ->execute([$conversaId, $remetenteId, $texto]);
    db()->prepare('UPDATE conversas SET atualizada_em = ? WHERE id = ?')->execute([gmdate('Y-m-d H:i:s'), $conversaId]);
    $stmt = db()->prepare('SELECT * FROM mensagens WHERE id = ?');
    $stmt->execute([db()->lastInsertId()]);
    return $stmt->fetch();
}

rota('POST', '/api/chat/conversas', function () {
    $usuario = usuario_atual();
    limitar_por_ip('chat-iniciar', 20, 600);
    $dados = corpo_json();
    $mensagemTexto = campo_obrigatorio($dados, 'mensagem');

    if ($usuario['tipo'] === 'candidato') {
        $vagaId = $dados['vaga_id'] ?? null;
        if (!$vagaId) {
            json_erro(400, 'Informe a vaga para iniciar a conversa com a empresa');
        }
        $vaga = buscar_vaga((int) $vagaId);
        if (!$vaga) {
            json_erro(404, 'Vaga não encontrada');
        }
        if (!$vaga['usuario_id']) {
            json_erro(400, 'Esta vaga não tem uma empresa disponível para chat');
        }
        $candidatoId = $usuario['id'];
        $empresaId = (int) $vaga['usuario_id'];
        $vagaIdConversa = (int) $vaga['id'];
    } elseif ($usuario['tipo'] === 'empresa') {
        $candidaturaId = $dados['candidatura_id'] ?? null;
        if (!$candidaturaId) {
            json_erro(400, 'Informe a candidatura para iniciar a conversa com o candidato');
        }
        $stmt = db()->prepare('SELECT * FROM candidaturas WHERE id = ?');
        $stmt->execute([$candidaturaId]);
        $candidatura = $stmt->fetch();
        $vagaDaCandidatura = null;
        if ($candidatura) {
            $stmt = db()->prepare('SELECT * FROM vagas WHERE id = ? AND usuario_id = ?');
            $stmt->execute([$candidatura['vaga_id'], $usuario['id']]);
            $vagaDaCandidatura = $stmt->fetch();
        }
        if (!$candidatura || !$vagaDaCandidatura) {
            json_erro(404, 'Candidatura não encontrada');
        }
        $stmt = db()->prepare('SELECT * FROM usuarios WHERE LOWER(email) = LOWER(?) AND tipo = ?');
        $stmt->execute([$candidatura['email'], 'candidato']);
        $candidato = $stmt->fetch();
        if (!$candidato) {
            json_erro(404, 'Este candidato ainda não tem conta na plataforma para receber mensagens');
        }
        $candidatoId = (int) $candidato['id'];
        $empresaId = $usuario['id'];
        $vagaIdConversa = (int) $vagaDaCandidatura['id'];
    } else {
        json_erro(403, 'Este tipo de conta não pode iniciar conversas');
    }

    $stmt = db()->prepare('SELECT * FROM conversas WHERE candidato_id = ? AND empresa_id = ?');
    $stmt->execute([$candidatoId, $empresaId]);
    $conversa = $stmt->fetch();
    if (!$conversa) {
        db()->prepare('INSERT INTO conversas (candidato_id, empresa_id, vaga_id) VALUES (?, ?, ?)')
            ->execute([$candidatoId, $empresaId, $vagaIdConversa]);
        $conversaId = (int) db()->lastInsertId();
    } else {
        $conversaId = (int) $conversa['id'];
    }

    $mensagem = registrar_mensagem($conversaId, $usuario['id'], $mensagemTexto);
    json_saida(['conversa_id' => $conversaId, 'mensagem' => mensagem_para_json($mensagem, $usuario['id'])], 201);
});

rota('GET', '/api/chat/conversas', function () {
    $usuario = usuario_atual();
    if (!in_array($usuario['tipo'], ['candidato', 'empresa'], true)) {
        json_saida([]);
    }
    $campoProprio = $usuario['tipo'] === 'candidato' ? 'candidato_id' : 'empresa_id';
    $stmt = db()->prepare("SELECT * FROM conversas WHERE {$campoProprio} = ? ORDER BY atualizada_em DESC");
    $stmt->execute([$usuario['id']]);
    $conversas = $stmt->fetchAll();
    if (!$conversas) {
        json_saida([]);
    }

    $outroIds = array_map(fn ($c) => $usuario['tipo'] === 'candidato' ? (int) $c['empresa_id'] : (int) $c['candidato_id'], $conversas);
    $outroIds = array_unique($outroIds);
    $in = implode(',', array_fill(0, count($outroIds), '?'));
    $stmt = db()->prepare("SELECT * FROM usuarios WHERE id IN ({$in})");
    $stmt->execute($outroIds);
    $outros = [];
    foreach ($stmt->fetchAll() as $u) {
        $outros[$u['id']] = $u;
    }

    $vagaIds = array_filter(array_column($conversas, 'vaga_id'));
    $vagas = [];
    if ($vagaIds) {
        $in = implode(',', array_fill(0, count($vagaIds), '?'));
        $stmt = db()->prepare("SELECT * FROM vagas WHERE id IN ({$in})");
        $stmt->execute($vagaIds);
        foreach ($stmt->fetchAll() as $v) {
            $vagas[$v['id']] = $v;
        }
    }

    $resultado = [];
    foreach ($conversas as $c) {
        $outroId = $usuario['tipo'] === 'candidato' ? (int) $c['empresa_id'] : (int) $c['candidato_id'];
        $outro = $outros[$outroId] ?? null;
        $stmt = db()->prepare('SELECT * FROM mensagens WHERE conversa_id = ? ORDER BY id DESC LIMIT 1');
        $stmt->execute([$c['id']]);
        $ultima = $stmt->fetch();
        $stmt = db()->prepare('SELECT COUNT(id) AS t FROM mensagens WHERE conversa_id = ? AND remetente_id != ? AND lida_em IS NULL');
        $stmt->execute([$c['id'], $usuario['id']]);
        $naoLidas = (int) $stmt->fetch()['t'];
        $vaga = $vagas[$c['vaga_id']] ?? null;

        $resultado[] = [
            'id' => (int) $c['id'],
            'outro_usuario' => $outro ? ['id' => (int) $outro['id'], 'nome' => $outro['nome']] : null,
            'vaga' => $vaga ? ['id' => (int) $vaga['id'], 'cargo' => $vaga['cargo']] : null,
            'ultima_mensagem' => $ultima ? mensagem_para_json($ultima, $usuario['id']) : null,
            'nao_lidas' => $naoLidas,
            'atualizada_em' => $c['atualizada_em'] ? date('c', strtotime($c['atualizada_em'])) : null,
        ];
    }
    json_saida($resultado);
});

rota('GET', '/api/chat/conversas/{id}/mensagens', function ($p) {
    $usuario = usuario_atual();
    $conversa = obter_conversa_do_participante((int) $p['id'], $usuario);
    $stmt = db()->prepare('SELECT * FROM mensagens WHERE conversa_id = ? ORDER BY id ASC');
    $stmt->execute([$conversa['id']]);
    $mensagens = $stmt->fetchAll();

    $idsParaMarcar = array_column(array_filter($mensagens, fn ($m) => (int) $m['remetente_id'] !== $usuario['id'] && $m['lida_em'] === null), 'id');
    if ($idsParaMarcar) {
        $in = implode(',', array_fill(0, count($idsParaMarcar), '?'));
        db()->prepare("UPDATE mensagens SET lida_em = ? WHERE id IN ({$in})")
            ->execute(array_merge([gmdate('Y-m-d H:i:s')], $idsParaMarcar));
    }

    json_saida(['mensagens' => array_map(fn ($m) => mensagem_para_json($m, $usuario['id']), $mensagens)]);
});

rota('POST', '/api/chat/conversas/{id}/mensagens', function ($p) {
    $usuario = usuario_atual();
    limitar_por_ip('chat-mensagem', 60, 600);
    $conversa = obter_conversa_do_participante((int) $p['id'], $usuario);
    $dados = corpo_json();
    $texto = campo_obrigatorio($dados, 'texto');
    $mensagem = registrar_mensagem((int) $conversa['id'], $usuario['id'], $texto);
    json_saida(mensagem_para_json($mensagem, $usuario['id']), 201);
});
