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

let vagasCarregadas = [];

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
    vagasCarregadas = dados.vagas || [];
    renderizarVagas(vagasCarregadas);
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

/* ===== Toast ===== */

const toast = document.getElementById('toast');
let toastTimeout;

function mostrarToast(mensagem) {
  if (!toast) return;
  toast.textContent = mensagem;
  toast.hidden = false;
  clearTimeout(toastTimeout);
  toastTimeout = setTimeout(() => { toast.hidden = true; }, 3500);
}

/* ===== Modal ===== */

const modalOverlay = document.getElementById('modalOverlay');
const modalConteudo = document.getElementById('modalConteudo');
const modalFechar = document.getElementById('modalFechar');

function abrirModal(html) {
  if (!modalOverlay || !modalConteudo) return;
  modalConteudo.innerHTML = html;
  modalOverlay.hidden = false;
}

function fecharModal() {
  if (!modalOverlay) return;
  modalOverlay.hidden = true;
  modalConteudo.innerHTML = '';
}

if (modalFechar) modalFechar.addEventListener('click', fecharModal);
if (modalOverlay) {
  modalOverlay.addEventListener('click', (event) => {
    if (event.target === modalOverlay) fecharModal();
  });
}
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape') fecharModal();
});

/* ===== Candidatura ===== */

function abrirModalCandidatura(vaga) {
  abrirModal(`
    <h2>Candidatar-se: ${vaga.cargo}</h2>
    <p class="modal-subtitulo">${vaga.empresa} • ${vaga.cidade}${vaga.estado ? ', ' + vaga.estado : ''}</p>
    <form id="formCandidatura">
      <label>Nome completo
        <input type="text" name="nome" required autocomplete="name">
      </label>
      <label>E-mail
        <input type="email" name="email" required autocomplete="email">
      </label>
      <label>Telefone
        <input type="tel" name="telefone" autocomplete="tel">
      </label>
      <p class="modal-erro" id="candidaturaErro" hidden></p>
      <button type="submit" class="modal-enviar">Enviar candidatura</button>
    </form>
  `);

  document.getElementById('formCandidatura').addEventListener('submit', async (event) => {
    event.preventDefault();
    const form = event.target;
    const erroEl = document.getElementById('candidaturaErro');
    erroEl.hidden = true;

    try {
      const resposta = await fetch(`${API_BASE}/candidaturas`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          vaga_id: vaga.id,
          nome: form.nome.value.trim(),
          email: form.email.value.trim(),
          telefone: form.telefone.value.trim() || null,
        }),
      });

      if (!resposta.ok) throw new Error('Falha ao enviar candidatura');

      abrirModal(`
        <div class="modal-sucesso">
          <div class="icone">✅</div>
          <h2>Candidatura enviada!</h2>
          <p class="modal-subtitulo">A empresa ${vaga.empresa} vai analisar seu perfil para a vaga de ${vaga.cargo}.</p>
        </div>
      `);
    } catch (erro) {
      erroEl.textContent = 'Não foi possível enviar sua candidatura. Tente novamente.';
      erroEl.hidden = false;
      console.error(erro);
    }
  });
}

if (vagasGrid) {
  vagasGrid.addEventListener('click', (event) => {
    const botao = event.target.closest('.btn-candidatar');
    if (!botao) return;
    const vaga = vagasCarregadas.find((v) => String(v.id) === botao.dataset.vagaId);
    if (vaga) abrirModalCandidatura(vaga);
  });
}

/* ===== Lista de espera (candidato / empresa) ===== */

function abrirModalListaEspera(tipo) {
  const titulo = tipo === 'empresa' ? 'Anuncie suas vagas no LogJobs' : 'Entre na lista de espera';
  const subtitulo = tipo === 'empresa'
    ? 'Estamos abrindo aos poucos para empresas parceiras. Deixe seu contato e avisaremos você.'
    : 'O login completo de candidatos está em desenvolvimento. Deixe seu contato e avisaremos assim que estiver no ar.';

  abrirModal(`
    <h2>${titulo}</h2>
    <p class="modal-subtitulo">${subtitulo}</p>
    <form id="formInteressado">
      <label>Nome
        <input type="text" name="nome" required autocomplete="name">
      </label>
      <label>E-mail
        <input type="email" name="email" required autocomplete="email">
      </label>
      <p class="modal-erro" id="interessadoErro" hidden></p>
      <button type="submit" class="modal-enviar">Quero ser avisado</button>
    </form>
  `);

  document.getElementById('formInteressado').addEventListener('submit', async (event) => {
    event.preventDefault();
    const form = event.target;
    const erroEl = document.getElementById('interessadoErro');
    erroEl.hidden = true;

    try {
      const resposta = await fetch(`${API_BASE}/interessados`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          nome: form.nome.value.trim(),
          email: form.email.value.trim(),
          tipo,
        }),
      });

      if (!resposta.ok) throw new Error('Falha ao enviar cadastro');

      abrirModal(`
        <div class="modal-sucesso">
          <div class="icone">🎉</div>
          <h2>Cadastro recebido!</h2>
          <p class="modal-subtitulo">Vamos avisar você assim que essa funcionalidade estiver disponível.</p>
        </div>
      `);
    } catch (erro) {
      erroEl.textContent = 'Não foi possível enviar seu cadastro. Tente novamente.';
      erroEl.hidden = false;
      console.error(erro);
    }
  });
}

document.querySelectorAll('[data-lista-espera]').forEach((el) => {
  el.addEventListener('click', (event) => {
    event.preventDefault();
    abrirModalListaEspera(el.dataset.listaEspera);
  });
});

document.querySelectorAll('[data-em-breve]').forEach((el) => {
  el.addEventListener('click', (event) => {
    event.preventDefault();
    mostrarToast(`🚧 ${el.dataset.emBreve} — em breve!`);
  });
});

buscarVagas();
carregarEstatisticas();
