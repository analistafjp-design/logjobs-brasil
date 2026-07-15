const API_BASE_DASH = '/api';

function formatarSalarioDash(valor) {
  return `R$ ${Number(valor).toLocaleString('pt-BR', { maximumFractionDigits: 0 })}`;
}

function renderizarEvolucao(container, dados) {
  if (!container) return;

  if (!dados.length) {
    container.innerHTML = '<p class="dash-carregando">Ainda não há execuções registradas — a primeira atualização automática roda em até 20 minutos após o site subir.</p>';
    return;
  }

  const largura = 640;
  const altura = 200;
  const margem = 28;
  const valores = dados.map((d) => d.vagas_novas);
  const max = Math.max(1, ...valores);
  const passoX = dados.length > 1 ? (largura - margem * 2) / (dados.length - 1) : 0;

  const pontos = dados.map((d, i) => {
    const x = margem + i * passoX;
    const y = altura - margem - (d.vagas_novas / max) * (altura - margem * 2);
    return { x, y, valor: d.vagas_novas };
  });

  const linha = pontos.map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
  const area = `${margem},${altura - margem} ${linha} ${pontos[pontos.length - 1].x.toFixed(1)},${altura - margem}`;
  const ultimo = pontos[pontos.length - 1];

  container.innerHTML = `
    <svg viewBox="0 0 ${largura} ${altura}" preserveAspectRatio="none" role="img" aria-label="Vagas novas encontradas por execução do agendador">
      <line class="grafico-linha-eixo" x1="${margem}" y1="${altura - margem}" x2="${largura - margem}" y2="${altura - margem}"></line>
      <polygon class="grafico-linha-area" points="${area}"></polygon>
      <polyline class="grafico-linha-path" points="${linha}"></polyline>
      <circle class="grafico-linha-ponto" cx="${ultimo.x.toFixed(1)}" cy="${ultimo.y.toFixed(1)}" r="4"></circle>
      <text class="grafico-linha-rotulo" x="${ultimo.x.toFixed(1)}" y="${(ultimo.y - 10).toFixed(1)}" text-anchor="end">${ultimo.valor}</text>
    </svg>
  `;
}

async function carregarDashboard() {
  const elCategoria = document.getElementById('graficoCategoria');
  const elEstado = document.getElementById('graficoEstado');
  const elEmpresas = document.getElementById('graficoEmpresas');
  const elSalario = document.getElementById('graficoSalario');
  const elEvolucao = document.getElementById('graficoEvolucao');

  try {
    const resposta = await fetch(`${API_BASE_DASH}/dashboard`);
    const dados = await resposta.json();

    const categoriaAgrupada = agruparTop(dados.por_categoria || [], 'categoria', 'total', 8);
    const mapaCoresCategoria = construirMapaCores(categoriaAgrupada, 'categoria');
    renderizarBarras(elCategoria, categoriaAgrupada, 'categoria', 'total', mapaCoresCategoria);
    if (elCategoria) {
      elCategoria.insertAdjacentHTML('afterend', `<div class="dash-legenda">${renderizarLegenda(categoriaAgrupada, 'categoria', mapaCoresCategoria)}</div>`);
    }

    const estadoTop = agruparTop(dados.por_estado || [], 'estado', 'total', 10);
    const mapaCoresEstado = new Map(estadoTop.map((d) => [d.estado, corVar('--serie-1')]));
    renderizarBarras(elEstado, estadoTop, 'estado', 'total', mapaCoresEstado);

    const empresasTop = (dados.top_empresas || []).slice(0, 10);
    const mapaCoresEmpresas = new Map(empresasTop.map((d) => [d.empresa, corVar('--serie-2')]));
    renderizarBarras(elEmpresas, empresasTop, 'empresa', 'total', mapaCoresEmpresas);

    const salarioOrdenado = [...(dados.salario_por_categoria || [])].sort((a, b) => b.salario_medio - a.salario_medio);
    const mapaCoresSalario = new Map(
      salarioOrdenado.map((d) => [d.categoria, mapaCoresCategoria.get(d.categoria) || corVar('--texto-suave')])
    );
    renderizarBarras(elSalario, salarioOrdenado, 'categoria', 'salario_medio', mapaCoresSalario, formatarSalarioDash);

    renderizarEvolucao(elEvolucao, dados.evolucao || []);
  } catch (erro) {
    console.error('Erro ao carregar dashboard:', erro);
    [elCategoria, elEstado, elEmpresas, elSalario, elEvolucao].forEach((el) => {
      if (el) el.innerHTML = '<p class="dash-carregando">Não foi possível carregar os dados agora. Tente recarregar a página.</p>';
    });
  }
}

carregarDashboard();
