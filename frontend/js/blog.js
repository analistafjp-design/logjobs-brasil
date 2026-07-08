let artigosCarregados = [];
let categoriaAtiva = '';

function formatarDataArtigo(iso) {
  if (!iso) return '';
  return new Date(iso).toLocaleDateString('pt-BR', { day: '2-digit', month: 'long', year: 'numeric' });
}

function renderizarFiltros() {
  const categorias = [...new Set(artigosCarregados.map((a) => a.categoria))];
  const container = document.getElementById('blogFiltros');
  container.innerHTML = [
    `<button class="blog-filtro-btn${categoriaAtiva === '' ? ' ativo' : ''}" data-categoria="">Todos</button>`,
    ...categorias.map((c) => `<button class="blog-filtro-btn${categoriaAtiva === c ? ' ativo' : ''}" data-categoria="${escapeHtml(c)}">${escapeHtml(c)}</button>`),
  ].join('');

  container.querySelectorAll('.blog-filtro-btn').forEach((botao) => {
    botao.addEventListener('click', () => {
      categoriaAtiva = botao.dataset.categoria;
      renderizarFiltros();
      renderizarArtigos();
    });
  });
}

function renderizarArtigos() {
  const container = document.getElementById('blogGrid');
  const lista = categoriaAtiva ? artigosCarregados.filter((a) => a.categoria === categoriaAtiva) : artigosCarregados;

  if (!lista.length) {
    container.innerHTML = '<p class="dash-carregando">Nenhum artigo nessa categoria ainda.</p>';
    return;
  }

  container.innerHTML = lista.map((a) => `
    <article class="blog-card">
      <span class="tag">${escapeHtml(a.categoria)}</span>
      <h2><a href="artigo.html?slug=${encodeURIComponent(a.slug)}">${escapeHtml(a.titulo)}</a></h2>
      <p>${escapeHtml(a.resumo)}</p>
      <div class="blog-meta">
        <span>${escapeHtml(a.autor)}</span>
        <span>${formatarDataArtigo(a.publicado_em)}</span>
      </div>
    </article>
  `).join('');
}

async function carregarBlog() {
  try {
    const resposta = await fetch('/api/blog');
    artigosCarregados = await resposta.json();
    renderizarFiltros();
    renderizarArtigos();
  } catch (erro) {
    document.getElementById('blogGrid').innerHTML = '<p class="dash-carregando">Não foi possível carregar os artigos.</p>';
    console.error(erro);
  }
}

carregarBlog();
