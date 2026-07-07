const API_BASE = '/api';

const navToggle = document.getElementById('navToggle');
const navLinks = document.getElementById('navLinks');

if (navToggle && navLinks) {
  navToggle.addEventListener('click', () => {
    const aberto = navLinks.classList.toggle('aberto');
    navToggle.setAttribute('aria-expanded', String(aberto));
  });

  navLinks.querySelectorAll('a').forEach((link) => {
    link.addEventListener('click', () => {
      navLinks.classList.remove('aberto');
      navToggle.setAttribute('aria-expanded', 'false');
    });
  });
}

const vagasGrid = document.getElementById('vagasGrid');
const statVagas = document.getElementById('statVagas');
const statEmpresas = document.getElementById('statEmpresas');
const statCidades = document.getElementById('statCidades');
const searchForm = document.querySelector('.search-box');
const limparFiltro = document.getElementById('limparFiltro');

function formatarSalario(valor) {
  if (!valor) return 'A combinar';
  return `R$ ${Number(valor).toLocaleString('pt-BR')}/mês`;
}

function renderizarVagas(vagas) {
  if (!vagasGrid) return;

  if (vagas.length === 0) {
    vagasGrid.innerHTML = '<p class="vagas-carregando">Nenhuma vaga encontrada para esse filtro.</p>';
    return;
  }

  vagasGrid.innerHTML = vagas.map((vaga) => `
    <article class="vaga">
      <div class="vaga-topo">
        <h3>${vaga.empresa}</h3>
        <span class="tag">${vaga.categoria || ''}</span>
      </div>
      <p class="vaga-info">${vaga.cargo} • ${vaga.cidade}${vaga.estado ? ', ' + vaga.estado : ''}</p>
      <div class="vaga-rodape">
        <span class="salario">${formatarSalario(vaga.salario)}</span>
        <button class="btn-candidatar" data-vaga-id="${vaga.id}">Candidatar-se</button>
      </div>
    </article>
  `).join('');
}

async function buscarVagas(params = {}) {
  if (vagasGrid) {
    vagasGrid.innerHTML = '<p class="vagas-carregando">Carregando vagas...</p>';
  }

  const query = new URLSearchParams(params).toString();

  try {
    const resposta = await fetch(`${API_BASE}/vagas${query ? '?' + query : ''}`);
    const dados = await resposta.json();
    renderizarVagas(dados.vagas || []);
  } catch (erro) {
    if (vagasGrid) {
      vagasGrid.innerHTML = '<p class="vagas-carregando">Não foi possível carregar as vagas. Tente novamente em instantes.</p>';
    }
    console.error('Erro ao buscar vagas:', erro);
  }
}

async function carregarEstatisticas() {
  try {
    const resposta = await fetch(`${API_BASE}/estatisticas`);
    const dados = await resposta.json();
    if (statVagas) statVagas.textContent = dados.vagas ?? '—';
    if (statEmpresas) statEmpresas.textContent = dados.empresas ?? '—';
    if (statCidades) statCidades.textContent = dados.cidades ?? '—';
  } catch (erro) {
    console.error('Erro ao buscar estatísticas:', erro);
  }
}

if (searchForm) {
  searchForm.addEventListener('submit', (event) => {
    event.preventDefault();
    const [cargoInput, cidadeInput] = searchForm.querySelectorAll('input');
    buscarVagas({
      cargo: cargoInput.value.trim(),
      cidade: cidadeInput.value.trim(),
    });
  });
}

document.querySelectorAll('.categoria').forEach((botao) => {
  botao.addEventListener('click', () => {
    buscarVagas({ categoria: botao.dataset.categoria });
    document.getElementById('vagas')?.scrollIntoView({ behavior: 'smooth' });
  });
});

if (limparFiltro) {
  limparFiltro.addEventListener('click', (event) => {
    event.preventDefault();
    buscarVagas();
  });
}

if (vagasGrid) {
  vagasGrid.addEventListener('click', (event) => {
    const botao = event.target.closest('.btn-candidatar');
    if (!botao) return;
    console.log('Candidatura iniciada para vaga id:', botao.dataset.vagaId);
  });
}

buscarVagas();
carregarEstatisticas();
