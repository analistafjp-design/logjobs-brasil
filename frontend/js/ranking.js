function formatarSalarioRanking(valor) {
  return `R$ ${Number(valor).toLocaleString('pt-BR', { maximumFractionDigits: 0 })}`;
}

function renderizarRankingBarras(container, dados, chaveValor, cor, formatador) {
  if (!container) return;

  if (!dados.length) {
    container.innerHTML = '<p class="dash-carregando">Ainda sem dados suficientes.</p>';
    return;
  }

  const max = Math.max(...dados.map((d) => d[chaveValor]));

  container.innerHTML = dados.map((d, indice) => {
    const pct = max > 0 ? Math.max(2, Math.round((d[chaveValor] / max) * 100)) : 0;
    const posicao = indice + 1;
    const medalha = posicao === 1 ? '🥇' : posicao === 2 ? '🥈' : posicao === 3 ? '🥉' : `${posicao}º`;
    const rotulo = escapeHtml(d.empresa);
    return `
      <div class="barra-item">
        <span class="barra-rotulo" title="${rotulo}">${medalha} ${rotulo}</span>
        <div class="barra-trilho"><div class="barra-preenchimento" style="width:${pct}%;background:${cor}"></div></div>
        <span class="barra-valor">${formatador(d[chaveValor])}</span>
      </div>
    `;
  }).join('');
}

async function carregarRanking() {
  const elVagas = document.getElementById('rankingVagas');
  const elSalario = document.getElementById('rankingSalario');

  try {
    const resposta = await fetch('/api/ranking');
    const dados = await resposta.json();

    renderizarRankingBarras(elVagas, dados.por_vagas || [], 'total', 'var(--serie-1)', formatarNumeroRanking);
    renderizarRankingBarras(elSalario, dados.por_salario || [], 'salario_medio', 'var(--serie-2)', formatarSalarioRanking);
  } catch (erro) {
    console.error('Erro ao carregar ranking:', erro);
    [elVagas, elSalario].forEach((el) => {
      if (el) el.innerHTML = '<p class="dash-carregando">Não foi possível carregar o ranking agora. Tente recarregar a página.</p>';
    });
  }
}

function formatarNumeroRanking(valor) {
  return Number(valor).toLocaleString('pt-BR');
}

carregarRanking();
