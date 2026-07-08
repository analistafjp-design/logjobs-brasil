function formatarDataArtigo(iso) {
  if (!iso) return '';
  return new Date(iso).toLocaleDateString('pt-BR', { day: '2-digit', month: 'long', year: 'numeric' });
}

async function carregarArtigo() {
  const slug = new URLSearchParams(window.location.search).get('slug');
  const container = document.getElementById('artigoConteudo');

  if (!slug) {
    container.innerHTML = '<p>Artigo não especificado. <a href="blog.html">Voltar ao blog</a>.</p>';
    return;
  }

  try {
    const resposta = await fetch(`/api/blog/${encodeURIComponent(slug)}`);
    if (!resposta.ok) throw new Error();
    const artigo = await resposta.json();

    document.title = `${artigo.titulo} — Blog LogJobs Brasil`;
    document.getElementById('metaDescricao').setAttribute('content', artigo.resumo);
    document.getElementById('linkCanonico').setAttribute('href', `https://logjobs-brasil.onrender.com/artigo.html?slug=${artigo.slug}`);

    const paragrafos = artigo.conteudo.split('\n\n').map((p) => `<p>${escapeHtml(p)}</p>`).join('');

    container.innerHTML = `
      <span class="tag">${escapeHtml(artigo.categoria)}</span>
      <h1>${escapeHtml(artigo.titulo)}</h1>
      <p class="artigo-meta">Por ${escapeHtml(artigo.autor)} · ${formatarDataArtigo(artigo.publicado_em)}</p>
      <div class="artigo-corpo">${paragrafos}</div>
      <a class="artigo-voltar" href="blog.html">← Voltar ao blog</a>
    `;

    injetarSchemaArtigo(artigo);
  } catch {
    container.innerHTML = '<p>Não foi possível carregar este artigo. <a href="blog.html">Voltar ao blog</a>.</p>';
  }
}

function injetarSchemaArtigo(artigo) {
  const schema = {
    "@context": "https://schema.org",
    "@type": "Article",
    headline: artigo.titulo,
    description: artigo.resumo,
    author: { "@type": "Organization", name: artigo.autor },
    datePublished: artigo.publicado_em,
  };
  const script = document.createElement('script');
  script.type = 'application/ld+json';
  script.textContent = JSON.stringify(schema);
  document.head.appendChild(script);
}

carregarArtigo();
