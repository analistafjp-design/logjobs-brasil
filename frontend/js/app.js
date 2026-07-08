const API_BASE = '/api';

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch((erro) => {
      console.warn('Não foi possível registrar o service worker:', erro);
    });
  });
}

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

function botaoSalvar(vaga) {
  const salva = favoritosIds.has(Number(vaga.id));
  return `<button class="btn-salvar${salva ? ' salvo' : ''}" data-vaga-id="${escapeHtml(vaga.id)}" aria-pressed="${salva}" aria-label="${salva ? 'Remover dos salvos' : 'Salvar vaga'}" title="${salva ? 'Remover dos salvos' : 'Salvar vaga'}">${salva ? '★' : '☆'}</button>`;
}

function vagaParaHtml(vaga, indice = 0) {
  const detalhes = [vaga.modalidade, vaga.turno, vaga.tipo_contratacao].filter(Boolean);
  return `
    <article class="vaga" style="animation-delay:${Math.min(indice, 8) * 40}ms">
      <div class="vaga-topo">
        <h3><a href="/vagas/${escapeHtml(vaga.id)}">${escapeHtml(vaga.empresa)}</a></h3>
        <span class="tag">${escapeHtml(vaga.categoria || '')}</span>
      </div>
      <p class="vaga-info"><a href="/vagas/${escapeHtml(vaga.id)}">${escapeHtml(vaga.cargo)}</a> • ${escapeHtml(vaga.cidade)}${vaga.estado ? ', ' + escapeHtml(vaga.estado) : ''}</p>
      ${detalhes.length ? `<p class="vaga-detalhes">${detalhes.map(escapeHtml).join(' · ')}</p>` : ''}
      <div class="vaga-rodape">
        <span class="salario">${escapeHtml(formatarSalario(vaga.salario))}</span>
        <div class="vaga-acoes">
          ${botaoSalvar(vaga)}
          ${botaoCandidatura(vaga)}
        </div>
      </div>
    </article>
  `;
}

function renderizarSkeletons(quantidade = 6) {
  if (!vagasGrid) return;
  vagasGrid.innerHTML = Array.from({ length: quantidade }).map(() => `
    <div class="skeleton-card" aria-hidden="true">
      <div class="skeleton-linha curta"></div>
      <div class="skeleton-linha media"></div>
      <div class="skeleton-linha"></div>
      <div class="skeleton-linha larga"></div>
    </div>
  `).join('');
}

function renderizarVagas(vagas) {
  if (!vagasGrid) return;

  if (vagas.length === 0) {
    vagasGrid.innerHTML = `
      <div class="empty-state">
        <div class="empty-icone">🔍</div>
        <h3>Nenhuma vaga encontrada</h3>
        <p>Tente ajustar os filtros ou buscar por outro termo.</p>
        <button type="button" id="btnLimparBuscaVazia">Limpar filtros</button>
      </div>
    `;
    document.getElementById('btnLimparBuscaVazia')?.addEventListener('click', () => {
      limparTodosFiltros();
    });
    return;
  }

  vagasGrid.innerHTML = vagas.map(vagaParaHtml).join('');
}

function atualizarBotaoCarregarMais() {
  if (!carregarMaisBotao) return;
  carregarMaisBotao.hidden = vagasCarregadas.length >= totalDisponivel;
}

function limparParams(params) {
  const limpo = {};
  Object.entries(params).forEach(([chave, valor]) => {
    if (valor !== undefined && valor !== null && valor !== '') limpo[chave] = valor;
  });
  return limpo;
}

async function buscarVagas(params = {}) {
  filtroAtual = limparParams(params);

  renderizarSkeletons();

  const query = new URLSearchParams({ ...filtroAtual, limit: TAMANHO_PAGINA, offset: 0 }).toString();

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

/* ===== Filtros avançados ===== */

const IDS_FILTROS_SELECT = ['filtroEstado', 'filtroModalidade', 'filtroTurno', 'filtroTipoContratacao'];
const IDS_FILTROS_TEXTO = ['filtroSalarioMin', 'filtroSalarioMax', 'filtroBeneficio'];

function coletarFiltrosBasicos() {
  if (!searchForm) return {};
  const [cargoInput, cidadeInput] = searchForm.querySelectorAll('input');
  return {
    cargo: cargoInput.value.trim(),
    cidade: cidadeInput.value.trim(),
  };
}

function coletarFiltrosAvancados() {
  const valor = (id) => document.getElementById(id)?.value.trim() || '';
  return {
    estado: valor('filtroEstado'),
    modalidade: valor('filtroModalidade'),
    turno: valor('filtroTurno'),
    tipo_contratacao: valor('filtroTipoContratacao'),
    salario_min: valor('filtroSalarioMin'),
    salario_max: valor('filtroSalarioMax'),
    beneficio: valor('filtroBeneficio'),
    ordenar: document.getElementById('filtroOrdenar')?.value || 'recentes',
  };
}

function atualizarBadgeFiltros() {
  const avancados = coletarFiltrosAvancados();
  const total = Object.entries(avancados).filter(
    ([chave, val]) => val && !(chave === 'ordenar' && val === 'recentes')
  ).length;
  const badge = document.getElementById('filtrosAtivosCount');
  if (badge) badge.textContent = total > 0 ? `(${total})` : '';
}

function executarBuscaCompleta() {
  const params = { ...coletarFiltrosBasicos(), ...coletarFiltrosAvancados() };
  buscarVagas(params);
  salvarBuscaRecente(params);
  atualizarBadgeFiltros();
}

function limparTodosFiltros() {
  searchForm?.reset();
  [...IDS_FILTROS_SELECT, ...IDS_FILTROS_TEXTO].forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.value = '';
  });
  const ordenar = document.getElementById('filtroOrdenar');
  if (ordenar) ordenar.value = 'recentes';
  atualizarBadgeFiltros();
  buscarVagas({});
}

const btnFiltrosAvancados = document.getElementById('btnFiltrosAvancados');
const painelFiltrosAvancados = document.getElementById('filtrosAvancados');

if (btnFiltrosAvancados && painelFiltrosAvancados) {
  btnFiltrosAvancados.addEventListener('click', () => {
    const estaAberto = !painelFiltrosAvancados.hidden;
    painelFiltrosAvancados.hidden = estaAberto;
    btnFiltrosAvancados.setAttribute('aria-expanded', String(!estaAberto));
  });
}

document.getElementById('btnAplicarFiltros')?.addEventListener('click', () => {
  executarBuscaCompleta();
  document.getElementById('vagas')?.scrollIntoView({ behavior: 'smooth' });
});

document.getElementById('btnLimparFiltrosAvancados')?.addEventListener('click', limparTodosFiltros);

/* ===== Autocomplete (cargo / cidade) ===== */

function configurarAutocomplete(inputEl, datalistId, tipo) {
  if (!inputEl) return;
  let temporizador;
  inputEl.addEventListener('input', () => {
    clearTimeout(temporizador);
    const valor = inputEl.value.trim();
    if (valor.length < 2) return;
    temporizador = setTimeout(async () => {
      try {
        const resposta = await fetch(`${API_BASE}/sugestoes?tipo=${tipo}&q=${encodeURIComponent(valor)}`);
        const sugestoes = await resposta.json();
        const datalist = document.getElementById(datalistId);
        if (datalist) datalist.innerHTML = sugestoes.map((s) => `<option value="${escapeHtml(s)}"></option>`).join('');
      } catch {
        // Autocomplete é um acessório da busca — falha silenciosa não deve travar o usuário.
      }
    }, 250);
  });
}

if (searchForm) {
  const [cargoInput, cidadeInput] = searchForm.querySelectorAll('input');
  configurarAutocomplete(cargoInput, 'listaCargos', 'cargo');
  configurarAutocomplete(cidadeInput, 'listaCidades', 'cidade');

  searchForm.addEventListener('submit', (event) => {
    event.preventDefault();
    executarBuscaCompleta();
  });
}

/* ===== Histórico de buscas (local ao navegador) ===== */

const CHAVE_BUSCAS_RECENTES = 'logjobs-buscas-recentes';

function obterBuscasRecentes() {
  try {
    return JSON.parse(localStorage.getItem(CHAVE_BUSCAS_RECENTES) || '[]');
  } catch {
    return [];
  }
}

function salvarBuscaRecente(params) {
  if (!params.cargo && !params.cidade) return;
  const atuais = obterBuscasRecentes().filter(
    (b) => !(b.cargo === params.cargo && b.cidade === params.cidade)
  );
  atuais.unshift(params);
  localStorage.setItem(CHAVE_BUSCAS_RECENTES, JSON.stringify(atuais.slice(0, 5)));
  renderizarBuscasRecentes();
}

function rotuloBusca(b) {
  return [b.cargo, b.cidade].filter(Boolean).join(' em ') || 'Todas as vagas';
}

function renderizarBuscasRecentes() {
  const container = document.getElementById('buscasRecentes');
  const chipsEl = document.getElementById('buscasRecentesChips');
  if (!container || !chipsEl) return;

  const buscas = obterBuscasRecentes();
  if (!buscas.length) {
    container.hidden = true;
    return;
  }

  container.hidden = false;
  chipsEl.innerHTML = buscas.map((b, indice) => `
    <button type="button" class="busca-recente-chip" data-indice="${indice}">${escapeHtml(rotuloBusca(b))}</button>
  `).join('');

  chipsEl.querySelectorAll('.busca-recente-chip').forEach((chip) => {
    chip.addEventListener('click', () => {
      const busca = buscas[Number(chip.dataset.indice)];
      if (searchForm) {
        const [cargoInput, cidadeInput] = searchForm.querySelectorAll('input');
        cargoInput.value = busca.cargo || '';
        cidadeInput.value = busca.cidade || '';
      }
      IDS_FILTROS_SELECT.concat(IDS_FILTROS_TEXTO).forEach((id) => {
        const chaveApi = { filtroEstado: 'estado', filtroModalidade: 'modalidade', filtroTurno: 'turno', filtroTipoContratacao: 'tipo_contratacao', filtroSalarioMin: 'salario_min', filtroSalarioMax: 'salario_max', filtroBeneficio: 'beneficio' }[id];
        const el = document.getElementById(id);
        if (el) el.value = busca[chaveApi] || '';
      });
      atualizarBadgeFiltros();
      buscarVagas(busca);
      document.getElementById('vagas')?.scrollIntoView({ behavior: 'smooth' });
    });
  });
}

renderizarBuscasRecentes();

document.querySelectorAll('.categoria').forEach((botao) => {
  botao.addEventListener('click', () => {
    buscarVagas({ categoria: botao.dataset.categoria });
    document.getElementById('vagas')?.scrollIntoView({ behavior: 'smooth' });
  });
});

if (limparFiltro) {
  limparFiltro.addEventListener('click', (event) => {
    event.preventDefault();
    limparTodosFiltros();
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
  const usuarioLogado = typeof obterUsuario === 'function' ? obterUsuario() : null;

  abrirModal(`
    <h2>Candidatar-se: ${escapeHtml(vaga.cargo)}</h2>
    <p class="modal-subtitulo">${escapeHtml(vaga.empresa)} • ${escapeHtml(vaga.cidade)}${vaga.estado ? ', ' + escapeHtml(vaga.estado) : ''}</p>
    <form id="formCandidatura">
      ${CAMPO_HONEYPOT}
      <label>Nome completo
        <input type="text" name="nome" required autocomplete="name" value="${usuarioLogado ? escapeHtml(usuarioLogado.nome) : ''}">
      </label>
      <label>E-mail
        <input type="email" name="email" required autocomplete="email" value="${usuarioLogado ? escapeHtml(usuarioLogado.email) : ''}">
      </label>
      <label>Telefone
        <input type="tel" name="telefone" autocomplete="tel" value="${usuarioLogado ? escapeHtml(usuarioLogado.telefone || '') : ''}">
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
    const botaoCandidatar = event.target.closest('.btn-candidatar');
    if (botaoCandidatar && botaoCandidatar.tagName !== 'A') {
      const vaga = vagasCarregadas.find((v) => String(v.id) === botaoCandidatar.dataset.vagaId);
      if (vaga) abrirModalCandidatura(vaga);
      return;
    }

    const botaoSalvarEl = event.target.closest('.btn-salvar');
    if (botaoSalvarEl) {
      alternarFavorito(botaoSalvarEl.dataset.vagaId, botaoSalvarEl);
    }
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

/* ===== Autenticação (candidato / empresa) ===== */

const CHAVE_TOKEN = 'logjobs-token';
const CHAVE_USUARIO = 'logjobs-usuario';
const areaConta = document.getElementById('areaConta');
let favoritosIds = new Set();

function obterToken() {
  return localStorage.getItem(CHAVE_TOKEN);
}

function obterUsuario() {
  try {
    return JSON.parse(localStorage.getItem(CHAVE_USUARIO) || 'null');
  } catch {
    return null;
  }
}

function salvarSessao(token, usuario) {
  localStorage.setItem(CHAVE_TOKEN, token);
  localStorage.setItem(CHAVE_USUARIO, JSON.stringify(usuario));
}

function encerrarSessao() {
  localStorage.removeItem(CHAVE_TOKEN);
  localStorage.removeItem(CHAVE_USUARIO);
  favoritosIds = new Set();
  renderAreaConta();
  renderizarVagas(vagasCarregadas);
}

function renderAreaConta() {
  if (!areaConta) return;
  const usuario = obterUsuario();

  if (!usuario || !obterToken()) {
    areaConta.innerHTML = `<button class="btn-login" id="btnEntrar">Entrar</button>`;
    document.getElementById('btnEntrar')?.addEventListener('click', () => abrirModalAuth('login'));
    return;
  }

  areaConta.innerHTML = `
    <a href="perfil.html" class="conta-nome">Olá, ${escapeHtml(usuario.nome.split(' ')[0])}</a>
    <button class="btn-login btn-sair" id="btnSair">Sair</button>
  `;
  document.getElementById('btnSair')?.addEventListener('click', encerrarSessao);
}

function abrirModalAuth(modoInicial) {
  const renderizarCodigoTotp = (email, senha) => {
    abrirModal(`
      <h2>Verificação em duas etapas</h2>
      <p class="modal-subtitulo">Digite o código de 6 dígitos do seu app autenticador.</p>
      <form id="formTotp">
        <label>Código
          <input type="text" name="codigo" inputmode="numeric" pattern="[0-9]{6}" maxlength="6" required autocomplete="one-time-code" autofocus>
        </label>
        <p class="modal-erro" id="totpErro" hidden></p>
        <button type="submit" class="modal-enviar">Confirmar</button>
      </form>
    `);

    document.getElementById('formTotp').addEventListener('submit', async (event) => {
      event.preventDefault();
      const erroEl = document.getElementById('totpErro');
      erroEl.hidden = true;
      const codigo = event.target.codigo.value.trim();

      try {
        const resposta = await fetch(`${API_BASE}/auth/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, senha, codigo_totp: codigo }),
        });
        const dados = await resposta.json();
        if (!resposta.ok) throw new Error(dados.detail || 'Código inválido');

        salvarSessao(dados.access_token, dados.usuario);
        renderAreaConta();
        await carregarFavoritos();
        if (vagasCarregadas.length) renderizarVagas(vagasCarregadas);
        if (typeof aoAutenticar === 'function') aoAutenticar();
        fecharModal();
        mostrarToast(`👋 Bem-vindo(a), ${dados.usuario.nome.split(' ')[0]}!`);
      } catch (erro) {
        erroEl.textContent = erro.message;
        erroEl.hidden = false;
      }
    });
  };

  const renderizar = (modo) => {
    const ehLogin = modo === 'login';
    abrirModal(`
      <div class="auth-tabs" role="tablist">
        <button type="button" class="auth-tab${ehLogin ? ' ativa' : ''}" data-modo="login" role="tab" aria-selected="${ehLogin}">Entrar</button>
        <button type="button" class="auth-tab${ehLogin ? '' : ' ativa'}" data-modo="cadastro" role="tab" aria-selected="${!ehLogin}">Cadastrar</button>
      </div>
      <h2>${ehLogin ? 'Entrar na sua conta' : 'Criar conta gratuita'}</h2>
      <form id="formAuth">
        ${ehLogin ? '' : `
        <label>Nome
          <input type="text" name="nome" required autocomplete="name">
        </label>
        <label>Você é
          <select name="tipo">
            <option value="candidato">Candidato</option>
            <option value="empresa">Empresa</option>
          </select>
        </label>`}
        <label>E-mail
          <input type="email" name="email" required autocomplete="email">
        </label>
        <label>Senha
          <input type="password" name="senha" required minlength="6" autocomplete="${ehLogin ? 'current-password' : 'new-password'}">
        </label>
        <p class="modal-erro" id="authErro" hidden></p>
        <button type="submit" class="modal-enviar">${ehLogin ? 'Entrar' : 'Criar conta'}</button>
      </form>
    `);

    document.querySelectorAll('.auth-tab').forEach((tab) => {
      tab.addEventListener('click', () => renderizar(tab.dataset.modo));
    });

    document.getElementById('formAuth').addEventListener('submit', async (event) => {
      event.preventDefault();
      const form = event.target;
      const erroEl = document.getElementById('authErro');
      erroEl.hidden = true;

      const rota = ehLogin ? 'login' : 'registro';
      const corpo = ehLogin
        ? { email: form.email.value.trim(), senha: form.senha.value }
        : {
            nome: form.nome.value.trim(),
            email: form.email.value.trim(),
            senha: form.senha.value,
            tipo: form.tipo.value,
          };

      try {
        const resposta = await fetch(`${API_BASE}/auth/${rota}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(corpo),
        });
        const dados = await resposta.json();

        if (!resposta.ok) {
          if (resposta.status === 429) throw new Error('Muitas tentativas. Aguarde alguns minutos.');
          throw new Error(dados.detail || 'Não foi possível concluir. Tente novamente.');
        }

        if (dados.requer_totp) {
          renderizarCodigoTotp(corpo.email, corpo.senha);
          return;
        }

        salvarSessao(dados.access_token, dados.usuario);
        renderAreaConta();
        await carregarFavoritos();
        if (vagasCarregadas.length) renderizarVagas(vagasCarregadas);
        if (typeof aoAutenticar === 'function') aoAutenticar();
        fecharModal();
        mostrarToast(`👋 Bem-vindo(a), ${dados.usuario.nome.split(' ')[0]}!`);
      } catch (erro) {
        erroEl.textContent = erro.message;
        erroEl.hidden = false;
      }
    });
  };

  renderizar(modoInicial);
}

async function carregarFavoritos() {
  const token = obterToken();
  if (!token) {
    favoritosIds = new Set();
    return;
  }
  try {
    const resposta = await fetch(`${API_BASE}/favoritos`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!resposta.ok) throw new Error();
    const dados = await resposta.json();
    favoritosIds = new Set((dados.vagas || []).map((v) => Number(v.id)));
  } catch {
    favoritosIds = new Set();
  }
}

async function alternarFavorito(vagaId, botaoEl) {
  if (!obterToken()) {
    abrirModalAuth('login');
    return;
  }

  const id = Number(vagaId);
  const salva = favoritosIds.has(id);
  const metodo = salva ? 'DELETE' : 'POST';

  try {
    const resposta = await fetch(`${API_BASE}/favoritos/${id}`, {
      method: metodo,
      headers: { Authorization: `Bearer ${obterToken()}` },
    });
    if (!resposta.ok) throw new Error();

    if (salva) {
      favoritosIds.delete(id);
    } else {
      favoritosIds.add(id);
    }

    if (botaoEl) {
      botaoEl.classList.toggle('salvo', !salva);
      botaoEl.setAttribute('aria-pressed', String(!salva));
      botaoEl.textContent = !salva ? '★' : '☆';
    }
    mostrarToast(salva ? 'Vaga removida dos salvos' : '⭐ Vaga salva!');
  } catch {
    mostrarToast('Não foi possível atualizar. Tente novamente.');
  }
}

renderAreaConta();
carregarFavoritos().then(() => {
  if (vagasCarregadas.length) renderizarVagas(vagasCarregadas);
});

if (vagasGrid) {
  const estadoNaUrl = new URLSearchParams(window.location.search).get('estado');
  buscarVagas(estadoNaUrl ? { estado: estadoNaUrl } : {});
}
carregarEstatisticas();
carregarStatusAtualizacao();
