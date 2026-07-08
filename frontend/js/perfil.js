const perfilBloqueado = document.getElementById('perfilBloqueado');
const perfilConteudo = document.getElementById('perfilConteudo');
const formPerfil = document.getElementById('formPerfil');
const perfilFavoritosEl = document.getElementById('perfilFavoritos');
const secaoRecomendadas = document.getElementById('secaoRecomendadas');
const perfilRecomendadasEl = document.getElementById('perfilRecomendadas');

document.getElementById('btnEntrarPerfil')?.addEventListener('click', () => abrirModalAuth('login'));

async function iniciarPerfil() {
  const token = obterToken();
  const usuarioLocal = obterUsuario();

  if (!token || !usuarioLocal) {
    perfilBloqueado.hidden = false;
    perfilConteudo.hidden = true;
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
    // Token inválido ou expirado: trata como deslogado.
    encerrarSessao();
    perfilBloqueado.hidden = false;
    perfilConteudo.hidden = true;
    return;
  }

  perfilBloqueado.hidden = true;
  perfilConteudo.hidden = false;

  document.getElementById('perfilTitulo').textContent =
    usuario.tipo === 'empresa' ? 'Perfil da empresa' : 'Meu perfil';
  document.getElementById('labelResumo').firstChild.textContent =
    usuario.tipo === 'empresa' ? 'Sobre a empresa' : 'Mini-currículo';
  formPerfil.querySelector('textarea[name=resumo]').placeholder =
    usuario.tipo === 'empresa'
      ? 'Conte um pouco sobre a empresa...'
      : 'Conte um pouco sobre sua experiência...';

  formPerfil.nome.value = usuario.nome || '';
  formPerfil.email.value = usuario.email || '';
  formPerfil.telefone.value = usuario.telefone || '';
  formPerfil.cidade.value = usuario.cidade || '';
  formPerfil.resumo.value = usuario.resumo || '';

  if (usuario.tipo === 'candidato') {
    secaoRecomendadas.hidden = false;
    carregarRecomendacoes();
  } else {
    secaoRecomendadas.hidden = true;
  }

  carregarFavoritosPerfil();
}

async function carregarRecomendacoes() {
  try {
    const resposta = await fetch(`${API_BASE}/recomendacoes`, {
      headers: { Authorization: `Bearer ${obterToken()}` },
    });
    const dados = await resposta.json();

    if (dados.motivo === 'perfil_incompleto') {
      perfilRecomendadasEl.innerHTML = '<p class="vagas-carregando">Preencha seu mini-currículo acima e clique em "Salvar alterações" para receber recomendações personalizadas.</p>';
      return;
    }

    const vagas = dados.vagas || [];
    if (vagas.length === 0) {
      perfilRecomendadasEl.innerHTML = '<p class="vagas-carregando">Ainda não encontramos vagas compatíveis com seu perfil. Tente detalhar mais suas experiências.</p>';
      return;
    }

    perfilRecomendadasEl.innerHTML = `<div class="vagas-grid">${vagas.map((vaga) => `
      <article class="vaga">
        <div class="vaga-topo">
          <h3><a href="/vagas/${escapeHtml(vaga.id)}">${escapeHtml(vaga.empresa)}</a></h3>
          <span class="tag compatibilidade">${vaga.compatibilidade}% compatível</span>
        </div>
        <p class="vaga-info"><a href="/vagas/${escapeHtml(vaga.id)}">${escapeHtml(vaga.cargo)}</a> • ${escapeHtml(vaga.cidade)}${vaga.estado ? ', ' + escapeHtml(vaga.estado) : ''}</p>
        <div class="vaga-rodape">
          <span class="salario">${escapeHtml(formatarSalario(vaga.salario))}</span>
          <div class="vaga-acoes">
            ${botaoSalvar(vaga)}
          </div>
        </div>
      </article>
    `).join('')}</div>`;
  } catch {
    perfilRecomendadasEl.innerHTML = '<p class="vagas-carregando">Não foi possível carregar recomendações.</p>';
  }
}

perfilRecomendadasEl?.addEventListener('click', (event) => {
  const botao = event.target.closest('.btn-salvar');
  if (botao) alternarFavorito(botao.dataset.vagaId, botao).then(() => carregarFavoritosPerfil());
});

formPerfil?.addEventListener('submit', async (event) => {
  event.preventDefault();
  const erroEl = document.getElementById('perfilErro');
  const sucessoEl = document.getElementById('perfilSucesso');
  erroEl.hidden = true;
  sucessoEl.hidden = true;

  try {
    const resposta = await fetch(`${API_BASE}/auth/me`, {
      method: 'PATCH',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${obterToken()}`,
      },
      body: JSON.stringify({
        nome: formPerfil.nome.value.trim(),
        telefone: formPerfil.telefone.value.trim(),
        cidade: formPerfil.cidade.value.trim(),
        resumo: formPerfil.resumo.value.trim(),
      }),
    });
    const usuarioAtualizado = await resposta.json();
    if (!resposta.ok) throw new Error(usuarioAtualizado.detail || 'Não foi possível salvar');

    localStorage.setItem('logjobs-usuario', JSON.stringify(usuarioAtualizado));
    renderAreaConta();
    if (usuarioAtualizado.tipo === 'candidato') carregarRecomendacoes();
    sucessoEl.hidden = false;
    setTimeout(() => { sucessoEl.hidden = true; }, 3000);
  } catch (erro) {
    erroEl.textContent = erro.message || 'Não foi possível salvar. Tente novamente.';
    erroEl.hidden = false;
  }
});

async function carregarFavoritosPerfil() {
  await carregarFavoritos();

  if (favoritosIds.size === 0) {
    perfilFavoritosEl.innerHTML = '<p class="vagas-carregando">Você ainda não salvou nenhuma vaga.</p>';
    return;
  }

  try {
    const resposta = await fetch(`${API_BASE}/favoritos`, {
      headers: { Authorization: `Bearer ${obterToken()}` },
    });
    const dados = await resposta.json();
    const vagas = dados.vagas || [];

    if (vagas.length === 0) {
      perfilFavoritosEl.innerHTML = '<p class="vagas-carregando">Você ainda não salvou nenhuma vaga.</p>';
      return;
    }

    perfilFavoritosEl.innerHTML = `<div class="vagas-grid">${vagas.map((vaga) => `
      <article class="vaga">
        <div class="vaga-topo">
          <h3><a href="/vagas/${escapeHtml(vaga.id)}">${escapeHtml(vaga.empresa)}</a></h3>
          <span class="tag">${escapeHtml(vaga.categoria || '')}</span>
        </div>
        <p class="vaga-info"><a href="/vagas/${escapeHtml(vaga.id)}">${escapeHtml(vaga.cargo)}</a> • ${escapeHtml(vaga.cidade)}${vaga.estado ? ', ' + escapeHtml(vaga.estado) : ''}</p>
        <div class="vaga-rodape">
          <span class="salario">${escapeHtml(formatarSalario(vaga.salario))}</span>
          <div class="vaga-acoes">
            <button class="btn-salvar salvo" data-vaga-id="${escapeHtml(vaga.id)}" aria-pressed="true" aria-label="Remover dos salvos" title="Remover dos salvos">★</button>
          </div>
        </div>
      </article>
    `).join('')}</div>`;
  } catch {
    perfilFavoritosEl.innerHTML = '<p class="vagas-carregando">Não foi possível carregar suas vagas salvas.</p>';
  }
}

perfilFavoritosEl?.addEventListener('click', (event) => {
  const botao = event.target.closest('.btn-salvar');
  if (!botao) return;
  alternarFavorito(botao.dataset.vagaId, botao).then(() => {
    if (!favoritosIds.has(Number(botao.dataset.vagaId))) {
      botao.closest('.vaga')?.remove();
      if (favoritosIds.size === 0) {
        perfilFavoritosEl.innerHTML = '<p class="vagas-carregando">Você ainda não salvou nenhuma vaga.</p>';
      }
    }
  });
});

renderAreaConta();
iniciarPerfil();
