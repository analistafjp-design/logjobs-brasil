<?php
declare(strict_types=1);

// Rode este arquivo UMA VEZ pelo navegador (https://seudominio.com.br/backend-php/setup.php)
// logo depois de subir os arquivos e configurar config.local.php — ele cria as tabelas e
// popula vagas/artigos de exemplo. Depois de rodar com sucesso, APAGUE este arquivo do
// servidor (ou pelo menos renomeie), senão qualquer pessoa pode re-executá-lo.

require_once __DIR__ . '/lib/config.php';
require_once __DIR__ . '/lib/db.php';

header('Content-Type: text/plain; charset=utf-8');

echo "== LogJobs Brasil — instalação do banco MySQL ==\n\n";

$pdo = db();

echo "1. Criando tabelas (schema.sql)...\n";
$sql = file_get_contents(__DIR__ . '/schema.sql');
foreach (array_filter(array_map('trim', explode(';', $sql))) as $comando) {
    if ($comando === '' || str_starts_with($comando, '--') || str_starts_with($comando, 'SET NAMES')) {
        continue;
    }
    $pdo->exec($comando);
}
echo "   OK.\n\n";

echo "2. Populando vagas de exemplo (se o banco estiver vazio)...\n";
$totalVagas = (int) $pdo->query('SELECT COUNT(id) AS t FROM vagas')->fetch()['t'];
if ($totalVagas === 0) {
    $vagas = json_decode(file_get_contents(__DIR__ . '/seed/vagas_exemplo.json'), true);
    $stmt = $pdo->prepare(
        'INSERT INTO vagas (cargo, empresa, cidade, estado, salario, modalidade, veiculo, categoria, descricao, beneficios, requisitos, fonte)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
    );
    $inseridas = 0;
    foreach ($vagas as $v) {
        try {
            $stmt->execute([
                $v['cargo'], $v['empresa'], $v['cidade'], $v['estado'], $v['salario'] ?? null,
                $v['modalidade'] ?? null, $v['veiculo'] ?? null, $v['categoria'],
                $v['descricao'] ?? null, $v['beneficios'] ?? null, $v['requisitos'] ?? null, 'exemplo',
            ]);
            $inseridas++;
        } catch (PDOException $e) {
            if ($e->getCode() !== '23000') {
                throw $e;
            }
        }
    }
    echo "   {$inseridas} vagas de exemplo inseridas.\n\n";
} else {
    echo "   Banco já tem {$totalVagas} vaga(s) — pulando (não sobrescreve dados existentes).\n\n";
}

echo "3. Populando artigos do blog (se estiver vazio)...\n";
$totalArtigos = (int) $pdo->query('SELECT COUNT(id) AS t FROM artigos')->fetch()['t'];
if ($totalArtigos === 0) {
    $artigos = json_decode(file_get_contents(__DIR__ . '/seed/artigos_exemplo.json'), true);
    $stmt = $pdo->prepare('INSERT INTO artigos (slug, titulo, resumo, conteudo, categoria) VALUES (?, ?, ?, ?, ?)');
    $inseridos = 0;
    foreach ($artigos as $a) {
        try {
            $stmt->execute([$a['slug'], $a['titulo'], $a['resumo'], $a['conteudo'], $a['categoria']]);
            $inseridos++;
        } catch (PDOException $e) {
            if ($e->getCode() !== '23000') {
                throw $e;
            }
        }
    }
    echo "   {$inseridos} artigo(s) inseridos.\n\n";
} else {
    echo "   Banco já tem {$totalArtigos} artigo(s) — pulando.\n\n";
}

echo "== Instalação concluída ==\n";
echo "IMPORTANTE: apague ou renomeie este arquivo (setup.php) agora, antes de divulgar o site.\n";
