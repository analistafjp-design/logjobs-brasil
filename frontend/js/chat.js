const chatBloqueado = document.getElementById('chatBloqueado');
const chatConteudo = document.getElementById('chatConteudo');
const chatListaConversas = document.getElementById('chatListaConversas');
const chatJanelaVazia = document.getElementById('chatJanelaVazia');
const chatJanelaAtiva = document.getElementById('chatJanelaAtiva');
const chatOutroNome = document.getElementById('chatOutroNome');
const chatVagaTag = document.getElementById('chatVagaTag');
const chatMensagensEl = document.getElementById('chatMensagens');
const chatForm = document.getElementById('chatForm');

document.getElementById('btnEntrarChat')?.addEventListener('click', () => abrirModalAuth('login'));

let conversaAtivaId = null;
let socketAtivo = null;
let idsMensagensRenderizadas = new Set();
let intervalPollingMensagens = null;
let intervalPollingConversas = null;

function formatarHoraMensagem(iso) {
  if (!iso) return '';
  const data = new Date(iso);
  return data.toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
}

function renderizarMensagem(mensagem) {
  if (idsMensagensRenderizadas.has(mensagem.id)) return;
  idsMensagensRenderizadas.add(mensagem.id);

  const bolha = document.createElement('div');
  bolha.className = `chat-bolha ${mensagem.de_mim ? 'chat-bolha-mim' : ''}`;
  bolha.dataset.mensagemId = mensagem.id;
  bolha.innerHTML = `
    <p>${escapeHtml(mensagem.texto)}</p>
    <span class="chat-bolha-hora">${escapeHtml(formatarHoraMensagem(mensagem.criada_em))}</span>
  `;
  chatMensagensEl.appendChild(bolha);
  chatMensagensEl.scrollTop = chatMensagensEl.scrollHeight;
}

function fecharSocket() {
  if (socketAtivo) {
    socketAtivo.close();
    socketAtivo = null;
  }
  if (intervalPollingMensagens) {
    clearInterval(intervalPollingMensagens);
    intervalPollingMensagens = null;
  }
}

async function buscarMensagensNovas(conversaId) {
  try {
    const resposta = await apiFetch(`${API_BASE}/chat/conversas/${conversaId}/mensagens`);
    if (!resposta.ok) return;
    const dados = await resposta.json();
    dados.mensagens.forEach(renderizarMensagem);
  } catch {
    // silencioso: tenta de novo no próximo ciclo
  }
}

function conectarSocket(conversaId) {
  fecharSocket();

  // Servidores sem suporte a WebSocket (ex.: hospedagem compartilhada, sem processo de
  // longa duração para manter a conexão) simplesmente não têm a rota /ws/chat/ — a conexão
  // falha e cai no catch. Por isso a busca por polling abaixo roda sempre, como reforço:
  // com WebSocket disponível, mensagens aparecem na hora; sem ele, aparecem em até 5s.
  // renderizarMensagem já ignora IDs repetidos, então não duplica nada.
  try {
    const protocolo = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const token = obterToken();
    socketAtivo = new WebSocket(`${protocolo}//${window.location.host}/ws/chat/${conversaId}?token=${encodeURIComponent(token)}`);
    socketAtivo.addEventListener('message', (evento) => {
      try {
        const mensagem = JSON.parse(evento.data);
        renderizarMensagem({ ...mensagem, de_mim: false });
        // se a mensagem é minha (recebida de volta pelo próprio socket), corrige a marcação
        const usuario = obterUsuario();
        if (usuario && mensagem.remetente_id === usuario.id) {
          const el = chatMensagensEl.querySelector(`[data-mensagem-id="${mensagem.id}"]`);
          el?.classList.add('chat-bolha-mim');
        }
      } catch {
        // ignora mensagens que não sejam JSON válido
      }
    });
    socketAtivo.addEventListener('error', () => {
      socketAtivo = null;
    });
  } catch {
    socketAtivo = null;
  }

  intervalPollingMensagens = setInterval(() => buscarMensagensNovas(conversaId), 5000);
}

async function abrirConversa(conversaId, outroNome, vagaCargo) {
  conversaAtivaId = conversaId;
  idsMensagensRenderizadas = new Set();
  chatMensagensEl.innerHTML = '';
  chatOutroNome.textContent = outroNome || 'Conversa';
  if (vagaCargo) {
    chatVagaTag.textContent = `Sobre: ${vagaCargo}`;
    chatVagaTag.hidden = false;
  } else {
    chatVagaTag.hidden = true;
  }

  chatJanelaVazia.hidden = true;
  chatJanelaAtiva.hidden = false;

  document.querySelectorAll('.chat-conversa-item').forEach((el) => {
    el.classList.toggle('ativa', Number(el.dataset.conversaId) === conversaId);
  });

  try {
    const resposta = await apiFetch(`${API_BASE}/chat/conversas/${conversaId}/mensagens`);
    if (!resposta.ok) throw new Error();
    const dados = await resposta.json();
    dados.mensagens.forEach(renderizarMensagem);
  } catch {
    mostrarToast('Não foi possível carregar as mensagens.');
  }

  conectarSocket(conversaId);
  carregarConversas(); // atualiza contagem de não lidas na lista
}

function conversaParaHtml(conversa) {
  const outroNome = conversa.outro_usuario ? conversa.outro_usuario.nome : 'Usuário removido';
  const preview = conversa.ultima_mensagem
    ? `${conversa.ultima_mensagem.de_mim ? 'Você: ' : ''}${conversa.ultima_mensagem.texto}`
    : 'Nenhuma mensagem ainda';
  return `
    <button type="button" class="chat-conversa-item${conversa.nao_lidas ? ' nao-lida' : ''}" data-conversa-id="${conversa.id}">
      <strong>${escapeHtml(outroNome)}</strong>
      ${conversa.vaga ? `<span class="chat-conversa-vaga">${escapeHtml(conversa.vaga.cargo)}</span>` : ''}
      <span class="chat-conversa-preview">${escapeHtml(preview)}</span>
      ${conversa.nao_lidas ? `<span class="chat-badge">${escapeHtml(conversa.nao_lidas)}</span>` : ''}
    </button>
  `;
}

async function carregarConversas() {
  try {
    const resposta = await apiFetch(`${API_BASE}/chat/conversas`);
    if (!resposta.ok) throw new Error();
    const conversas = await resposta.json();

    if (!conversas.length) {
      chatListaConversas.innerHTML = '<p class="vagas-carregando">Você ainda não tem conversas.</p>';
      return;
    }

    chatListaConversas.innerHTML = conversas.map(conversaParaHtml).join('');
    chatListaConversas.querySelectorAll('.chat-conversa-item').forEach((botao) => {
      botao.addEventListener('click', () => {
        const conversa = conversas.find((c) => c.id === Number(botao.dataset.conversaId));
        abrirConversa(conversa.id, conversa.outro_usuario?.nome, conversa.vaga?.cargo);
      });
    });

    return conversas;
  } catch {
    chatListaConversas.innerHTML = '<p class="vagas-carregando">Não foi possível carregar suas conversas.</p>';
  }
}

chatForm?.addEventListener('submit', async (evento) => {
  evento.preventDefault();
  if (!conversaAtivaId) return;

  const texto = chatForm.texto.value.trim();
  if (!texto) return;
  chatForm.texto.value = '';

  try {
    const resposta = await apiFetch(`${API_BASE}/chat/conversas/${conversaAtivaId}/mensagens`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ texto }),
    });
    if (!resposta.ok) throw new Error();
    const mensagem = await resposta.json();
    renderizarMensagem(mensagem);
  } catch {
    mostrarToast('Não foi possível enviar a mensagem.');
  }
});

async function iniciarChat() {
  const token = obterToken();
  const usuario = obterUsuario();

  if (!token || !usuario) {
    chatBloqueado.hidden = false;
    chatConteudo.hidden = true;
    return;
  }

  chatBloqueado.hidden = true;
  chatConteudo.hidden = false;

  const conversas = await carregarConversas();

  const params = new URLSearchParams(window.location.search);
  const conversaAlvo = params.get('conversa');
  if (conversaAlvo && conversas) {
    const conversa = conversas.find((c) => c.id === Number(conversaAlvo));
    if (conversa) abrirConversa(conversa.id, conversa.outro_usuario?.nome, conversa.vaga?.cargo);
  }

  // Atualiza a lista de conversas (contagem de não lidas) periodicamente, mesmo sem
  // nenhuma conversa aberta — mesma lógica de reforço por polling usada nas mensagens.
  intervalPollingConversas = setInterval(carregarConversas, 20000);
}

function pararPolling() {
  fecharSocket();
  if (intervalPollingConversas) {
    clearInterval(intervalPollingConversas);
    intervalPollingConversas = null;
  }
}

window.addEventListener('beforeunload', pararPolling);

iniciarChat();
