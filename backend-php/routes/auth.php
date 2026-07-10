<?php
declare(strict_types=1);

function calcular_completude_perfil(array $usuario): int
{
    if ($usuario['tipo'] !== 'candidato') {
        return 100;
    }
    $campos = [
        !empty($usuario['telefone']), !empty($usuario['cidade']), !empty($usuario['resumo']), !empty($usuario['habilidades']),
        !empty($usuario['pretensao_salarial']), !empty($usuario['disponibilidade']),
        (bool) lista_json($usuario['experiencias_json']), (bool) lista_json($usuario['formacoes_json']),
        !empty($usuario['idiomas_json']) && (bool) lista_json($usuario['idiomas_json']),
        !empty($usuario['linkedin_url']) || !empty($usuario['portfolio_url']) || !empty($usuario['github_url']),
    ];
    return (int) round(100 * count(array_filter($campos)) / count($campos));
}

function usuario_para_json(array $u): array
{
    return [
        'id' => (int) $u['id'], 'nome' => $u['nome'], 'email' => $u['email'], 'tipo' => $u['tipo'],
        'telefone' => $u['telefone'], 'cidade' => $u['cidade'], 'resumo' => $u['resumo'], 'habilidades' => $u['habilidades'],
        'pretensao_salarial' => $u['pretensao_salarial'] !== null ? (float) $u['pretensao_salarial'] : null,
        'disponibilidade' => $u['disponibilidade'], 'possui_cnh' => $u['possui_cnh'], 'veiculo_proprio' => $u['veiculo_proprio'],
        'portfolio_url' => $u['portfolio_url'], 'linkedin_url' => $u['linkedin_url'], 'github_url' => $u['github_url'],
        'logo_url' => $u['logo_url'], 'site_url' => $u['site_url'], 'instagram_url' => $u['instagram_url'],
        'experiencias' => lista_json($u['experiencias_json']), 'formacoes' => lista_json($u['formacoes_json']),
        'cursos' => lista_json($u['cursos_json']), 'certificados' => lista_json($u['certificados_json']),
        'idiomas' => lista_json($u['idiomas_json']), 'totp_ativado' => (bool) $u['totp_ativado'],
        'perfil_completude' => calcular_completude_perfil($u),
    ];
}

rota('POST', '/api/auth/registro', function () {
    limitar_por_ip('auth-registro', 10, 600);
    $dados = corpo_json();
    $nome = campo_obrigatorio($dados, 'nome');
    $email = campo_obrigatorio($dados, 'email');
    $senha = campo_obrigatorio($dados, 'senha');
    $tipo = $dados['tipo'] ?? 'candidato';

    if (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
        json_erro(422, 'E-mail inválido');
    }
    if (strlen($senha) < 6) {
        json_erro(400, 'A senha precisa ter pelo menos 6 caracteres');
    }
    if (!in_array($tipo, ['candidato', 'empresa'], true)) {
        json_erro(400, 'Tipo de conta inválido');
    }
    if (buscar_usuario_por_email($email)) {
        json_erro(400, 'Este e-mail já está cadastrado');
    }

    db()->prepare('INSERT INTO usuarios (nome, email, senha_hash, tipo) VALUES (?, ?, ?, ?)')
        ->execute([$nome, $email, hash_password($senha), $tipo]);
    $usuario = buscar_usuario_por_id((int) db()->lastInsertId());

    json_saida([
        'access_token' => criar_token($usuario['id']),
        'refresh_token' => criar_refresh_token($usuario['id']),
        'usuario' => usuario_para_json($usuario),
    ], 201);
});

rota('POST', '/api/auth/login', function () {
    limitar_por_ip('auth-login', 10, 600);
    $dados = corpo_json();
    $email = campo_obrigatorio($dados, 'email');
    $senha = campo_obrigatorio($dados, 'senha');

    $usuario = buscar_usuario_por_email($email);
    if (!$usuario || !verify_password($senha, $usuario['senha_hash'])) {
        json_erro(401, 'E-mail ou senha inválidos');
    }

    if ($usuario['totp_ativado']) {
        $codigo = $dados['codigo_totp'] ?? null;
        if (!$codigo) {
            json_saida(['requer_totp' => true]);
        }
        if (!totp_verificar($usuario['totp_secret'], $codigo)) {
            json_erro(401, 'Código de verificação inválido');
        }
    }

    json_saida([
        'access_token' => criar_token($usuario['id']),
        'refresh_token' => criar_refresh_token($usuario['id']),
        'usuario' => usuario_para_json($usuario),
    ]);
});

rota('GET', '/api/auth/me', function () {
    json_saida(usuario_para_json(usuario_atual()));
});

rota('POST', '/api/auth/refresh', function () {
    limitar_por_ip('auth-refresh', 30, 600);
    $dados = corpo_json();
    $token = campo_obrigatorio($dados, 'refresh_token');
    $resultado = rotacionar_refresh_token($token);
    if (!$resultado) {
        json_erro(401, 'Sessão expirada, faça login novamente');
    }
    [$usuario, $novoRefresh] = $resultado;
    json_saida([
        'access_token' => criar_token($usuario['id']),
        'refresh_token' => $novoRefresh,
        'usuario' => usuario_para_json($usuario),
    ]);
});

rota('POST', '/api/auth/logout', function () {
    $dados = corpo_json();
    $token = campo_obrigatorio($dados, 'refresh_token');
    revogar_refresh_token($token);
    http_response_code(204);
    exit;
});

rota('GET', '/api/auth/recuperar-senha/configurado', function () {
    json_saida(['configurado' => email_configurado()]);
});

rota('POST', '/api/auth/recuperar-senha', function () {
    limitar_por_ip('recuperar-senha', 5, 600);
    $dados = corpo_json();
    $email = campo_obrigatorio($dados, 'email');
    $mensagemPadrao = ['mensagem' => 'Se este e-mail estiver cadastrado, você vai receber um link para redefinir sua senha.'];

    if (!email_configurado()) {
        json_erro(503, 'Recuperação de senha por e-mail não está disponível neste servidor');
    }

    $usuario = buscar_usuario_por_email($email);
    if (!$usuario) {
        json_saida($mensagemPadrao);
    }

    $token = criar_token_recuperacao_senha($usuario['id']);
    $link = site_url() . "/redefinir-senha.html?token={$token}";
    $corpo = "Olá, {$usuario['nome']}!\n\n"
        . "Recebemos um pedido para redefinir a senha da sua conta no LogJobs Brasil.\n\n"
        . "Clique no link abaixo para escolher uma nova senha (válido por 1 hora):\n{$link}\n\n"
        . "Se você não pediu isso, pode ignorar este e-mail — sua senha continua a mesma.";
    try {
        enviar_email($usuario['email'], 'Redefinir sua senha — LogJobs Brasil', $corpo);
    } catch (ErroEnvioEmail $e) {
        json_erro(502, 'Não foi possível enviar o e-mail agora. Tente novamente em instantes.');
    }
    json_saida($mensagemPadrao);
});

rota('POST', '/api/auth/redefinir-senha', function () {
    limitar_por_ip('redefinir-senha', 10, 600);
    $dados = corpo_json();
    $token = campo_obrigatorio($dados, 'token');
    $novaSenha = campo_obrigatorio($dados, 'nova_senha');
    if (strlen($novaSenha) < 6) {
        json_erro(400, 'A senha precisa ter pelo menos 6 caracteres');
    }
    $usuario = validar_e_consumir_token_recuperacao($token);
    if (!$usuario) {
        json_erro(401, 'Link inválido ou expirado. Peça uma nova recuperação de senha.');
    }
    db()->prepare('UPDATE usuarios SET senha_hash = ? WHERE id = ?')->execute([hash_password($novaSenha), $usuario['id']]);
    revogar_todos_refresh_tokens($usuario['id']);
    json_saida(['mensagem' => 'Senha redefinida com sucesso. Faça login com sua nova senha.']);
});

rota('GET', '/api/auth/google/configurado', function () {
    json_saida(['configurado' => google_configurado()]);
});

rota('GET', '/api/auth/google/login', function () {
    if (!google_configurado()) {
        json_erro(503, 'Login com Google não está configurado neste servidor');
    }
    limitar_por_ip('auth-google', 20, 600);
    $state = encode_jwt(['exp' => time() + 600, 'nonce' => bin2hex(random_bytes(8))], secret_key());
    header('Location: ' . google_url_autorizacao($state));
    exit;
});

rota('GET', '/api/auth/google/callback', function () {
    $falha = function (string $motivo) {
        header('Location: /oauth-callback.html?erro=' . rawurlencode($motivo));
        exit;
    };

    if (!empty($_GET['error'])) {
        $falha('Login com Google cancelado ou negado');
    }
    $code = $_GET['code'] ?? null;
    $state = $_GET['state'] ?? null;
    if (!$code || !$state || !decode_jwt($state, secret_key())) {
        $falha('Requisição inválida ou expirada');
    }

    try {
        $perfil = google_trocar_codigo_por_perfil($code);
    } catch (ErroTrocaGoogle $e) {
        $falha('Não foi possível confirmar sua conta Google');
        return;
    }

    $email = $perfil['email'] ?? null;
    if (!$email) {
        $falha('O Google não retornou um e-mail para esta conta');
    }

    $usuario = buscar_usuario_por_email($email);
    if (!$usuario) {
        db()->prepare('INSERT INTO usuarios (nome, email, senha_hash, tipo, oauth_provider, oauth_id) VALUES (?, ?, ?, ?, ?, ?)')
            ->execute([
                $perfil['name'] ?? explode('@', $email)[0], $email, hash_password(bin2hex(random_bytes(32))),
                'candidato', 'google', $perfil['sub'] ?? null,
            ]);
        $usuario = buscar_usuario_por_id((int) db()->lastInsertId());
    } elseif (!$usuario['oauth_provider']) {
        db()->prepare('UPDATE usuarios SET oauth_provider = ?, oauth_id = ? WHERE id = ?')
            ->execute(['google', $perfil['sub'] ?? null, $usuario['id']]);
    }

    $token = criar_token($usuario['id']);
    $refreshToken = criar_refresh_token($usuario['id']);
    header("Location: /oauth-callback.html#token={$token}&refresh_token={$refreshToken}");
    exit;
});

rota('POST', '/api/auth/2fa/iniciar', function () {
    $usuario = usuario_atual();
    if ($usuario['totp_ativado']) {
        json_erro(400, 'Verificação em duas etapas já está ativada');
    }
    $segredo = totp_gerar_segredo();
    db()->prepare('UPDATE usuarios SET totp_secret = ? WHERE id = ?')->execute([$segredo, $usuario['id']]);
    json_saida(['segredo' => $segredo, 'otpauth_uri' => totp_uri_otpauth($usuario['email'], $segredo)]);
});

rota('POST', '/api/auth/2fa/confirmar', function () {
    $usuario = usuario_atual();
    $dados = corpo_json();
    $codigo = campo_obrigatorio($dados, 'codigo');
    if (!$usuario['totp_secret']) {
        json_erro(400, 'Nenhuma ativação de verificação em duas etapas pendente');
    }
    if (!totp_verificar($usuario['totp_secret'], $codigo)) {
        json_erro(400, 'Código inválido');
    }
    db()->prepare('UPDATE usuarios SET totp_ativado = 1 WHERE id = ?')->execute([$usuario['id']]);
    json_saida(['mensagem' => 'Verificação em duas etapas ativada']);
});

rota('POST', '/api/auth/2fa/desativar', function () {
    $usuario = usuario_atual();
    $dados = corpo_json();
    $senha = campo_obrigatorio($dados, 'senha');
    if (!verify_password($senha, $usuario['senha_hash'])) {
        json_erro(401, 'Senha incorreta');
    }
    db()->prepare('UPDATE usuarios SET totp_ativado = 0, totp_secret = NULL WHERE id = ?')->execute([$usuario['id']]);
    json_saida(['mensagem' => 'Verificação em duas etapas desativada']);
});

const CAMPOS_PERFIL_TEXTO = [
    'nome', 'telefone', 'cidade', 'resumo', 'habilidades', 'disponibilidade', 'possui_cnh',
    'veiculo_proprio', 'portfolio_url', 'linkedin_url', 'github_url', 'logo_url', 'site_url', 'instagram_url',
];
const CAMPOS_PERFIL_LISTA = ['experiencias', 'formacoes', 'cursos', 'certificados', 'idiomas'];

rota('PATCH', '/api/auth/me', function () {
    $usuario = usuario_atual();
    $dados = corpo_json();
    $sets = [];
    $valores = [];

    foreach (CAMPOS_PERFIL_TEXTO as $campo) {
        if (array_key_exists($campo, $dados)) {
            $valor = is_string($dados[$campo]) ? trim($dados[$campo]) : $dados[$campo];
            if ($campo === 'nome' && $valor === '') {
                json_erro(400, 'Nome não pode ficar vazio');
            }
            $sets[] = "{$campo} = ?";
            $valores[] = $valor !== '' ? $valor : null;
        }
    }
    if (array_key_exists('pretensao_salarial', $dados)) {
        $sets[] = 'pretensao_salarial = ?';
        $valores[] = $dados['pretensao_salarial'];
    }
    foreach (CAMPOS_PERFIL_LISTA as $campo) {
        if (array_key_exists($campo, $dados)) {
            $sets[] = "{$campo}_json = ?";
            $valores[] = json_encode($dados[$campo], JSON_UNESCAPED_UNICODE);
        }
    }

    if ($sets) {
        $valores[] = $usuario['id'];
        db()->prepare('UPDATE usuarios SET ' . implode(', ', $sets) . ' WHERE id = ?')->execute($valores);
    }

    json_saida(usuario_para_json(buscar_usuario_por_id($usuario['id'])));
});

rota('GET', '/api/auth/meus-dados', function () {
    $usuario = usuario_atual();
    $pdo = db();

    $stmt = $pdo->prepare('SELECT vaga_id, criado_em FROM favoritos WHERE usuario_id = ?');
    $stmt->execute([$usuario['id']]);
    $favoritos = $stmt->fetchAll();

    $stmt = $pdo->prepare('SELECT cargo, categoria, cidade, estado, criado_em FROM alertas WHERE usuario_id = ?');
    $stmt->execute([$usuario['id']]);
    $alertas = $stmt->fetchAll();

    $stmt = $pdo->prepare('SELECT vaga_id, criada_em FROM candidaturas WHERE email = ?');
    $stmt->execute([$usuario['email']]);
    $candidaturas = $stmt->fetchAll();

    $dados = [
        'perfil' => usuario_para_json($usuario),
        'favoritos' => array_map(fn ($f) => ['vaga_id' => (int) $f['vaga_id'], 'criado_em' => $f['criado_em'] ? date('c', strtotime($f['criado_em'])) : null], $favoritos),
        'alertas' => array_map(fn ($a) => [
            'cargo' => $a['cargo'], 'categoria' => $a['categoria'], 'cidade' => $a['cidade'], 'estado' => $a['estado'],
            'criado_em' => $a['criado_em'] ? date('c', strtotime($a['criado_em'])) : null,
        ], $alertas),
        'candidaturas' => array_map(fn ($c) => ['vaga_id' => (int) $c['vaga_id'], 'criada_em' => $c['criada_em'] ? date('c', strtotime($c['criada_em'])) : null], $candidaturas),
    ];

    if ($usuario['tipo'] === 'empresa') {
        $stmt = $pdo->prepare('SELECT id, cargo, cidade, estado, criada_em FROM vagas WHERE usuario_id = ?');
        $stmt->execute([$usuario['id']]);
        $dados['vagas_publicadas'] = array_map(fn ($v) => [
            'id' => (int) $v['id'], 'cargo' => $v['cargo'], 'cidade' => $v['cidade'], 'estado' => $v['estado'],
            'criada_em' => $v['criada_em'] ? date('c', strtotime($v['criada_em'])) : null,
        ], $stmt->fetchAll());
    }

    json_saida($dados);
});

rota('DELETE', '/api/auth/me', function () {
    $usuario = usuario_atual();
    $dados = corpo_json();
    $senha = campo_obrigatorio($dados, 'senha');
    if ($usuario['oauth_provider'] !== 'google' && !verify_password($senha, $usuario['senha_hash'])) {
        json_erro(401, 'Senha incorreta');
    }
    excluir_usuario_em_cascata($usuario['id']);
    revogar_todos_refresh_tokens($usuario['id']);
    http_response_code(204);
    exit;
});
