const API_BASE = '/api';
const CHAVE_TOKEN_ADMIN = 'logjobs-admin-token';

function escapeHtml(valor) {
  const texto = valor === null || valor === undefined ? '' : String(valor);
  return texto.replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[c]));
}

/* ===== Toast ===== */
const toast = document.getElementById('toast');
let toastTimeout;
function mostrarToast(texto) {
  if (!toast) return;
  toast.textContent = texto;
  toast.hidden = false;
  clearTimeout(toastTimeout);
  toastTimeout = setTimeout(() => { toast.hidden = true; }, 3500);
}

/* ===== Token / sessão ===== */

function obterTokenAdmin() {
  return sessionStorage.getItem(CHAVE_TOKEN_ADMIN);
}

async function chamarAdmin(path, opcoes = {}) {
  const resposta = await fetch(`${API_BASE}${path}`, {
    ...opcoes,
    headers: {
      ...(opcoes.headers || {}),
      'X-Admin-Token': obterTokenAdmin() || '',
    },
  });
  if (resposta.status === 403) {
    sessionStorage.removeItem(CHAVE_TOKEN_ADMIN);
    mostrarBloqueio('Sessão expirada ou token inválido. Entre novamente.');
    throw new Error('Acesso negado');
  }
  return resposta;
}

const adminBloqueado = document.getElementById('adminBloqueado');
const adminConteudo = document.getElementById('adminConteudo');

function mostrarBloqueio(mensagemErro) {
  adminBloqueado.hidden = false;
  adminConteudo.hidden = true;
  const erroEl = document.getElementById('adminTokenErro');
  if (mensagemErro) {
    erroEl.textContent = mensagemErro;
    erroEl.hidden = false;
  }
}

function mostrarConteudo() {
  adminBloqueado.hidden = true;
  adminConteudo.hidden = false;
}

document.getElementById('formAdminToken').addEventListener('submit', async (event) => {
  event.preventDefault();
  const token = event.target.token.value.trim();
  const erroEl = document.getElementById('adminTokenErro');
  erroEl.hidden = true;

  sessionStorage.setItem(CHAVE_TOKEN_ADMIN, token);
  try {
    const resposta = await fetch(`${API_BASE}/admin/verificar`, { headers: { 'X-Admin-Token': token } });
    if (!resposta.ok) throw new Error();
    mostrarConteudo();
    iniciarPainel();
  } catch {
    sessionStorage.removeItem(CHAVE_TOKEN_ADMIN);
    erroEl.textContent = 'Token inválido.';
    erroEl.hidden = false;
  }
});

document.getElementById('btnSairAdmin').addEventListener('click', () => {
  sessionStorage.removeItem(CHAVE_TOKEN_ADMIN);
  mostrarBloqueio();
});

/* ===== Abas ===== */

document.querySelectorAll('.admin-tab').forEach((tab) => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.admin-tab').forEach((t) => t.classList.remove('ativa'));
    tab.classList.add('ativa');
    document.querySelectorAll('.admin-secao').forEach((s) => { s.hidden = true; });
    const secao = document.getElementById(`secao${tab.dataset.aba.charAt(0).toUpperCase()}${tab.dataset.aba.slice(1)}`);
    if (secao) secao.hidden = false;

    if (tab.dataset.aba === 'candidaturas') carregarCandidaturas();
    if (tab.dataset.aba === 'interessados') carregarInteressados();
    if (tab.dataset.aba === 'usuarios') carregarUsuarios();
  });
});

/* ===== Vagas ===== */

let vagasAdmin = [];

function formatarSalarioAdmin(valor) {
  if (!valor) return '—';
  return `R$ ${Number(valor).toLocaleString('pt-BR')}`;
}

function linhaVaga(vaga) {
  return `
    <tr data-vaga-id="${vaga.id}">
      <td>${escapeHtml(vaga.cargo)}</td>
      <td>${escapeHtml(vaga.empresa)}</td>
      <td>${escapeHtml(vaga.cidade)}/${escapeHtml(vaga.estado)}</td>
      <td>${escapeHtml(vaga.categoria)}</td>
      <td>${formatarSalarioAdmin(vaga.salario)}</td>
      <td>${escapeHtml(vaga.fonte)}</td>
      <td>
        <button class="admin-acao-btn editar" data-id="${vaga.id}">Editar</button>
        <button class="admin-acao-btn excluir" data-id="${vaga.id}">Excluir</button>
      </td>
    </tr>
  `;
}

async function carregarVagas(busca = '') {
  const tbody = document.querySelector('#tabelaVagas tbody');
  tbody.innerHTML = '<tr><td colspan="7">Carregando...</td></tr>';
  try {
    const query = busca ? `?q=${encodeURIComponent(busca)}` : '';
    const resposta = await chamarAdmin(`/admin/vagas${query}`);
    const dados = await resposta.json();
    vagasAdmin = dados.vagas || [];
    tbody.innerHTML = vagasAdmin.length
      ? vagasAdmin.map(linhaVaga).join('')
      : '<tr><td colspan="7">Nenhuma vaga encontrada.</td></tr>';
  } catch (erro) {
    tbody.innerHTML = '<tr><td colspan="7">Não foi possível carregar as vagas.</td></tr>';
  }
}

let buscaTimeout;
document.getElementById('buscaVagas').addEventListener('input', (event) => {
  clearTimeout(buscaTimeout);
  buscaTimeout = setTimeout(() => carregarVagas(event.target.value.trim()), 350);
});

const formVaga = document.getElementById('formVaga');
const btnNovaVaga = document.getElementById('btnNovaVaga');
const btnCancelarVaga = document.getElementById('btnCancelarVaga');

function abrirFormNovaVaga() {
  formVaga.reset();
  formVaga.id.value = '';
  document.getElementById('formVagaTitulo').textContent = 'Nova vaga';
  formVaga.hidden = false;
  formVaga.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function abrirFormEditarVaga(vaga) {
  formVaga.reset();
  formVaga.id.value = vaga.id;
  formVaga.cargo.value = vaga.cargo || '';
  formVaga.empresa.value = vaga.empresa || '';
  formVaga.cidade.value = vaga.cidade || '';
  formVaga.estado.value = vaga.estado || '';
  formVaga.categoria.value = vaga.categoria || '';
  formVaga.salario.value = vaga.salario || '';
  formVaga.modalidade.value = vaga.modalidade || '';
  formVaga.turno.value = vaga.turno || '';
  formVaga.tipo_contratacao.value = vaga.tipo_contratacao || '';
  formVaga.veiculo.value = vaga.veiculo || '';
  formVaga.link.value = vaga.link || '';
  formVaga.descricao.value = vaga.descricao || '';
  formVaga.beneficios.value = vaga.beneficios || '';
  formVaga.requisitos.value = vaga.requisitos || '';
  document.getElementById('formVagaTitulo').textContent = `Editar: ${vaga.cargo}`;
  formVaga.hidden = false;
  formVaga.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

btnNovaVaga.addEventListener('click', abrirFormNovaVaga);
btnCancelarVaga.addEventListener('click', () => { formVaga.hidden = true; });

formVaga.addEventListener('submit', async (event) => {
  event.preventDefault();
  const erroEl = document.getElementById('formVagaErro');
  erroEl.hidden = true;

  const id = formVaga.id.value;
  const corpo = {
    cargo: formVaga.cargo.value.trim(),
    empresa: formVaga.empresa.value.trim(),
    cidade: formVaga.cidade.value.trim(),
    estado: formVaga.estado.value.trim().toUpperCase(),
    categoria: formVaga.categoria.value.trim(),
    salario: formVaga.salario.value ? Number(formVaga.salario.value) : null,
    modalidade: formVaga.modalidade.value || null,
    turno: formVaga.turno.value || null,
    tipo_contratacao: formVaga.tipo_contratacao.value || null,
    veiculo: formVaga.veiculo.value.trim() || null,
    link: formVaga.link.value.trim() || null,
    descricao: formVaga.descricao.value.trim() || null,
    beneficios: formVaga.beneficios.value.trim() || null,
    requisitos: formVaga.requisitos.value.trim() || null,
  };

  try {
    const resposta = await chamarAdmin(id ? `/admin/vagas/${id}` : '/admin/vagas', {
      method: id ? 'PATCH' : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(corpo),
    });
    const dados = await resposta.json();
    if (!resposta.ok) throw new Error(dados.detail || 'Não foi possível salvar a vaga');

    formVaga.hidden = true;
    mostrarToast(id ? '✅ Vaga atualizada' : '✅ Vaga criada');
    carregarVagas(document.getElementById('buscaVagas').value.trim());
  } catch (erro) {
    erroEl.textContent = erro.message;
    erroEl.hidden = false;
  }
});

document.querySelector('#tabelaVagas tbody').addEventListener('click', async (event) => {
  const id = event.target.dataset.id;
  if (!id) return;

  if (event.target.classList.contains('editar')) {
    const vaga = vagasAdmin.find((v) => String(v.id) === id);
    if (vaga) abrirFormEditarVaga(vaga);
    return;
  }

  if (event.target.classList.contains('excluir')) {
    if (!confirm('Tem certeza que deseja excluir esta vaga?')) return;
    try {
      const resposta = await chamarAdmin(`/admin/vagas/${id}`, { method: 'DELETE' });
      if (!resposta.ok) throw new Error();
      mostrarToast('🗑️ Vaga excluída');
      carregarVagas(document.getElementById('buscaVagas').value.trim());
    } catch {
      mostrarToast('Não foi possível excluir a vaga.');
    }
  }
});

/* ===== Candidaturas / Interessados / Usuários (somente leitura) ===== */

function formatarData(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('pt-BR');
}

async function carregarCandidaturas() {
  const tbody = document.getElementById('tabelaCandidaturas');
  try {
    const resposta = await chamarAdmin('/admin/candidaturas');
    const dados = await resposta.json();
    tbody.innerHTML = dados.length ? dados.map((c) => `
      <tr>
        <td>${escapeHtml(c.nome)}</td>
        <td>${escapeHtml(c.email)}</td>
        <td>${escapeHtml(c.telefone || '—')}</td>
        <td>${escapeHtml(c.vaga_cargo || '—')}${c.vaga_empresa ? ' · ' + escapeHtml(c.vaga_empresa) : ''}</td>
        <td>${formatarData(c.criada_em)}</td>
      </tr>
    `).join('') : '<tr><td colspan="5">Nenhuma candidatura ainda.</td></tr>';
  } catch {
    tbody.innerHTML = '<tr><td colspan="5">Não foi possível carregar.</td></tr>';
  }
}

async function carregarInteressados() {
  const tbody = document.getElementById('tabelaInteressados');
  try {
    const resposta = await chamarAdmin('/admin/interessados');
    const dados = await resposta.json();
    tbody.innerHTML = dados.length ? dados.map((i) => `
      <tr>
        <td>${escapeHtml(i.nome)}</td>
        <td>${escapeHtml(i.email)}</td>
        <td>${escapeHtml(i.tipo)}</td>
        <td>${formatarData(i.criado_em)}</td>
      </tr>
    `).join('') : '<tr><td colspan="4">Ninguém na lista de espera ainda.</td></tr>';
  } catch {
    tbody.innerHTML = '<tr><td colspan="4">Não foi possível carregar.</td></tr>';
  }
}

async function carregarUsuarios() {
  const tbody = document.getElementById('tabelaUsuarios');
  try {
    const resposta = await chamarAdmin('/admin/usuarios');
    const dados = await resposta.json();
    tbody.innerHTML = dados.length ? dados.map((u) => `
      <tr>
        <td>${escapeHtml(u.nome)}</td>
        <td>${escapeHtml(u.email)}</td>
        <td>${escapeHtml(u.tipo)}</td>
        <td>${escapeHtml(u.cidade || '—')}</td>
        <td>${formatarData(u.criado_em)}</td>
      </tr>
    `).join('') : '<tr><td colspan="5">Nenhum usuário cadastrado ainda.</td></tr>';
  } catch {
    tbody.innerHTML = '<tr><td colspan="5">Não foi possível carregar.</td></tr>';
  }
}

/* ===== Inicialização ===== */

function iniciarPainel() {
  carregarVagas();
}

(async function iniciar() {
  const token = obterTokenAdmin();
  if (!token) {
    mostrarBloqueio();
    return;
  }
  try {
    const resposta = await fetch(`${API_BASE}/admin/verificar`, { headers: { 'X-Admin-Token': token } });
    if (!resposta.ok) throw new Error();
    mostrarConteudo();
    iniciarPainel();
  } catch {
    sessionStorage.removeItem(CHAVE_TOKEN_ADMIN);
    mostrarBloqueio();
  }
})();
