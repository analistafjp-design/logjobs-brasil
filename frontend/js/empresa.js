const empresaBloqueado = document.getElementById('empresaBloqueado');
const empresaConteudo = document.getElementById('empresaConteudo');

document.getElementById('btnEntrarEmpresa')?.addEventListener('click', () => abrirModalAuth('login'));
document.getElementById('btnCadastrarEmpresa')?.addEventListener('click', () => abrirModalAuth('cadastro'));

let vagasEmpresa = [];

function formatarSalarioEmpresa(valor) {
  if (!valor) return '—';
  return `R$ ${Number(valor).toLocaleString('pt-BR')}`;
}

async function iniciarEmpresa() {
  const token = obterToken();
  const usuarioLocal = obterUsuario();

  if (!token || !usuarioLocal) {
    empresaBloqueado.hidden = false;
    empresaConteudo.hidden = true;
    return;
  }

  let usuario;
  try {
    const resposta = await fetch(`${API_BASE}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!resposta.ok) throw new Error();
    usuario = await resposta.json();
  } catch {
    encerrarSessao();
    empresaBloqueado.hidden = false;
    empresaConteudo.hidden = true;
    return;
  }

  if (usuario.tipo !== 'empresa') {
    document.getElementById('empresaBloqueadoTexto').textContent =
      'Este painel é exclusivo para contas de empresa. Sua conta atual é de candidato.';
    document.getElementById('btnCadastrarEmpresa').hidden = false;
    empresaBloqueado.hidden = false;
    empresaConteudo.hidden = true;
    return;
  }

  empresaBloqueado.hidden = true;
  empresaConteudo.hidden = false;
  carregarEstatisticasEmpresa();
  carregarVagasEmpresa();
}

async function carregarEstatisticasEmpresa() {
  try {
    const resposta = await fetch(`${API_BASE}/empresa/estatisticas`, {
      headers: { Authorization: `Bearer ${obterToken()}` },
    });
    const dados = await resposta.json();
    document.getElementById('empresaStatVagas').textContent = dados.total_vagas ?? '—';
    document.getElementById('empresaStatCandidaturas').textContent = dados.total_candidaturas ?? '—';
  } catch {
    // estatísticas são um extra visual — falha silenciosa não impede o resto do painel
  }
}

function linhaVagaEmpresa(vaga) {
  return `
    <tr data-vaga-id="${vaga.id}">
      <td>${escapeHtml(vaga.cargo)}</td>
      <td>${escapeHtml(vaga.cidade)}/${escapeHtml(vaga.estado)}</td>
      <td>${escapeHtml(vaga.categoria)}</td>
      <td>${formatarSalarioEmpresa(vaga.salario)}</td>
      <td>${vaga.total_candidaturas ?? 0}</td>
      <td>
        <button class="admin-acao-btn editar" data-acao="candidaturas" data-id="${vaga.id}">Candidaturas</button>
        <button class="admin-acao-btn editar" data-acao="editar" data-id="${vaga.id}">Editar</button>
        <button class="admin-acao-btn excluir" data-acao="excluir" data-id="${vaga.id}">Excluir</button>
      </td>
    </tr>
  `;
}

async function carregarVagasEmpresa() {
  const tbody = document.querySelector('#tabelaVagasEmpresa tbody');
  tbody.innerHTML = '<tr><td colspan="6">Carregando...</td></tr>';
  try {
    const resposta = await fetch(`${API_BASE}/empresa/vagas`, {
      headers: { Authorization: `Bearer ${obterToken()}` },
    });
    if (!resposta.ok) throw new Error();
    vagasEmpresa = await resposta.json();
    tbody.innerHTML = vagasEmpresa.length
      ? vagasEmpresa.map(linhaVagaEmpresa).join('')
      : '<tr><td colspan="6">Você ainda não publicou nenhuma vaga.</td></tr>';
  } catch {
    tbody.innerHTML = '<tr><td colspan="6">Não foi possível carregar suas vagas.</td></tr>';
  }
}

const formVagaEmpresa = document.getElementById('formVagaEmpresa');
const btnNovaVagaEmpresa = document.getElementById('btnNovaVagaEmpresa');
const btnCancelarVagaEmpresa = document.getElementById('btnCancelarVagaEmpresa');

function abrirFormNovaVagaEmpresa() {
  formVagaEmpresa.reset();
  formVagaEmpresa.id.value = '';
  const usuario = obterUsuario();
  if (usuario?.nome) formVagaEmpresa.empresa.value = usuario.nome;
  document.getElementById('formVagaEmpresaTitulo').textContent = 'Nova vaga';
  formVagaEmpresa.hidden = false;
  formVagaEmpresa.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function abrirFormEditarVagaEmpresa(vaga) {
  formVagaEmpresa.reset();
  formVagaEmpresa.id.value = vaga.id;
  formVagaEmpresa.cargo.value = vaga.cargo || '';
  formVagaEmpresa.empresa.value = vaga.empresa || '';
  formVagaEmpresa.cidade.value = vaga.cidade || '';
  formVagaEmpresa.estado.value = vaga.estado || '';
  formVagaEmpresa.categoria.value = vaga.categoria || '';
  formVagaEmpresa.salario.value = vaga.salario || '';
  formVagaEmpresa.modalidade.value = vaga.modalidade || '';
  formVagaEmpresa.turno.value = vaga.turno || '';
  formVagaEmpresa.tipo_contratacao.value = vaga.tipo_contratacao || '';
  formVagaEmpresa.veiculo.value = vaga.veiculo || '';
  formVagaEmpresa.descricao.value = vaga.descricao || '';
  formVagaEmpresa.beneficios.value = vaga.beneficios || '';
  formVagaEmpresa.requisitos.value = vaga.requisitos || '';
  document.getElementById('formVagaEmpresaTitulo').textContent = `Editar: ${vaga.cargo}`;
  formVagaEmpresa.hidden = false;
  formVagaEmpresa.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

btnNovaVagaEmpresa.addEventListener('click', abrirFormNovaVagaEmpresa);
btnCancelarVagaEmpresa.addEventListener('click', () => { formVagaEmpresa.hidden = true; });

formVagaEmpresa.addEventListener('submit', async (event) => {
  event.preventDefault();
  const erroEl = document.getElementById('formVagaEmpresaErro');
  erroEl.hidden = true;

  const id = formVagaEmpresa.id.value;
  const corpo = {
    cargo: formVagaEmpresa.cargo.value.trim(),
    empresa: formVagaEmpresa.empresa.value.trim(),
    cidade: formVagaEmpresa.cidade.value.trim(),
    estado: formVagaEmpresa.estado.value.trim().toUpperCase(),
    categoria: formVagaEmpresa.categoria.value.trim(),
    salario: formVagaEmpresa.salario.value ? Number(formVagaEmpresa.salario.value) : null,
    modalidade: formVagaEmpresa.modalidade.value || null,
    turno: formVagaEmpresa.turno.value || null,
    tipo_contratacao: formVagaEmpresa.tipo_contratacao.value || null,
    veiculo: formVagaEmpresa.veiculo.value.trim() || null,
    descricao: formVagaEmpresa.descricao.value.trim() || null,
    beneficios: formVagaEmpresa.beneficios.value.trim() || null,
    requisitos: formVagaEmpresa.requisitos.value.trim() || null,
  };

  try {
    const resposta = await fetch(`${API_BASE}/empresa/vagas${id ? `/${id}` : ''}`, {
      method: id ? 'PATCH' : 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${obterToken()}`,
      },
      body: JSON.stringify(corpo),
    });
    const dados = await resposta.json();
    if (!resposta.ok) throw new Error(dados.detail || 'Não foi possível salvar a vaga');

    formVagaEmpresa.hidden = true;
    mostrarToast(id ? '✅ Vaga atualizada' : '✅ Vaga publicada');
    carregarVagasEmpresa();
    carregarEstatisticasEmpresa();
  } catch (erro) {
    erroEl.textContent = erro.message;
    erroEl.hidden = false;
  }
});

const secaoCandidaturasVaga = document.getElementById('secaoCandidaturasVaga');

async function abrirCandidaturasVaga(vaga) {
  document.getElementById('candidaturasVagaTitulo').textContent = `Candidaturas — ${vaga.cargo}`;
  secaoCandidaturasVaga.hidden = false;
  secaoCandidaturasVaga.scrollIntoView({ behavior: 'smooth', block: 'center' });
  const tbody = document.getElementById('tabelaCandidaturasVaga');
  tbody.innerHTML = '<tr><td colspan="4">Carregando...</td></tr>';
  try {
    const resposta = await fetch(`${API_BASE}/empresa/candidaturas/${vaga.id}`, {
      headers: { Authorization: `Bearer ${obterToken()}` },
    });
    if (!resposta.ok) throw new Error();
    const candidaturas = await resposta.json();
    tbody.innerHTML = candidaturas.length ? candidaturas.map((c) => `
      <tr>
        <td>${escapeHtml(c.nome)}</td>
        <td>${escapeHtml(c.email)}</td>
        <td>${escapeHtml(c.telefone || '—')}</td>
        <td>${c.criada_em ? new Date(c.criada_em).toLocaleString('pt-BR') : '—'}</td>
      </tr>
    `).join('') : '<tr><td colspan="4">Nenhuma candidatura recebida ainda.</td></tr>';
  } catch {
    tbody.innerHTML = '<tr><td colspan="4">Não foi possível carregar as candidaturas.</td></tr>';
  }
}

document.getElementById('btnFecharCandidaturasVaga').addEventListener('click', () => {
  secaoCandidaturasVaga.hidden = true;
});

document.querySelector('#tabelaVagasEmpresa tbody').addEventListener('click', async (event) => {
  const botao = event.target.closest('[data-id]');
  if (!botao) return;
  const vaga = vagasEmpresa.find((v) => String(v.id) === botao.dataset.id);
  if (!vaga) return;

  if (botao.dataset.acao === 'editar') {
    abrirFormEditarVagaEmpresa(vaga);
  } else if (botao.dataset.acao === 'candidaturas') {
    abrirCandidaturasVaga(vaga);
  } else if (botao.dataset.acao === 'excluir') {
    if (!confirm('Tem certeza que deseja excluir esta vaga?')) return;
    try {
      const resposta = await fetch(`${API_BASE}/empresa/vagas/${vaga.id}`, {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${obterToken()}` },
      });
      if (!resposta.ok) throw new Error();
      mostrarToast('🗑️ Vaga excluída');
      carregarVagasEmpresa();
      carregarEstatisticasEmpresa();
    } catch {
      mostrarToast('Não foi possível excluir a vaga.');
    }
  }
});

function aoAutenticar() {
  iniciarEmpresa();
}

renderAreaConta();
iniciarEmpresa();
