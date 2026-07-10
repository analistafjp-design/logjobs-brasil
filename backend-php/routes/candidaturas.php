<?php
declare(strict_types=1);

rota('POST', '/api/candidaturas', function () {
    $dados = corpo_json();
    if (!empty($dados['empresa_no_meio'])) {
        json_erro(400, 'Requisição inválida'); // honeypot
    }
    limitar_por_ip('candidatura', 5, 600);

    $vagaId = campo_obrigatorio($dados, 'vaga_id');
    $nome = campo_obrigatorio($dados, 'nome');
    $email = campo_obrigatorio($dados, 'email');
    if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
        json_erro(422, 'E-mail inválido');
    }

    $vaga = buscar_vaga((int) $vagaId);
    if (!$vaga) {
        json_erro(404, 'Vaga não encontrada');
    }

    db()->prepare('INSERT INTO candidaturas (vaga_id, nome, email, telefone) VALUES (?, ?, ?, ?)')
        ->execute([$vagaId, $nome, $email, $dados['telefone'] ?? null]);

    json_saida(['id' => (int) db()->lastInsertId(), 'mensagem' => 'Candidatura enviada com sucesso!']);
});

rota('POST', '/api/interessados', function () {
    $dados = corpo_json();
    if (!empty($dados['empresa_no_meio'])) {
        json_erro(400, 'Requisição inválida');
    }
    limitar_por_ip('interessado', 5, 600);

    $nome = campo_obrigatorio($dados, 'nome');
    $email = campo_obrigatorio($dados, 'email');
    $tipo = campo_obrigatorio($dados, 'tipo');
    if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
        json_erro(422, 'E-mail inválido');
    }

    db()->prepare('INSERT INTO interessados (nome, email, tipo) VALUES (?, ?, ?)')->execute([$nome, $email, $tipo]);
    json_saida(['id' => (int) db()->lastInsertId(), 'mensagem' => 'Cadastro recebido! Avisaremos você em breve.']);
});
