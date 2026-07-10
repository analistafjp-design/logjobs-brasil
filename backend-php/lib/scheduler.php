<?php
declare(strict_types=1);

// Porta de backend/scheduler.py. Sem BackgroundScheduler (não existe processo de
// longa duração em hospedagem compartilhada): quem "agenda" a execução periódica é
// o cron job do hPanel da Hostinger, chamando cron/atualizar.php a cada 20 min —
// ver MIGRACAO_HOSTINGER.md para o passo a passo de configuração.

const DIAS_EXPIRACAO_VAGA = 60;
const CHAVE_CORRECAO_GEOGRAFICA = 'correcao_geografica_pais_v1';

function aplicar_correcao_geografica_uma_vez(): void
{
    $pdo = db();
    $stmt = $pdo->prepare('SELECT id FROM marcadores WHERE chave = ?');
    $stmt->execute([CHAVE_CORRECAO_GEOGRAFICA]);
    if ($stmt->fetch()) {
        return;
    }
    $stmt = $pdo->prepare('SELECT id FROM vagas WHERE fonte = ?');
    $stmt->execute(['jooble']);
    $ids = array_column($stmt->fetchAll(), 'id');
    if ($ids) {
        $in = implode(',', array_fill(0, count($ids), '?'));
        $pdo->prepare("DELETE FROM candidaturas WHERE vaga_id IN ({$in})")->execute($ids);
        $pdo->prepare('DELETE FROM vagas WHERE fonte = ?')->execute(['jooble']);
    }
    $pdo->prepare('INSERT INTO marcadores (chave) VALUES (?)')->execute([CHAVE_CORRECAO_GEOGRAFICA]);
}

function reclassificar_vagas_sem_categoria(): void
{
    $pdo = db();
    $stmt = $pdo->prepare('SELECT * FROM vagas WHERE categoria IN (?, ?)');
    $stmt->execute(['Importado (Jooble)', 'Logística']);
    foreach ($stmt->fetchAll() as $vaga) {
        $novaCategoria = jooble_classificar_categoria($vaga['cargo']);
        if ($novaCategoria !== $vaga['categoria']) {
            $pdo->prepare('UPDATE vagas SET categoria = ? WHERE id = ?')->execute([$novaCategoria, $vaga['id']]);
        }
    }
}

function remover_vagas_expiradas(): void
{
    $pdo = db();
    $limite = gmdate('Y-m-d H:i:s', time() - DIAS_EXPIRACAO_VAGA * 86400);
    $stmt = $pdo->prepare('SELECT id FROM vagas WHERE fonte = ? AND criada_em < ?');
    $stmt->execute(['jooble', $limite]);
    $ids = array_column($stmt->fetchAll(), 'id');
    if ($ids) {
        $in = implode(',', array_fill(0, count($ids), '?'));
        $pdo->prepare("DELETE FROM candidaturas WHERE vaga_id IN ({$in})")->execute($ids);
        $pdo->prepare("DELETE FROM vagas WHERE id IN ({$in})")->execute($ids);
    }
}

function remover_vagas_exemplo_se_ha_reais(): void
{
    $pdo = db();
    $stmt = $pdo->prepare('SELECT id FROM vagas WHERE fonte = ? LIMIT 1');
    $stmt->execute(['jooble']);
    if ($stmt->fetch()) {
        $pdo->prepare('DELETE FROM vagas WHERE fonte = ?')->execute(['exemplo']);
    }
}

function atualizar_vagas_periodicamente(): void
{
    $pdo = db();
    $vagasNovas = 0;

    try {
        $indiceCategoria = (int) $pdo->query('SELECT COUNT(id) AS t FROM atualizacoes')->fetch()['t'];
        $vagasEncontradas = jooble_buscar_vagas_proxima_categoria($indiceCategoria);

        $stmt = $pdo->query('SELECT cargo, empresa, cidade FROM vagas');
        $chavesExistentes = [];
        foreach ($stmt->fetchAll() as $v) {
            $chavesExistentes[$v['cargo'] . '|' . $v['empresa'] . '|' . $v['cidade']] = true;
        }

        foreach ($vagasEncontradas as $dados) {
            $chave = $dados['cargo'] . '|' . $dados['empresa'] . '|' . $dados['cidade'];
            if (isset($chavesExistentes[$chave])) {
                continue;
            }
            $chavesExistentes[$chave] = true;
            try {
                inserir_vaga_bruta($dados);
                $vagasNovas++;
            } catch (PDOException $e) {
                if ($e->getCode() !== '23000') {
                    throw $e;
                }
            }
        }

        $totalVagas = (int) $pdo->query('SELECT COUNT(id) AS t FROM vagas')->fetch()['t'];
        $pdo->prepare('INSERT INTO atualizacoes (jooble_configurado, vagas_novas, vagas_totais) VALUES (?, ?, ?)')
            ->execute([jooble_api_key() !== null ? 1 : 0, $vagasNovas, $totalVagas]);
    } catch (Throwable $e) {
        error_log('Falha ao atualizar vagas periodicamente: ' . $e->getMessage());
    }

    remover_vagas_exemplo_se_ha_reais();
    remover_vagas_expiradas();
}

function inserir_vaga_bruta(array $dados): void
{
    $colunas = ['cargo', 'empresa', 'cidade', 'estado', 'salario', 'modalidade', 'veiculo', 'categoria', 'descricao', 'beneficios', 'requisitos', 'link', 'fonte'];
    $valores = [];
    foreach ($colunas as $c) {
        $valores[] = $dados[$c] ?? null;
    }
    $placeholders = implode(', ', array_fill(0, count($colunas), '?'));
    db()->prepare('INSERT INTO vagas (' . implode(', ', $colunas) . ") VALUES ({$placeholders})")->execute($valores);
}
