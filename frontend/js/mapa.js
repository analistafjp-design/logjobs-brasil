// Coordenadas aproximadas das capitais (lat, lng) — usadas como ponto representativo
// de cada estado, já que o banco não guarda geolocalização por vaga/cidade.
const COORDENADAS_ESTADO = {
  AC: [-9.97, -67.81], AL: [-9.65, -35.70], AP: [0.03, -51.05], AM: [-3.10, -60.02],
  BA: [-12.97, -38.51], CE: [-3.73, -38.52], DF: [-15.78, -47.93], ES: [-20.32, -40.34],
  GO: [-16.68, -49.25], MA: [-2.53, -44.30], MT: [-15.60, -56.10], MS: [-20.44, -54.65],
  MG: [-19.92, -43.94], PA: [-1.46, -48.50], PB: [-7.12, -34.86], PR: [-25.43, -49.27],
  PE: [-8.05, -34.90], PI: [-5.09, -42.80], RJ: [-22.91, -43.17], RN: [-5.79, -35.21],
  RS: [-30.03, -51.23], RO: [-8.76, -63.90], RR: [2.82, -60.67], SC: [-27.60, -48.55],
  SP: [-23.55, -46.63], SE: [-10.91, -37.07], TO: [-10.25, -48.32],
};

const LAT_MIN = -33.75, LAT_MAX = 5.27, LNG_MIN = -73.99, LNG_MAX = -34.79;
const LARGURA = 620, ALTURA = 640, MARGEM = 30;

function projetar(lat, lng) {
  const x = MARGEM + ((lng - LNG_MIN) / (LNG_MAX - LNG_MIN)) * (LARGURA - 2 * MARGEM);
  const y = MARGEM + ((LAT_MAX - lat) / (LAT_MAX - LAT_MIN)) * (ALTURA - 2 * MARGEM);
  return [x, y];
}

async function carregarMapa() {
  const container = document.getElementById('mapaWrap');
  try {
    const resposta = await fetch('/api/dashboard');
    const dados = await resposta.json();
    const porEstado = (dados.por_estado || []).filter((d) => COORDENADAS_ESTADO[d.estado]);

    if (!porEstado.length) {
      container.innerHTML = '<p class="dash-carregando">Ainda sem dados suficientes para o mapa.</p>';
      return;
    }

    const max = Math.max(...porEstado.map((d) => d.total));
    const raioMax = 34, raioMin = 8;

    const circulos = porEstado.map((d) => {
      const [lat, lng] = COORDENADAS_ESTADO[d.estado];
      const [x, y] = projetar(lat, lng);
      const raio = raioMin + Math.sqrt(d.total / max) * (raioMax - raioMin);
      return `
        <g class="mapa-ponto" data-estado="${d.estado}" data-total="${d.total}" tabindex="0" role="button" aria-label="${d.estado}: ${d.total} vagas">
          <circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${raio.toFixed(1)}"></circle>
          <text x="${x.toFixed(1)}" y="${y.toFixed(1)}" dy="0.35em" text-anchor="middle">${d.estado}</text>
        </g>
      `;
    }).join('');

    container.innerHTML = `
      <svg viewBox="0 0 ${LARGURA} ${ALTURA}" class="mapa-svg" role="img" aria-label="Mapa de vagas por estado">
        ${circulos}
      </svg>
      <div class="mapa-tooltip" id="mapaTooltip" hidden></div>
    `;

    ativarInteracao();
  } catch (erro) {
    container.innerHTML = '<p class="dash-carregando">Não foi possível carregar o mapa agora.</p>';
    console.error(erro);
  }
}

function ativarInteracao() {
  const tooltip = document.getElementById('mapaTooltip');
  const pontos = document.querySelectorAll('.mapa-ponto');

  pontos.forEach((ponto) => {
    const mostrarTooltip = (evento) => {
      const estado = ponto.dataset.estado;
      const total = ponto.dataset.total;
      tooltip.textContent = `${estado}: ${total} vaga${total === '1' ? '' : 's'}`;
      tooltip.hidden = false;
      const rect = ponto.closest('.mapa-wrap').getBoundingClientRect();
      const origem = evento.touches ? evento.touches[0] : evento;
      tooltip.style.left = `${origem.clientX - rect.left + 12}px`;
      tooltip.style.top = `${origem.clientY - rect.top + 12}px`;
    };

    ponto.addEventListener('mousemove', mostrarTooltip);
    ponto.addEventListener('mouseleave', () => { tooltip.hidden = true; });
    ponto.addEventListener('click', () => {
      window.location.href = `index.html?estado=${ponto.dataset.estado}#vagas`;
    });
    ponto.addEventListener('keydown', (evento) => {
      if (evento.key === 'Enter' || evento.key === ' ') {
        window.location.href = `index.html?estado=${ponto.dataset.estado}#vagas`;
      }
    });
  });
}

carregarMapa();
