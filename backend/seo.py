import html
import json
import os
from datetime import datetime, timedelta

# SITE_URL pode ser definida manualmente; caso contrário, usa a URL que o
# próprio Render injeta automaticamente (RENDER_EXTERNAL_URL) em produção.
SITE_URL = os.getenv("SITE_URL") or os.getenv("RENDER_EXTERNAL_URL") or "https://logjobs-brasil.onrender.com"
SITE_URL = SITE_URL.rstrip("/")
SITE_NOME = "LogJobs Brasil"


def _esc(valor):
    return html.escape(str(valor)) if valor is not None else ""


def _empregatipo(modalidade):
    if modalidade == "Autônomo":
        return "CONTRACTOR"
    return "FULL_TIME"


def _iso(data):
    if data is None:
        return datetime.utcnow().isoformat()
    return data.isoformat()


def job_posting_jsonld(vaga):
    postado_em = vaga.criada_em or datetime.utcnow()
    valido_ate = postado_em + timedelta(days=45)

    dados = {
        "@context": "https://schema.org/",
        "@type": "JobPosting",
        "title": vaga.cargo,
        "description": vaga.descricao or f"Vaga de {vaga.cargo} na empresa {vaga.empresa}, em {vaga.cidade}.",
        "datePosted": _iso(postado_em),
        "validThrough": _iso(valido_ate),
        "employmentType": _empregatipo(vaga.modalidade),
        "hiringOrganization": {
            "@type": "Organization",
            "name": vaga.empresa,
        },
        "jobLocation": {
            "@type": "Place",
            "address": {
                "@type": "PostalAddress",
                "addressLocality": vaga.cidade,
                "addressRegion": vaga.estado,
                "addressCountry": "BR",
            },
        },
        "identifier": {
            "@type": "PropertyValue",
            "name": SITE_NOME,
            "value": str(vaga.id),
        },
    }

    if vaga.salario:
        dados["baseSalary"] = {
            "@type": "MonetaryAmount",
            "currency": "BRL",
            "value": {
                "@type": "QuantitativeValue",
                "value": vaga.salario,
                "unitText": "MONTH",
            },
        }

    return json.dumps(dados, ensure_ascii=False)


def pagina_vaga_html(vaga):
    url_vaga = f"{SITE_URL}/vagas/{vaga.id}"
    titulo = f"{vaga.cargo} — {vaga.empresa} — {SITE_NOME}"
    descricao_meta = _esc((vaga.descricao or f"Vaga de {vaga.cargo} na {vaga.empresa}, em {vaga.cidade}, {vaga.estado}.")[:200])

    if vaga.link:
        acao_html = f'<a class="btn-candidatar" href="{_esc(vaga.link)}" target="_blank" rel="noopener noreferrer">Ver vaga original ↗</a>'
    else:
        acao_html = f'<button class="btn-candidatar" onclick="abrirCandidaturaVagaAtual()">Candidatar-se</button>'

    salario_html = f"R$ {vaga.salario:,.0f}/mês".replace(",", ".") if vaga.salario else "A combinar"

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{_esc(titulo)}</title>
<meta name="description" content="{descricao_meta}">
<link rel="canonical" href="{_esc(url_vaga)}">
<link rel="stylesheet" href="/css/style.css">
<meta property="og:type" content="website">
<meta property="og:title" content="{_esc(vaga.cargo)} — {_esc(vaga.empresa)}">
<meta property="og:description" content="{descricao_meta}">
<meta property="og:url" content="{_esc(url_vaga)}">
<meta property="og:site_name" content="{SITE_NOME}">
<meta name="twitter:card" content="summary">
<meta name="twitter:title" content="{_esc(vaga.cargo)} — {_esc(vaga.empresa)}">
<meta name="twitter:description" content="{descricao_meta}">
<script type="application/ld+json">{job_posting_jsonld(vaga)}</script>
</head>
<body>
<header class="navbar">
  <div class="navbar-inner">
    <a href="/" class="logo">🚚 <span>{SITE_NOME}</span></a>
  </div>
</header>
<main>
  <section class="vagas" style="padding-top:48px">
    <a href="/#vagas" class="ver-todas">← Voltar para todas as vagas</a>
    <article class="vaga" style="margin-top:24px;max-width:640px">
      <div class="vaga-topo">
        <h1 style="font-size:22px;font-weight:700">{_esc(vaga.cargo)}</h1>
        <span class="tag">{_esc(vaga.categoria)}</span>
      </div>
      <p class="vaga-info">{_esc(vaga.empresa)} • {_esc(vaga.cidade)}, {_esc(vaga.estado)}</p>
      <p class="vaga-info">{_esc(vaga.descricao) if vaga.descricao else ''}</p>
      <div class="vaga-rodape">
        <span class="salario">{salario_html}</span>
        {acao_html}
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
  function abrirCandidaturaVagaAtual() {{
    window.__vagaAtual = {{
      id: {vaga.id},
      cargo: {json.dumps(vaga.cargo, ensure_ascii=False)},
      empresa: {json.dumps(vaga.empresa, ensure_ascii=False)},
      cidade: {json.dumps(vaga.cidade, ensure_ascii=False)},
      estado: {json.dumps(vaga.estado, ensure_ascii=False)},
    }};
    if (typeof abrirModalCandidatura === 'function') {{
      abrirModalCandidatura(window.__vagaAtual);
    }}
  }}
</script>
</body>
</html>"""


def pagina_sitemap_xml(vagas):
    urls = [f"<url><loc>{SITE_URL}/</loc><changefreq>hourly</changefreq><priority>1.0</priority></url>"]
    for vaga in vagas:
        urls.append(
            f"<url><loc>{SITE_URL}/vagas/{vaga.id}</loc>"
            f"<lastmod>{_iso(vaga.criada_em)[:10]}</lastmod>"
            f"<changefreq>daily</changefreq><priority>0.8</priority></url>"
        )

    corpo = "".join(urls)
    return f'<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{corpo}</urlset>'


ROBOTS_TXT = f"""User-agent: *
Allow: /

Sitemap: {SITE_URL}/sitemap.xml
"""
