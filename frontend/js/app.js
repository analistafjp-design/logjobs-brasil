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

/* ===== Gráficos de barra reutilizáveis (dashboard público, painel de empresa, painel admin) ===== */

const CORES_SERIE = ['--serie-1', '--serie-2', '--serie-3', '--serie-4', '--serie-5', '--serie-6', '--serie-7', '--serie-8'];

function corVar(nome) {
  return `var(${nome})`;
}

function agruparTop(lista, chaveLabel, chaveValor, maximo = 8) {
  const ordenado = [...lista].sort((a, b) => b[chaveValor] - a[chaveValor]);
  if (ordenado.length <= maximo) return ordenado;

  const top = ordenado.slice(0, maximo - 1);
  const resto = ordenado.slice(maximo - 1);
  const somaResto = resto.reduce((acc, item) => acc + item[chaveValor], 0);
  top.push({ [chaveLabel]: 'Outros', [chaveValor]: somaResto });
  return top;
}

function formatarNumero(valor) {
  return Number(valor).toLocaleString('pt-BR');
}

function renderizarBarras(container, dados, chaveLabel, chaveValor, mapaCores, formatador = formatarNumero) {
  if (!container) return;

  if (!dados.length) {
    container.innerHTML = '<p class="dash-carregando">Ainda sem dados suficientes.</p>';
    return;
  }

  const max = Math.max(...dados.map((d) => d[chaveValor]));

  container.innerHTML = dados.map((d) => {
    const pct = max > 0 ? Math.max(2, Math.round((d[chaveValor] / max) * 100)) : 0;
    const cor = mapaCores.get(d[chaveLabel]) || corVar('--texto-suave');
    const rotulo = escapeHtml(d[chaveLabel]);
    return `
      <div class="barra-item">
        <span class="barra-rotulo" title="${rotulo}">${rotulo}</span>
        <div class="barra-trilho"><div class="barra-preenchimento" style="width:${pct}%;background:${cor}"></div></div>
        <span class="barra-valor">${formatador(d[chaveValor])}</span>
      </div>
    `;
  }).join('');
}

function renderizarLegenda(dados, chaveLabel, mapaCores) {
  return dados.map((d) => {
    const cor = mapaCores.get(d[chaveLabel]) || corVar('--texto-suave');
    return `
      <span class="dash-legenda-item">
        <span class="dash-legenda-ponto" style="background:${cor}"></span>
        ${escapeHtml(d[chaveLabel])}
      </span>
    `;
  }).join('');
}

function construirMapaCores(dadosAgrupados, chaveLabel) {
  const mapa = new Map();
  dadosAgrupados.forEach((d, i) => {
    const cor = d[chaveLabel] === 'Outros' ? corVar('--texto-suave') : corVar(CORES_SERIE[i % CORES_SERIE.length]);
    mapa.set(d[chaveLabel], cor);
  });
  return mapa;
}

/* ===== Geolocalização: "vagas perto de mim" =====
   O banco não guarda latitude/longitude por vaga (só cidade/UF em texto), então a
   aproximação possível é por estado: usamos a posição do navegador (Geolocation API,
   só quando o usuário clica e autoriza — nunca automático) e achamos o estado mais
   próximo por distância geodésica até o centróide de cada UF. Sem geocodificação
   nem serviço externo de terceiros — tudo calculado no cliente. */

const NOME_ESTADO = {
  AC: 'Acre', AL: 'Alagoas', AM: 'Amazonas', AP: 'Amapá', BA: 'Bahia', CE: 'Ceará',
  DF: 'Distrito Federal', ES: 'Espírito Santo', GO: 'Goiás', MA: 'Maranhão',
  MG: 'Minas Gerais', MS: 'Mato Grosso do Sul', MT: 'Mato Grosso', PA: 'Pará',
  PB: 'Paraíba', PE: 'Pernambuco', PI: 'Piauí', PR: 'Paraná', RJ: 'Rio de Janeiro',
  RN: 'Rio Grande do Norte', RO: 'Rondônia', RR: 'Roraima', RS: 'Rio Grande do Sul',
  SC: 'Santa Catarina', SE: 'Sergipe', SP: 'São Paulo', TO: 'Tocantins',
};

const LATLNG_ESTADO = {
  AC: [-8.875, -71.85], AL: [-9.27, -36.47], AM: [-2.4, -65.002], AP: [1.41, -52.008],
  BA: [-12.832, -42.198], CE: [-5.377, -39.67], ES: [-19.493, -40.859], GO: [-15.233, -48.87],
  MA: [-4.772, -45.309], MG: [-18.342, -44.991], MS: [-19.941, -55.095], MT: [-14.193, -56.343],
  PA: [-1.679, -52.255], PB: [-7.115, -37.09], PE: [-8.299, -38.214], PI: [-7.068, -43.047],
  PR: [-24.777, -50.943], RJ: [-22.492, -43.264], RN: [-6.043, -37.037], RO: [-10.735, -63.101],
  RR: [2.391, -61.505], RS: [-30.495, -52.732], SC: [-27.333, -50.748], SE: [-10.479, -37.638],
  SP: [-22.464, -47.856], TO: [-10.347, -47.884], DF: [-15.824, -47.702],
};

function distanciaKm([lat1, lng1], [lat2, lng2]) {
  const R = 6371;
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLng = (lng2 - lng1) * Math.PI / 180;
  const a = Math.sin(dLat / 2) ** 2 + Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * Math.sin(dLng / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function estadoMaisProximo(lat, lng) {
  let melhorUf = null;
  let melhorDist = Infinity;
  for (const [uf, coords] of Object.entries(LATLNG_ESTADO)) {
    const d = distanciaKm([lat, lng], coords);
    if (d < melhorDist) { melhorDist = d; melhorUf = uf; }
  }
  return melhorUf;
}

function obterLocalizacaoUsuario() {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) { reject(new Error('Geolocalização não é suportada neste navegador.')); return; }
    navigator.geolocation.getCurrentPosition(
      (posicao) => resolve({ lat: posicao.coords.latitude, lng: posicao.coords.longitude }),
      () => reject(new Error('Não foi possível acessar sua localização. Verifique a permissão do navegador.')),
      { timeout: 8000 }
    );
  });
}

async function localizarEstadoDoUsuario() {
  const { lat, lng } = await obterLocalizacaoUsuario();
  return estadoMaisProximo(lat, lng);
}

document.getElementById('btnVagasPertoDeMim')?.addEventListener('click', async (event) => {
  const botao = event.currentTarget;
  const textoOriginal = botao.textContent;
  botao.disabled = true;
  botao.textContent = '📍 Localizando...';
  try {
    const uf = await localizarEstadoDoUsuario();
    const filtroEstadoEl = document.getElementById('filtroEstado');
    if (filtroEstadoEl) filtroEstadoEl.value = uf;
    if (painelFiltrosAvancados) painelFiltrosAvancados.hidden = false;
    if (btnFiltrosAvancados) btnFiltrosAvancados.setAttribute('aria-expanded', 'true');
    executarBuscaCompleta();
    document.getElementById('vagas')?.scrollIntoView({ behavior: 'smooth' });
    mostrarToast(`📍 Mostrando vagas em ${NOME_ESTADO[uf] || uf}`);
  } catch (erro) {
    mostrarToast(erro.message);
  } finally {
    botao.disabled = false;
    botao.textContent = textoOriginal;
  }
});

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

function botaoCompartilhar(vaga) {
  return `<button class="btn-compartilhar" data-vaga-id="${escapeHtml(vaga.id)}" data-vaga-cargo="${escapeHtml(vaga.cargo)}" data-vaga-empresa="${escapeHtml(vaga.empresa)}" aria-label="Compartilhar vaga" title="Compartilhar vaga">🔗</button>`;
}

async function compartilharVaga(vagaId, cargo, empresa) {
  const url = `${window.location.origin}/vagas/${vagaId}`;
  const dadosCompartilhamento = { title: `${cargo} — ${empresa}`, text: `Vaga de ${cargo} na ${empresa} — LogJobs Brasil`, url };

  if (navigator.share) {
    try {
      await navigator.share(dadosCompartilhamento);
    } catch {
      // Usuário cancelou o compartilhamento — não é um erro a ser tratado.
    }
    return;
  }

  try {
    await navigator.clipboard.writeText(url);
    mostrarToast('🔗 Link da vaga copiado!');
  } catch {
    mostrarToast('Não foi possível copiar o link');
  }
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
          ${botaoCompartilhar(vaga)}
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
    if (!estaAberto) {
      // Painel acabou de abrir: centraliza ele na tela, já que em telas
      // menores ele pode nascer parcialmente fora da área visível.
      requestAnimationFrame(() => {
        painelFiltrosAvancados.scrollIntoView({ behavior: 'smooth', block: 'center' });
      });
    }
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
    <div id="candidaturaChatArea"></div>
  `);

  if (usuarioLogado && usuarioLogado.tipo === 'candidato') {
    fetch(`${API_BASE}/vagas/${vaga.id}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((detalhe) => {
        if (!detalhe || !detalhe.usuario_id) return;
        const area = document.getElementById('candidaturaChatArea');
        if (!area) return;
        area.innerHTML = `<button type="button" class="btn-login" id="btnEnviarMensagemEmpresa" style="margin-top:12px;width:100%;">💬 Enviar mensagem para a empresa</button>`;
        document.getElementById('btnEnviarMensagemEmpresa')?.addEventListener('click', () => abrirModalMensagemVaga(vaga));
      })
      .catch(() => {});
  }

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

function abrirModalMensagemVaga(vaga) {
  abrirModal(`
    <h2>Mensagem para ${escapeHtml(vaga.empresa)}</h2>
    <p class="modal-subtitulo">Sobre a vaga: ${escapeHtml(vaga.cargo)}</p>
    <form id="formMensagemVaga">
      <label>Sua mensagem
        <textarea name="mensagem" rows="4" required maxlength="2000" placeholder="Escreva sua mensagem..."></textarea>
      </label>
      <p class="modal-erro" id="mensagemVagaErro" hidden></p>
      <button type="submit" class="modal-enviar">Enviar</button>
    </form>
  `);

  document.getElementById('formMensagemVaga').addEventListener('submit', async (event) => {
    event.preventDefault();
    const erroEl = document.getElementById('mensagemVagaErro');
    erroEl.hidden = true;
    const mensagem = event.target.mensagem.value.trim();
    if (!mensagem) return;

    try {
      const resposta = await apiFetch(`${API_BASE}/chat/conversas`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ vaga_id: vaga.id, mensagem }),
      });
      const dados = await resposta.json();
      if (!resposta.ok) throw new Error(dados.detail || 'Não foi possível enviar a mensagem.');
      window.location.href = `chat.html?conversa=${dados.conversa_id}`;
    } catch (erro) {
      erroEl.textContent = erro.message;
      erroEl.hidden = false;
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
      return;
    }

    const botaoCompartilharEl = event.target.closest('.btn-compartilhar');
    if (botaoCompartilharEl) {
      compartilharVaga(botaoCompartilharEl.dataset.vagaId, botaoCompartilharEl.dataset.vagaCargo, botaoCompartilharEl.dataset.vagaEmpresa);
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
const CHAVE_REFRESH = 'logjobs-refresh-token';
const CHAVE_USUARIO = 'logjobs-usuario';
const areaConta = document.getElementById('areaConta');
let favoritosIds = new Set();

function obterToken() {
  return localStorage.getItem(CHAVE_TOKEN);
}

function obterRefreshToken() {
  return localStorage.getItem(CHAVE_REFRESH);
}

function obterUsuario() {
  try {
    return JSON.parse(localStorage.getItem(CHAVE_USUARIO) || 'null');
  } catch {
    return null;
  }
}

function salvarSessao(token, usuario, refreshToken) {
  localStorage.setItem(CHAVE_TOKEN, token);
  localStorage.setItem(CHAVE_USUARIO, JSON.stringify(usuario));
  if (refreshToken) localStorage.setItem(CHAVE_REFRESH, refreshToken);
}

// Troca o refresh token guardado por um novo par de tokens (rotação de uso
// único no backend). Usado pelo apiFetch quando um pedido autenticado leva
// 401 — mantém a sessão viva sem exigir login de novo a cada expiração do
// access token.
async function renovarSessao() {
  const refreshToken = obterRefreshToken();
  if (!refreshToken) return false;

  try {
    const resposta = await fetch(`${API_BASE}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!resposta.ok) return false;
    const dados = await resposta.json();
    salvarSessao(dados.access_token, dados.usuario, dados.refresh_token);
    return true;
  } catch {
    return false;
  }
}

// Wrapper de fetch para chamadas autenticadas: anexa o access token e, se a
// resposta vier 401 (token expirado), tenta renovar a sessão uma vez e repete
// o pedido antes de desistir.
async function apiFetch(url, opcoes = {}) {
  const comToken = (token) => ({
    ...opcoes,
    headers: { ...(opcoes.headers || {}), Authorization: `Bearer ${token}` },
  });

  let resposta = await fetch(url, comToken(obterToken()));
  if (resposta.status === 401 && obterRefreshToken()) {
    const renovou = await renovarSessao();
    if (renovou) {
      resposta = await fetch(url, comToken(obterToken()));
    }
  }
  return resposta;
}

function encerrarSessao() {
  const refreshToken = obterRefreshToken();
  if (refreshToken) {
    fetch(`${API_BASE}/auth/logout`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    }).catch(() => {});
  }
  localStorage.removeItem(CHAVE_TOKEN);
  localStorage.removeItem(CHAVE_REFRESH);
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
    <a href="chat.html" class="conta-nome" title="Mensagens" aria-label="Mensagens">💬</a>
    <a href="perfil.html" class="conta-nome">Olá, ${escapeHtml(usuario.nome.split(' ')[0])}</a>
    <button class="btn-login btn-sair" id="btnSair">Sair</button>
  `;
  document.getElementById('btnSair')?.addEventListener('click', encerrarSessao);
}

let googleConfiguradoCache = null;
async function verificarGoogleConfigurado() {
  if (googleConfiguradoCache !== null) return googleConfiguradoCache;
  try {
    const resposta = await fetch(`${API_BASE}/auth/google/configurado`);
    const dados = await resposta.json();
    googleConfiguradoCache = Boolean(dados.configurado);
  } catch {
    googleConfiguradoCache = false;
  }
  return googleConfiguradoCache;
}

let recuperarSenhaConfiguradaCache = null;
async function verificarRecuperarSenhaConfigurada() {
  if (recuperarSenhaConfiguradaCache !== null) return recuperarSenhaConfiguradaCache;
  try {
    const resposta = await fetch(`${API_BASE}/auth/recuperar-senha/configurado`);
    const dados = await resposta.json();
    recuperarSenhaConfiguradaCache = Boolean(dados.configurado);
  } catch {
    recuperarSenhaConfiguradaCache = false;
  }
  return recuperarSenhaConfiguradaCache;
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

        salvarSessao(dados.access_token, dados.usuario, dados.refresh_token);
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
        ${ehLogin ? '<button type="button" class="link-esqueci-senha" id="btnEsqueciSenha" hidden>Esqueci minha senha</button>' : ''}
        <p class="modal-erro" id="authErro" hidden></p>
        <button type="submit" class="modal-enviar">${ehLogin ? 'Entrar' : 'Criar conta'}</button>
      </form>
      <div class="auth-divisor" id="authDivisorGoogle" hidden><span>ou</span></div>
      <a class="btn-google" id="btnLoginGoogle" href="${API_BASE}/auth/google/login" hidden>
        <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true"><path fill="#4285F4" d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.72v2.26h2.92c1.7-1.57 2.68-3.88 2.68-6.62z"/><path fill="#34A853" d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.92-2.26c-.81.54-1.85.86-3.04.86-2.34 0-4.32-1.58-5.03-3.7H.97v2.33A9 9 0 0 0 9 18z"/><path fill="#FBBC05" d="M3.97 10.72A5.4 5.4 0 0 1 3.68 9c0-.6.1-1.18.29-1.72V4.95H.97A9 9 0 0 0 0 9c0 1.45.35 2.83.97 4.05l3-2.33z"/><path fill="#EA4335" d="M9 3.58c1.32 0 2.5.45 3.44 1.35l2.58-2.58C13.46.89 11.43 0 9 0A9 9 0 0 0 .97 4.95l3 2.33C4.68 5.16 6.66 3.58 9 3.58z"/></svg>
        Continuar com Google
      </a>
    `);

    verificarGoogleConfigurado().then((configurado) => {
      if (!configurado) return;
      document.getElementById('authDivisorGoogle').hidden = false;
      document.getElementById('btnLoginGoogle').hidden = false;
    });

    if (ehLogin) {
      verificarRecuperarSenhaConfigurada().then((configurado) => {
        const botao = document.getElementById('btnEsqueciSenha');
        if (botao) botao.hidden = !configurado;
      });
      document.getElementById('btnEsqueciSenha')?.addEventListener('click', () => abrirModalRecuperarSenha());
    }

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

        salvarSessao(dados.access_token, dados.usuario, dados.refresh_token);
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

function abrirModalRecuperarSenha() {
  abrirModal(`
    <h2>Recuperar senha</h2>
    <p class="modal-subtitulo">Digite seu e-mail e enviaremos um link para você escolher uma nova senha.</p>
    <form id="formRecuperarSenha">
      <label>E-mail
        <input type="email" name="email" required autocomplete="email">
      </label>
      <p class="modal-erro" id="recuperarSenhaErro" hidden></p>
      <button type="submit" class="modal-enviar">Enviar link</button>
    </form>
  `);

  document.getElementById('formRecuperarSenha').addEventListener('submit', async (event) => {
    event.preventDefault();
    const erroEl = document.getElementById('recuperarSenhaErro');
    erroEl.hidden = true;
    const email = event.target.email.value.trim();

    try {
      const resposta = await fetch(`${API_BASE}/auth/recuperar-senha`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      });
      const dados = await resposta.json();

      if (!resposta.ok) {
        if (resposta.status === 429) throw new Error('Muitas tentativas. Aguarde alguns minutos.');
        throw new Error(dados.detail || 'Não foi possível enviar o link agora. Tente novamente.');
      }

      abrirModal(`
        <div class="modal-sucesso">
          <div class="icone">📧</div>
          <h2>Verifique seu e-mail</h2>
          <p class="modal-subtitulo">${escapeHtml(dados.mensagem)}</p>
        </div>
      `);
    } catch (erro) {
      erroEl.textContent = erro.message;
      erroEl.hidden = false;
    }
  });
}

async function carregarFavoritos() {
  const token = obterToken();
  if (!token) {
    favoritosIds = new Set();
    return;
  }
  try {
    const resposta = await apiFetch(`${API_BASE}/favoritos`);
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
    const resposta = await apiFetch(`${API_BASE}/favoritos/${id}`, { method: metodo });
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

/* ===== Assistente virtual (central de ajuda por palavras-chave, sem IA generativa) =====
   Disponível em todas as páginas (widget flutuante), não exige login. */

function criarWidgetAssistente() {
  const botao = document.createElement('button');
  botao.type = 'button';
  botao.className = 'assistente-botao';
  botao.setAttribute('aria-label', 'Assistente virtual');
  botao.textContent = '💬';
  document.body.appendChild(botao);

  const painel = document.createElement('div');
  painel.className = 'assistente-painel';
  painel.hidden = true;
  painel.innerHTML = `
    <div class="assistente-cabecalho">
      <span>🤖 Central de ajuda</span>
      <button type="button" class="assistente-fechar" aria-label="Fechar">&times;</button>
    </div>
    <div class="assistente-mensagens" id="assistenteMensagens">
      <div class="assistente-bolha">Olá! Sou a central de ajuda do LogJobs. Pergunte sobre candidaturas, perfil, chat, 2FA e mais.</div>
    </div>
    <div class="assistente-sugestoes" id="assistenteSugestoes">
      <button type="button">Como me candidato a uma vaga?</button>
      <button type="button">Esqueci minha senha</button>
      <button type="button">Como criar meu currículo?</button>
      <button type="button">Como excluir minha conta?</button>
      <button type="button">Como a empresa publica uma vaga?</button>
    </div>
    <form class="assistente-form" id="assistenteForm">
      <input type="text" name="pergunta" placeholder="Digite sua dúvida..." maxlength="500" autocomplete="off" required>
      <button type="submit">Enviar</button>
    </form>
  `;
  document.body.appendChild(painel);

  botao.addEventListener('click', () => {
    painel.hidden = !painel.hidden;
    if (!painel.hidden) painel.querySelector('input[name="pergunta"]')?.focus();
  });
  painel.querySelector('.assistente-fechar').addEventListener('click', () => {
    painel.hidden = true;
  });

  const mensagensEl = painel.querySelector('#assistenteMensagens');
  const sugestoesEl = painel.querySelector('#assistenteSugestoes');

  async function perguntarAssistente(pergunta) {
    sugestoesEl.hidden = true;
    mensagensEl.insertAdjacentHTML('beforeend', `<div class="assistente-bolha assistente-bolha-usuario">${escapeHtml(pergunta)}</div>`);
    mensagensEl.scrollTop = mensagensEl.scrollHeight;

    try {
      const resposta = await fetch(`${API_BASE}/ia/assistente`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pergunta }),
      });
      const dados = await resposta.json();
      const texto = resposta.ok ? dados.resposta : 'Não foi possível responder agora. Tente novamente em instantes.';
      mensagensEl.insertAdjacentHTML('beforeend', `<div class="assistente-bolha">${escapeHtml(texto)}</div>`);
    } catch {
      mensagensEl.insertAdjacentHTML('beforeend', '<div class="assistente-bolha">Não foi possível responder agora. Tente novamente em instantes.</div>');
    }
    mensagensEl.scrollTop = mensagensEl.scrollHeight;
  }

  sugestoesEl.addEventListener('click', (evento) => {
    const botaoSugestao = evento.target.closest('button');
    if (botaoSugestao) perguntarAssistente(botaoSugestao.textContent);
  });

  painel.querySelector('#assistenteForm').addEventListener('submit', (evento) => {
    evento.preventDefault();
    const form = evento.target;
    const pergunta = form.pergunta.value.trim();
    if (!pergunta) return;
    form.pergunta.value = '';
    perguntarAssistente(pergunta);
  });
}

criarWidgetAssistente();

/* ===== Banner de convite para criar conta =====
   Discreto, some ao fechar (não repete na mesma aba/sessão) e nunca aparece
   para quem já está logado. Some sozinho depois de alguns segundos de
   navegação anônima — nunca bloqueia a tela nem interrompe nada. */

function criarBannerCTA() {
  if (obterUsuario()) return;
  if (sessionStorage.getItem('logjobs-cta-dispensado')) return;

  setTimeout(() => {
    if (obterUsuario()) return;

    const banner = document.createElement('div');
    banner.className = 'cta-banner';
    banner.innerHTML = `
      <button type="button" class="cta-banner-fechar" aria-label="Fechar">&times;</button>
      <p class="cta-banner-titulo">🎯 Não perca nenhuma vaga</p>
      <p class="cta-banner-texto">Crie uma conta grátis para salvar vagas e receber alertas de novas oportunidades.</p>
      <button type="button" class="cta-banner-botao">Criar conta grátis</button>
    `;
    document.body.appendChild(banner);
    requestAnimationFrame(() => banner.classList.add('cta-banner-visivel'));

    const fechar = () => {
      sessionStorage.setItem('logjobs-cta-dispensado', '1');
      banner.classList.remove('cta-banner-visivel');
      setTimeout(() => banner.remove(), 300);
    };

    banner.querySelector('.cta-banner-fechar').addEventListener('click', fechar);
    banner.querySelector('.cta-banner-botao').addEventListener('click', () => {
      fechar();
      abrirModalAuth('cadastro');
    });
  }, 10000);
}

criarBannerCTA();
