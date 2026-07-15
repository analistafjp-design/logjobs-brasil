<?php
declare(strict_types=1);

// Porta 1:1 de backend/analise_perfil.py.

function lista_json(?string $texto): array
{
    if (!$texto) {
        return [];
    }
    $dados = json_decode($texto, true);
    return is_array($dados) ? $dados : [];
}

function contar_palavras(?string $texto): int
{
    return $texto ? count(preg_split('/\s+/', trim($texto))) : 0;
}

function analisar_perfil(array $usuario): array
{
    $experiencias = lista_json($usuario['experiencias_json'] ?? null);
    $formacoes = lista_json($usuario['formacoes_json'] ?? null);
    $idiomas = lista_json($usuario['idiomas_json'] ?? null);
    $cursos = lista_json($usuario['cursos_json'] ?? null);
    $certificados = lista_json($usuario['certificados_json'] ?? null);

    $pontosFortes = [];
    $sugestoes = [];

    $resumo = $usuario['resumo'] ?? null;
    if ($resumo && contar_palavras($resumo) >= 30) {
        $pontosFortes[] = 'Mini-currículo bem detalhado';
    } elseif ($resumo) {
        $sugestoes[] = 'Seu mini-currículo está curto — detalhe um pouco mais sua experiência e objetivos.';
    } else {
        $sugestoes[] = 'Você ainda não escreveu um mini-currículo. Ele é o que mais pesa nas recomendações de vagas.';
    }

    $habilidades = $usuario['habilidades'] ?? null;
    if ($habilidades) {
        $totalHabilidades = count(array_filter(explode(',', $habilidades), fn ($h) => trim($h) !== ''));
        if ($totalHabilidades >= 3) {
            $pontosFortes[] = "{$totalHabilidades} habilidades cadastradas";
        } else {
            $sugestoes[] = 'Cadastre mais habilidades separadas por vírgula (ex.: "Direção defensiva, CNH E").';
        }
    } else {
        $sugestoes[] = 'Nenhuma habilidade cadastrada ainda — isso ajuda muito no motor de recomendação de vagas.';
    }

    if ($experiencias) {
        $pontosFortes[] = count($experiencias) . ' experiência(s) profissional(is) cadastrada(s)';
        $semDescricao = count(array_filter($experiencias, fn ($e) => trim($e['descricao'] ?? '') === ''));
        if ($semDescricao) {
            $sugestoes[] = "{$semDescricao} experiência(s) sem descrição — descreva suas responsabilidades e conquistas.";
        }
    } else {
        $sugestoes[] = 'Cadastre pelo menos uma experiência profissional no seu perfil.';
    }

    if ($formacoes) {
        $pontosFortes[] = count($formacoes) . ' formação/formações cadastrada(s)';
    } else {
        $sugestoes[] = 'Cadastre sua formação acadêmica ou técnica, mesmo que incompleta.';
    }

    $possuiCnh = $usuario['possui_cnh'] ?? null;
    if ($possuiCnh) {
        $pontosFortes[] = "CNH categoria {$possuiCnh}";
    } else {
        $sugestoes[] = 'Informe sua categoria de CNH, se tiver — é um dos filtros mais usados em vagas de logística.';
    }

    if (!$idiomas) {
        $sugestoes[] = 'Cadastre idiomas, mesmo que seja só "Português — Nativo".';
    }
    if (!$cursos && !$certificados) {
        $sugestoes[] = 'Cursos e certificados (mesmo online e gratuitos) aumentam sua compatibilidade com vagas técnicas.';
    }

    if (!empty($usuario['linkedin_url']) || !empty($usuario['portfolio_url']) || !empty($usuario['github_url'])) {
        $pontosFortes[] = 'Tem link de LinkedIn/portfólio cadastrado';
    } else {
        $sugestoes[] = 'Adicione seu LinkedIn ou portfólio, se tiver — passa mais confiança para a empresa.';
    }

    $disponibilidade = $usuario['disponibilidade'] ?? null;
    if ($disponibilidade) {
        $pontosFortes[] = "Disponibilidade informada: {$disponibilidade}";
    } else {
        $sugestoes[] = 'Informe sua disponibilidade para começar (Imediata, 15 dias, 30 dias...).';
    }

    $camposPreenchidos = [
        !empty($usuario['telefone']), !empty($usuario['cidade']), !empty($resumo), !empty($habilidades),
        !empty($usuario['pretensao_salarial']), !empty($disponibilidade), (bool) $experiencias, (bool) $formacoes,
        (bool) $idiomas, !empty($usuario['linkedin_url']) || !empty($usuario['portfolio_url']) || !empty($usuario['github_url']),
    ];
    $completude = (int) round(100 * count(array_filter($camposPreenchidos)) / count($camposPreenchidos));

    return ['completude' => $completude, 'pontos_fortes' => $pontosFortes, 'sugestoes' => $sugestoes];
}

function gerar_curriculo_texto(array $usuario): string
{
    $experiencias = lista_json($usuario['experiencias_json'] ?? null);
    $formacoes = lista_json($usuario['formacoes_json'] ?? null);
    $cursos = lista_json($usuario['cursos_json'] ?? null);
    $certificados = lista_json($usuario['certificados_json'] ?? null);
    $idiomas = lista_json($usuario['idiomas_json'] ?? null);

    $nome = $usuario['nome'];
    $linhas = [mb_strtoupper($nome), str_repeat('=', mb_strlen($nome))];

    $contato = array_filter([$usuario['email'] ?? null, $usuario['telefone'] ?? null, $usuario['cidade'] ?? null]);
    if ($contato) {
        $linhas[] = implode(' | ', $contato);
    }
    $links = array_filter([$usuario['linkedin_url'] ?? null, $usuario['github_url'] ?? null, $usuario['portfolio_url'] ?? null]);
    if ($links) {
        $linhas[] = implode(' | ', $links);
    }
    $linhas[] = '';

    if (!empty($usuario['resumo'])) {
        $linhas[] = 'RESUMO PROFISSIONAL';
        $linhas[] = $usuario['resumo'];
        $linhas[] = '';
    }

    $dadosRapidos = [];
    if (!empty($usuario['possui_cnh'])) {
        $dadosRapidos[] = "CNH: {$usuario['possui_cnh']}";
    }
    if (($usuario['veiculo_proprio'] ?? null) === 'sim') {
        $dadosRapidos[] = 'Possui veículo próprio';
    }
    if (!empty($usuario['disponibilidade'])) {
        $dadosRapidos[] = "Disponibilidade: {$usuario['disponibilidade']}";
    }
    if (!empty($usuario['pretensao_salarial'])) {
        $dadosRapidos[] = 'Pretensão salarial: R$ ' . number_format((float) $usuario['pretensao_salarial'], 2, ',', '.');
    }
    if ($dadosRapidos) {
        $linhas[] = 'DADOS COMPLEMENTARES';
        $linhas = array_merge($linhas, $dadosRapidos);
        $linhas[] = '';
    }

    if (!empty($usuario['habilidades'])) {
        $linhas[] = 'HABILIDADES';
        $linhas[] = $usuario['habilidades'];
        $linhas[] = '';
    }

    if ($experiencias) {
        $linhas[] = 'EXPERIÊNCIA PROFISSIONAL';
        foreach ($experiencias as $e) {
            $periodo = ($e['inicio'] ?? '?') . ' – ' . ($e['fim'] ?? 'atual');
            $linhas[] = '- ' . ($e['cargo'] ?? '') . ' | ' . ($e['empresa'] ?? '') . " ({$periodo})";
            if (!empty($e['descricao'])) {
                $linhas[] = '  ' . $e['descricao'];
            }
        }
        $linhas[] = '';
    }

    if ($formacoes) {
        $linhas[] = 'FORMAÇÃO ACADÊMICA';
        foreach ($formacoes as $f) {
            $status = !empty($f['status']) ? " — {$f['status']}" : '';
            $linhas[] = '- ' . ($f['curso'] ?? '') . ' | ' . ($f['instituicao'] ?? '') . $status;
        }
        $linhas[] = '';
    }

    if ($cursos) {
        $linhas[] = 'CURSOS';
        foreach ($cursos as $c) {
            $ano = !empty($c['ano']) ? " ({$c['ano']})" : '';
            $linhas[] = '- ' . ($c['nome'] ?? '') . $ano;
        }
        $linhas[] = '';
    }

    if ($certificados) {
        $linhas[] = 'CERTIFICADOS';
        foreach ($certificados as $c) {
            $ano = !empty($c['ano']) ? " ({$c['ano']})" : '';
            $linhas[] = '- ' . ($c['nome'] ?? '') . $ano;
        }
        $linhas[] = '';
    }

    if ($idiomas) {
        $linhas[] = 'IDIOMAS';
        foreach ($idiomas as $i) {
            $nivel = !empty($i['nivel']) ? " — {$i['nivel']}" : '';
            $linhas[] = '- ' . ($i['idioma'] ?? '') . $nivel;
        }
        $linhas[] = '';
    }

    return trim(implode("\n", $linhas)) . "\n";
}
