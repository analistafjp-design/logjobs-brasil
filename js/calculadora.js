let dadosSalarios = [];

function formatarMoeda(valor) {
  return `R$ ${Number(valor).toLocaleString('pt-BR', { maximumFractionDigits: 0 })}`;
}

async function carregarSalarios() {
  const tbody = document.querySelector('#tabelaSalarios tbody');
  try {
    const resposta = await fetch('/api/salarios');
    dadosSalarios = await resposta.json();

    if (!dadosSalarios.length) {
      tbody.innerHTML = '<tr><td colspan="5">Nenhuma vaga com salário informado ainda.</td></tr>';
      return;
    }

    tbody.innerHTML = dadosSalarios.map((d) => `
      <tr>
        <td>${escapeHtml(d.categoria)}</td>
        <td>${formatarMoeda(d.minimo)}</td>
        <td><strong>${formatarMoeda(d.media)}</strong></td>
        <td>${formatarMoeda(d.maximo)}</td>
        <td>${d.total}</td>
      </tr>
    `).join('');

    popularSeletores();
  } catch (erro) {
    tbody.innerHTML = '<tr><td colspan="5">Não foi possível carregar os dados salariais.</td></tr>';
    console.error(erro);
  }
}

function popularSeletores() {
  const opcoes = dadosSalarios.map((d) => `<option value="${escapeHtml(d.categoria)}">${escapeHtml(d.categoria)}</option>`).join('');
  document.getElementById('seletorA').insertAdjacentHTML('beforeend', opcoes);
  document.getElementById('seletorB').insertAdjacentHTML('beforeend', opcoes);
}

function cartaoCategoria(categoria) {
  const dados = dadosSalarios.find((d) => d.categoria === categoria);
  if (!dados) return '';
  return `
    <div class="comparador-card">
      <h3>${escapeHtml(dados.categoria)}</h3>
      <div class="comparador-linha"><span>Mínimo</span><span>${formatarMoeda(dados.minimo)}</span></div>
      <div class="comparador-linha"><span>Média</span><strong>${formatarMoeda(dados.media)}</strong></div>
      <div class="comparador-linha"><span>Máximo</span><span>${formatarMoeda(dados.maximo)}</span></div>
      <div class="comparador-linha"><span>Vagas com salário</span><span>${dados.total}</span></div>
    </div>
  `;
}

function atualizarComparador() {
  const a = document.getElementById('seletorA').value;
  const b = document.getElementById('seletorB').value;
  const container = document.getElementById('comparadorResultado');

  if (!a && !b) {
    container.innerHTML = '<p class="dash-carregando">Selecione ao menos uma categoria para ver a faixa salarial.</p>';
    return;
  }

  container.innerHTML = [a, b].filter(Boolean).map(cartaoCategoria).join('');
}

document.getElementById('seletorA').addEventListener('change', atualizarComparador);
document.getElementById('seletorB').addEventListener('change', atualizarComparador);

atualizarComparador();
carregarSalarios();
