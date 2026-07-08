const API_BASE = '/api';

function escapeHtml(valor) {
  const texto = valor === null || valor === undefined ? '' : String(valor);
  return texto.replace(/[&<>"']/g, (c) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  }[c]));
}

/* ===== Tema claro/escuro ===== */

const CHAVE_TEMA = 'logjobs-tema';
const btnTema = document.getElementById('btnTema');

function temaAtivo() {
  const armazenado = localStorage.getItem(CHAVE_TEMA);
  if (armazenado === 'dark' || armazenado === 'light') return armazenado;
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

function aplicarIconeTema(tema) {
  if (btnTema) btnTema.textContent = tema === 'dark' ? '☀️' : '🌙';
}

aplicarIconeTema(temaAtivo());

if (btnTema) {
  btnTema.addEventListener('click', () => {
    const novoTema = temaAtivo() === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', novoTema);
    localStorage.setItem(CHAVE_TEMA, novoTema);
    aplicarIconeTema(novoTema);
  });
}

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
const carregarMaisBotao = document.getElementById('carregarMais');

const TAMANHO_PAGINA = 20;
let vagasCarregadas = [];
let filtroAtual = {};
let totalDisponivel = 0;

function formatarSalario(valor) {
  if (!valor) return 'A combinar';
  return `R$ ${Number(valor).toLocaleString('pt-BR')}/mês`;
}

function botaoCandidatura(vaga) {
  if (vaga.link) {
    return `<a class="btn-candidatar" href="${escapeHtml(vaga.link)}" target="_blank" rel="noopener noreferrer">Ver vaga original ↗</a>`;
  }
  return `<button class="btn-candidatar" data-vaga-id="${escapeHtml(vaga.id)}">Candidatar-se</button>`;
}

function vagaParaHtml(vaga) {
  return `
    <article class="vaga">
      <div class="vaga-topo">
        <h3><a href="/vagas/${escapeHtml(vaga.id)}">${escapeHtml(vaga.empresa)}</a></h3>
        <span class="tag">${escapeHtml(vaga.categoria || '')}</span>
      </div>
      <p class="vaga-info"><a href="/vagas/${escapeHtml(vaga.id)}">${escapeHtml(vaga.cargo)}</a> • ${escapeHtml(vaga.cidade)}${vaga.estado ? ', ' + escapeHtml(vaga.estado) : ''}</p>
      <div class="vaga-rodape">
        <span class="salario">${escapeHtml(formatarSalario(vaga.salario))}</span>
        ${botaoCandidatura(vaga)}
      </div>
    </article>
  `;
}

function renderizarVagas(vagas) {
  if (!vagasGrid) return;

  if (vagas.length === 0) {
    vagasGrid.innerHTML = '<p class="vagas-carregando">Nenhuma vaga encontrada para esse filtro.</p>';
    return;
  }

  vagasGrid.innerHTML = vagas.map(vagaParaHtml).join('');
}

function atualizarBotaoCarregarMais() {
  if (!carregarMaisBotao) return;
  carregarMaisBotao.hidden = vagasCarregadas.length >= totalDisponivel;
}

async function buscarVagas(params = {}) {
  filtroAtual = params;

  if (vagasGrid) {
    vagasGrid.innerHTML = '<p class="vagas-carregando">Carregando vagas...</p>';
  }

  const query = new URLSearchParams({ ...params, limit: TAMANHO_PAGINA, offset: 0 }).toString();

  try {
    const resposta = await fetch(`${API_BASE}/vagas?${query}`);
    const dados = await resposta.json();
    vagasCarregadas = dados.vagas || [];
    totalDisponivel = dados.total || 0;
    renderizarVagas(vagasCarregadas);
    atualizarBotaoCarregarMais();
  } catch (erro) {
    if (vagasGrid) {
      vagasGrid.innerHTML = '<p class="vagas-carregando">Não foi possível carregar as vagas. Tente novamente em instantes.</p>';
    }
    console.error('Erro ao buscar vagas:', erro);
  }
}

async function carregarMaisVagas() {
  const query = new URLSearchParams({ ...filtroAtual, limit: TAMANHO_PAGINA, offset: vagasCarregadas.length }).toString();

  try {
    const resposta = await fetch(`${API_BASE}/vagas?${query}`);
    const dados = await resposta.json();
    vagasCarregadas = vagasCarregadas.concat(dados.vagas || []);
    totalDisponivel = dados.total || 0;

    if (vagasGrid) {
      vagasGrid.insertAdjacentHTML('beforeend', (dados.vagas || []).map(vagaParaHtml).join(''));
    }
    atualizarBotaoCarregarMais();
  } catch (erro) {
    console.error('Erro ao carregar mais vagas:', erro);
  }
}

if (carregarMaisBotao) {
  carregarMaisBotao.addEventListener('click', carregarMaisVagas);
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

const statAtualizacao = document.getElementById('statAtualizacao');
const statAtualizacaoLegenda = document.getElementById('statAtualizacaoLegenda');

function tempoDecorrido(isoString) {
  const minutos = Math.max(0, Math.round((Date.now() - new Date(isoString).getTime()) / 60000));
  if (minutos < 1) return 'agora mesmo';
  if (minutos === 1) return 'há 1 min';
  if (minutos < 60) return `há ${minutos} min`;
  const horas = Math.round(minutos / 60);
  return horas === 1 ? 'há 1h' : `há ${horas}h`;
}

async function carregarStatusAtualizacao() {
  try {
    const resposta = await fetch(`${API_BASE}/status`);
    const dados = await resposta.json();

    if (dados.ultima_atualizacao) {
      if (statAtualizacao) statAtualizacao.textContent = tempoDecorrido(dados.ultima_atualizacao);
      if (statAtualizacaoLegenda) {
        statAtualizacaoLegenda.textContent = dados.jooble_configurado
          ? 'Última atualização automática'
          : 'Última verificação (aguardando fonte real)';
      }
    } else if (statAtualizacaoLegenda) {
      statAtualizacaoLegenda.textContent = dados.jooble_configurado
        ? 'Atualização automática a cada 20 min'
        : 'Atualização a cada 20 min (fonte real pendente)';
    }
  } catch (erro) {
    console.error('Erro ao buscar status de atualização:', erro);
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
let elementoFocoAnterior = null;

function abrirModal(html) {
  if (!modalOverlay || !modalConteudo) return;
  elementoFocoAnterior = document.activeElement;
  modalConteudo.innerHTML = html;
  modalOverlay.hidden = false;
  const primeiroCampo = modalConteudo.querySelector('input, button');
  primeiroCampo?.focus();
}

function fecharModal() {
  if (!modalOverlay) return;
  modalOverlay.hidden = true;
  modalConteudo.innerHTML = '';
  elementoFocoAnterior?.focus();
}

if (modalFechar) modalFechar.addEventListener('click', fecharModal);
if (modalOverlay) {
  modalOverlay.addEventListener('click', (event) => {
    if (event.target === modalOverlay) fecharModal();
  });
  modalOverlay.addEventListener('keydown', (event) => {
    if (event.key !== 'Tab') return;
    const focaveis = modalOverlay.querySelectorAll('input, button, a[href]');
    if (focaveis.length === 0) return;
    const primeiro = focaveis[0];
    const ultimo = focaveis[focaveis.length - 1];
    if (event.shiftKey && document.activeElement === primeiro) {
      event.preventDefault();
      ultimo.focus();
    } else if (!event.shiftKey && document.activeElement === ultimo) {
      event.preventDefault();
      primeiro.focus();
    }
  });
}
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape') fecharModal();
});

const CAMPO_HONEYPOT = `<input type="text" name="empresa_no_meio" tabindex="-1" autocomplete="off" style="position:absolute;left:-9999px;width:1px;height:1px;opacity:0" aria-hidden="true">`;

/* ===== Candidatura ===== */

function abrirModalCandidatura(vaga) {
  abrirModal(`
    <h2>Candidatar-se: ${escapeHtml(vaga.cargo)}</h2>
    <p class="modal-subtitulo">${escapeHtml(vaga.empresa)} • ${escapeHtml(vaga.cidade)}${vaga.estado ? ', ' + escapeHtml(vaga.estado) : ''}</p>
    <form id="formCandidatura">
      ${CAMPO_HONEYPOT}
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
          empresa_no_meio: form.empresa_no_meio.value,
        }),
      });

      if (!resposta.ok) {
        if (resposta.status === 429) throw new Error('Muitas tentativas. Aguarde alguns minutos.');
        throw new Error('Falha ao enviar candidatura');
      }

      abrirModal(`
        <div class="modal-sucesso">
          <div class="icone">✅</div>
          <h2>Candidatura enviada!</h2>
          <p class="modal-subtitulo">A empresa ${escapeHtml(vaga.empresa)} vai analisar seu perfil para a vaga de ${escapeHtml(vaga.cargo)}.</p>
        </div>
      `);
    } catch (erro) {
      erroEl.textContent = erro.message || 'Não foi possível enviar sua candidatura. Tente novamente.';
      erroEl.hidden = false;
      console.error(erro);
    }
  });
}

if (vagasGrid) {
  vagasGrid.addEventListener('click', (event) => {
    const botao = event.target.closest('.btn-candidatar');
    if (!botao || botao.tagName === 'A') return;
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
    <h2>${escapeHtml(titulo)}</h2>
    <p class="modal-subtitulo">${escapeHtml(subtitulo)}</p>
    <form id="formInteressado">
      ${CAMPO_HONEYPOT}
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
          empresa_no_meio: form.empresa_no_meio.value,
        }),
      });

      if (!resposta.ok) {
        if (resposta.status === 429) throw new Error('Muitas tentativas. Aguarde alguns minutos.');
        throw new Error('Falha ao enviar cadastro');
      }

      abrirModal(`
        <div class="modal-sucesso">
          <div class="icone">🎉</div>
          <h2>Cadastro recebido!</h2>
          <p class="modal-subtitulo">Vamos avisar você assim que essa funcionalidade estiver disponível.</p>
        </div>
      `);
    } catch (erro) {
      erroEl.textContent = erro.message || 'Não foi possível enviar seu cadastro. Tente novamente.';
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

if (vagasGrid) buscarVagas();
carregarEstatisticas();
carregarStatusAtualizacao();
