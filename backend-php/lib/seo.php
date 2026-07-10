<?php
declare(strict_types=1);

// Porta 1:1 de backend/seo.py.

function site_url(): string
{
    return rtrim(config('SITE_URL', 'https://logjobsbrasil.com.br'), '/');
}

const SITE_NOME = 'LogJobs Brasil';

function esc(?string $valor): string
{
    return $valor !== null ? htmlspecialchars($valor, ENT_QUOTES, 'UTF-8') : '';
}

function empregatipo(?string $modalidade): string
{
    return $modalidade === 'Autônomo' ? 'CONTRACTOR' : 'FULL_TIME';
}

function job_posting_jsonld(array $vaga): string
{
    $postadoEm = $vaga['criada_em'] ?? gmdate('c');
    $validoAte = gmdate('c', strtotime($postadoEm) + 45 * 86400);

    $dados = [
        '@context' => 'https://schema.org/',
        '@type' => 'JobPosting',
        'title' => $vaga['cargo'],
        'description' => $vaga['descricao'] ?: "Vaga de {$vaga['cargo']} na empresa {$vaga['empresa']}, em {$vaga['cidade']}.",
        'datePosted' => date('c', strtotime($postadoEm)),
        'validThrough' => $validoAte,
        'employmentType' => empregatipo($vaga['modalidade'] ?? null),
        'hiringOrganization' => ['@type' => 'Organization', 'name' => $vaga['empresa']],
        'jobLocation' => [
            '@type' => 'Place',
            'address' => [
                '@type' => 'PostalAddress',
                'addressLocality' => $vaga['cidade'],
                'addressRegion' => $vaga['estado'],
                'addressCountry' => 'BR',
            ],
        ],
        'identifier' => ['@type' => 'PropertyValue', 'name' => SITE_NOME, 'value' => (string) $vaga['id']],
    ];

    if (!empty($vaga['salario'])) {
        $dados['baseSalary'] = [
            '@type' => 'MonetaryAmount',
            'currency' => 'BRL',
            'value' => ['@type' => 'QuantitativeValue', 'value' => $vaga['salario'], 'unitText' => 'MONTH'],
        ];
    }

    return json_encode($dados, JSON_UNESCAPED_UNICODE);
}

function pagina_vaga_html(array $vaga): string
{
    $siteUrl = site_url();
    $urlVaga = "{$siteUrl}/vagas/{$vaga['id']}";
    $titulo = "{$vaga['cargo']} — {$vaga['empresa']} — " . SITE_NOME;
    $descricaoMeta = esc(mb_substr($vaga['descricao'] ?: "Vaga de {$vaga['cargo']} na {$vaga['empresa']}, em {$vaga['cidade']}, {$vaga['estado']}.", 0, 200));

    if (!empty($vaga['link'])) {
        $acaoHtml = '<a class="btn-candidatar" href="' . esc($vaga['link']) . '" target="_blank" rel="noopener noreferrer">Ver vaga original ↗</a>';
    } else {
        $acaoHtml = '<button class="btn-candidatar" onclick="abrirCandidaturaVagaAtual()">Candidatar-se</button>';
    }

    $salarioHtml = !empty($vaga['salario'])
        ? 'R$ ' . number_format((float) $vaga['salario'], 0, ',', '.') . '/mês'
        : 'A combinar';

    $cargoJson = json_encode($vaga['cargo'], JSON_UNESCAPED_UNICODE);
    $empresaJson = json_encode($vaga['empresa'], JSON_UNESCAPED_UNICODE);
    $cidadeJson = json_encode($vaga['cidade'], JSON_UNESCAPED_UNICODE);
    $estadoJson = json_encode($vaga['estado'], JSON_UNESCAPED_UNICODE);
    $jsonLd = job_posting_jsonld($vaga);

    $cargoEsc = esc($vaga['cargo']);
    $empresaEsc = esc($vaga['empresa']);
    $cidadeEsc = esc($vaga['cidade']);
    $estadoEsc = esc($vaga['estado']);
    $categoriaEsc = esc($vaga['categoria']);
    $descricaoEsc = esc($vaga['descricao'] ?? '');
    $tituloEsc = esc($titulo);

    return <<<HTML
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{$tituloEsc}</title>
<meta name="description" content="{$descricaoMeta}">
<link rel="canonical" href="{$urlVaga}">
<link rel="stylesheet" href="/css/style.css">
<script>
  (function () {
    var tema = localStorage.getItem('logjobs-tema');
    if (tema === 'dark' || tema === 'light') {
      document.documentElement.setAttribute('data-theme', tema);
    }
  })();
</script>
<meta property="og:type" content="website">
<meta property="og:title" content="{$cargoEsc} — {$empresaEsc}">
<meta property="og:description" content="{$descricaoMeta}">
<meta property="og:url" content="{$urlVaga}">
<meta property="og:site_name" content="LogJobs Brasil">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="{$cargoEsc} — {$empresaEsc}">
<meta name="twitter:description" content="{$descricaoMeta}">
<script type="application/ld+json">{$jsonLd}</script>
</head>
<body>
<header class="navbar">
  <div class="navbar-inner">
    <a href="/" class="logo">🚚 <span>LogJobs Brasil</span></a>
  </div>
</header>
<main>
  <section class="vagas" style="padding-top:48px">
    <a href="/#vagas" class="ver-todas">← Voltar para todas as vagas</a>
    <article class="vaga" style="margin-top:24px;max-width:640px">
      <div class="vaga-topo">
        <h1 style="font-size:22px;font-weight:700">{$cargoEsc}</h1>
        <span class="tag">{$categoriaEsc}</span>
      </div>
      <p class="vaga-info">{$empresaEsc} • {$cidadeEsc}, {$estadoEsc}</p>
      <p class="vaga-info">{$descricaoEsc}</p>
      <div class="vaga-rodape">
        <span class="salario">{$salarioHtml}</span>
        {$acaoHtml}
      </div>
    </article>
  </section>
</main>
<div class="modal-overlay" id="modalOverlay" hidden>
  <div class="modal" role="dialog" aria-modal="true">
    <button class="modal-fechar" id="modalFechar" aria-label="Fechar">&times;</button>
    <div id="modalConteudo"></div>
  </div>
</div>
<div class="toast" id="toast" hidden></div>
<script src="/js/app.js"></script>
<script>
  function abrirCandidaturaVagaAtual() {
    window.__vagaAtual = {
      id: {$vaga['id']},
      cargo: {$cargoJson},
      empresa: {$empresaJson},
      cidade: {$cidadeJson},
      estado: {$estadoJson},
    };
    if (typeof abrirModalCandidatura === 'function') {
      abrirModalCandidatura(window.__vagaAtual);
    }
  }
</script>
</body>
</html>
HTML;
}

function pagina_sitemap_xml(array $vagas, array $artigos = []): string
{
    $siteUrl = site_url();
    $urls = [
        "<url><loc>{$siteUrl}/</loc><changefreq>hourly</changefreq><priority>1.0</priority></url>",
        "<url><loc>{$siteUrl}/blog.html</loc><changefreq>weekly</changefreq><priority>0.6</priority></url>",
    ];
    foreach ($vagas as $vaga) {
        $data = substr($vaga['criada_em'] ?? gmdate('c'), 0, 10);
        $urls[] = "<url><loc>{$siteUrl}/vagas/{$vaga['id']}</loc><lastmod>{$data}</lastmod><changefreq>daily</changefreq><priority>0.8</priority></url>";
    }
    foreach ($artigos as $artigo) {
        $data = substr($artigo['publicado_em'] ?? gmdate('c'), 0, 10);
        $urls[] = "<url><loc>{$siteUrl}/artigo.html?slug={$artigo['slug']}</loc><lastmod>{$data}</lastmod><changefreq>monthly</changefreq><priority>0.5</priority></url>";
    }
    $corpo = implode('', $urls);
    return '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' . $corpo . '</urlset>';
}

function robots_txt(): string
{
    $siteUrl = site_url();
    return "User-agent: *\nAllow: /\n\nSitemap: {$siteUrl}/sitemap.xml\n";
}

function pagina_404_html(): string
{
    return <<<HTML
<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Página não encontrada — LogJobs Brasil</title>
<meta name="robots" content="noindex">
<link rel="stylesheet" href="/css/style.css">
</head>
<body>
<header class="navbar">
  <div class="navbar-inner">
    <a href="/" class="logo">🚚 <span>LogJobs Brasil</span></a>
  </div>
</header>
<main>
  <section class="hero" style="padding:96px 24px">
    <div class="hero-inner">
      <h1 style="font-size:clamp(60px,10vw,96px);margin-bottom:8px">404</h1>
      <p style="margin-bottom:40px">Essa página não existe ou a vaga já pode ter sido removida.</p>
      <a href="/" style="display:inline-block;padding:14px 28px;font-size:15px;font-weight:600;background:#fff;color:var(--azul);border-radius:10px">← Voltar para a home</a>
    </div>
  </section>
</main>
</body>
</html>
HTML;
}
