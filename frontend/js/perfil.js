const perfilBloqueado = document.getElementById('perfilBloqueado');
const perfilConteudo = document.getElementById('perfilConteudo');
const formPerfil = document.getElementById('formPerfil');
const perfilFavoritosEl = document.getElementById('perfilFavoritos');
const secaoRecomendadas = document.getElementById('secaoRecomendadas');
const perfilRecomendadasEl = document.getElementById('perfilRecomendadas');
const secaoConquistas = document.getElementById('secaoConquistas');
const perfilConquistasEl = document.getElementById('perfilConquistas');
const perfilAlertasEl = document.getElementById('perfilAlertas');
const perfilCandidaturasEl = document.getElementById('perfilCandidaturas');

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
  formPerfil.habilidades.value = usuario.habilidades || '';
  formPerfil.pretensao_salarial.value = usuario.pretensao_salarial || '';
  formPerfil.disponibilidade.value = usuario.disponibilidade || '';
  formPerfil.possui_cnh.value = usuario.possui_cnh || '';
  formPerfil.veiculo_proprio.value = usuario.veiculo_proprio || '';
  formPerfil.linkedin_url.value = usuario.linkedin_url || '';
  formPerfil.github_url.value = usuario.github_url || '';
  formPerfil.portfolio_url.value = usuario.portfolio_url || '';

  const secaoAlertas = document.getElementById('secaoAlertas');
  const secaoCandidaturasHistorico = document.getElementById('secaoCandidaturasHistorico');
  const camposCandidato = document.getElementById('camposCandidato');
  const secaoListasCandidato = document.getElementById('secaoListasCandidato');
  const secaoFormacoes = document.getElementById('secaoFormacoes');
  const secaoCursos = document.getElementById('secaoCursos');
  const secaoCertificados = document.getElementById('secaoCertificados');
  const secaoIdiomas = document.getElementById('secaoIdiomas');
  const secaoCompletude = document.getElementById('secaoCompletude');
  const secaoIA = document.getElementById('secaoIA');

  if (usuario.tipo === 'candidato') {
    secaoRecomendadas.hidden = false;
    secaoConquistas.hidden = false;
    secaoAlertas.hidden = false;
    secaoCandidaturasHistorico.hidden = false;
    camposCandidato.hidden = false;
    secaoListasCandidato.hidden = false;
    secaoFormacoes.hidden = false;
    secaoCursos.hidden = false;
    secaoCertificados.hidden = false;
    secaoIdiomas.hidden = false;
    secaoCompletude.hidden = false;
    secaoIA.hidden = false;
    carregarRecomendacoes();
    carregarConquistas();
    carregarAlertas();
    carregarCandidaturasHistorico();
    renderizarCompletude(usuario.perfil_completude);
    inicializarListasCandidato(usuario);
    carregarAnalisePerfil();
    carregarCategoriasSimulador();
  } else {
    secaoRecomendadas.hidden = true;
    secaoConquistas.hidden = true;
    secaoAlertas.hidden = true;
    secaoCandidaturasHistorico.hidden = true;
    camposCandidato.hidden = true;
    secaoListasCandidato.hidden = true;
    secaoFormacoes.hidden = true;
    secaoCursos.hidden = true;
    secaoCertificados.hidden = true;
    secaoIdiomas.hidden = true;
    secaoCompletude.hidden = true;
    secaoIA.hidden = true;
  }

  carregarFavoritosPerfil();
  renderizarTotpStatus(usuario);
}

function renderizarCompletude(percentual) {
  document.getElementById('completudeBarra').style.width = `${percentual}%`;
  document.getElementById('completudeTexto').textContent =
    percentual >= 100 ? 'Perfil completo! 🎉' : `${percentual}% do perfil preenchido — quanto mais completo, melhores as recomendações de vaga.`;
}

/* ===== Listas do candidato: experiência, formação, cursos, certificados, idiomas =====
   Um único padrão genérico para as 5 seções, em vez de repetir a mesma lógica 5 vezes. */

const CONFIG_LISTAS_CANDIDATO = [
  {
    chave: 'experiencias',
    listaElId: 'listaExperiencias',
    formId: 'formExperiencia',
    formatar: (item) => `
      <strong>${escapeHtml(item.cargo)}</strong> — ${escapeHtml(item.empresa)}${item.cidade ? ' · ' + escapeHtml(item.cidade) : ''}<br>
      <span class="modal-subtitulo">${escapeHtml(item.inicio || '?')} – ${escapeHtml(item.fim || 'Atual')}</span>
      ${item.descricao ? `<p>${escapeHtml(item.descricao)}</p>` : ''}
    `,
  },
  {
    chave: 'formacoes',
    listaElId: 'listaFormacoes',
    formId: 'formFormacao',
    formatar: (item) => `
      <strong>${escapeHtml(item.curso)}</strong> — ${escapeHtml(item.instituicao)}<br>
      <span class="modal-subtitulo">${[item.nivel, item.status, item.ano].filter(Boolean).map(escapeHtml).join(' · ')}</span>
    `,
  },
  {
    chave: 'cursos',
    listaElId: 'listaCursos',
    formId: 'formCurso',
    formatar: (item) => `
      <strong>${escapeHtml(item.nome)}</strong>${item.instituicao ? ' — ' + escapeHtml(item.instituicao) : ''}${item.ano ? ` <span class="modal-subtitulo">(${escapeHtml(item.ano)})</span>` : ''}
    `,
  },
  {
    chave: 'certificados',
    listaElId: 'listaCertificados',
    formId: 'formCertificado',
    formatar: (item) => `
      <strong>${escapeHtml(item.nome)}</strong>${item.instituicao ? ' — ' + escapeHtml(item.instituicao) : ''}${item.ano ? ` <span class="modal-subtitulo">(${escapeHtml(item.ano)})</span>` : ''}
    `,
  },
  {
    chave: 'idiomas',
    listaElId: 'listaIdiomas',
    formId: 'formIdioma',
    formatar: (item) => `<strong>${escapeHtml(item.idioma)}</strong>${item.nivel ? ' — ' + escapeHtml(item.nivel) : ''}`,
  },
];

let estadoListasCandidato = {};

function renderizarListaCandidato(cfg) {
  const itens = estadoListasCandidato[cfg.chave] || [];
  const el = document.getElementById(cfg.listaElId);
  if (!itens.length) {
    el.innerHTML = '<p class="vagas-carregando">Nenhum item adicionado ainda.</p>';
    return;
  }
  el.innerHTML = itens.map((item, indice) => `
    <div class="comparador-card" style="margin-bottom: 10px;">
      <div class="comparador-linha" style="align-items:flex-start;">
        <div>${cfg.formatar(item)}</div>
        <button type="button" class="admin-acao-btn excluir" data-chave="${cfg.chave}" data-indice="${indice}">Remover</button>
      </div>
    </div>
  `).join('');
}

async function salvarListaCandidato(cfg) {
  try {
    const resposta = await fetch(`${API_BASE}/auth/me`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${obterToken()}` },
      body: JSON.stringify({ [cfg.chave]: estadoListasCandidato[cfg.chave] }),
    });
    const usuarioAtualizado = await resposta.json();
    if (!resposta.ok) throw new Error(usuarioAtualizado.detail || 'Não foi possível salvar');
    localStorage.setItem('logjobs-usuario', JSON.stringify(usuarioAtualizado));
    renderizarListaCandidato(cfg);
    renderizarCompletude(usuarioAtualizado.perfil_completude);
    mostrarToast('✅ Salvo');
  } catch (erro) {
    mostrarToast(erro.message || 'Não foi possível salvar');
  }
}

function inicializarListasCandidato(usuario) {
  CONFIG_LISTAS_CANDIDATO.forEach((cfg) => {
    estadoListasCandidato[cfg.chave] = usuario[cfg.chave] || [];
    renderizarListaCandidato(cfg);

    const form = document.getElementById(cfg.formId);
    if (form.dataset.configurado) return;
    form.dataset.configurado = '1';
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      const item = {};
      new FormData(form).forEach((valor, chave) => { item[chave] = valor.trim() || null; });
      estadoListasCandidato[cfg.chave] = [...estadoListasCandidato[cfg.chave], item];
      await salvarListaCandidato(cfg);
      form.reset();
    });
  });
}

document.addEventListener('click', async (event) => {
  const botao = event.target.closest('[data-chave][data-indice]');
  if (!botao) return;
  const cfg = CONFIG_LISTAS_CANDIDATO.find((c) => c.chave === botao.dataset.chave);
  if (!cfg) return;
  estadoListasCandidato[cfg.chave].splice(Number(botao.dataset.indice), 1);
  await salvarListaCandidato(cfg);
});

/* ===== Verificação em duas etapas (2FA) ===== */

const totpStatusEl = document.getElementById('totpStatus');

function renderizarTotpStatus(usuario) {
  if (usuario.totp_ativado) {
    totpStatusEl.innerHTML = `
      <p>✅ Verificação em duas etapas está <strong>ativada</strong> nesta conta.</p>
      <form id="formDesativarTotp">
        <label>Confirme sua senha para desativar
          <input type="password" name="senha" required autocomplete="current-password">
        </label>
        <p class="modal-erro" id="totpDesativarErro" hidden></p>
        <button type="submit" class="admin-acao-btn excluir">Desativar 2FA</button>
      </form>
    `;
    document.getElementById('formDesativarTotp').addEventListener('submit', async (event) => {
      event.preventDefault();
      const erroEl = document.getElementById('totpDesativarErro');
      erroEl.hidden = true;
      try {
        const resposta = await fetch(`${API_BASE}/auth/2fa/desativar`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${obterToken()}` },
          body: JSON.stringify({ senha: event.target.senha.value }),
        });
        const dados = await resposta.json();
        if (!resposta.ok) throw new Error(dados.detail || 'Não foi possível desativar');
        mostrarToast('2FA desativada');
        const usuarioAtual = { ...obterUsuario(), totp_ativado: false };
        localStorage.setItem('logjobs-usuario', JSON.stringify(usuarioAtual));
        renderizarTotpStatus(usuarioAtual);
      } catch (erro) {
        erroEl.textContent = erro.message;
        erroEl.hidden = false;
      }
    });
    return;
  }

  totpStatusEl.innerHTML = `
    <p>Verificação em duas etapas está <strong>desativada</strong>.</p>
    <button type="button" class="btn-candidatar" id="btnAtivarTotp">Ativar verificação em duas etapas</button>
  `;
  document.getElementById('btnAtivarTotp').addEventListener('click', iniciarAtivacaoTotp);
}

async function iniciarAtivacaoTotp() {
  try {
    const resposta = await fetch(`${API_BASE}/auth/2fa/iniciar`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${obterToken()}` },
    });
    const dados = await resposta.json();
    if (!resposta.ok) throw new Error(dados.detail || 'Não foi possível iniciar a ativação');

    totpStatusEl.innerHTML = `
      <p>1. Adicione esta chave no seu app autenticador (Google Authenticator, Authy...):</p>
      <p><code>${escapeHtml(dados.segredo)}</code></p>
      <p class="modal-subtitulo">Ou cole este link, se seu app aceitar importar por URL:<br><code style="word-break: break-all;">${escapeHtml(dados.otpauth_uri)}</code></p>
      <p>2. Digite o código de 6 dígitos gerado pelo app para confirmar:</p>
      <form id="formConfirmarTotp">
        <label>Código
          <input type="text" name="codigo" inputmode="numeric" pattern="[0-9]{6}" maxlength="6" required>
        </label>
        <p class="modal-erro" id="totpConfirmarErro" hidden></p>
        <button type="submit" class="modal-enviar">Confirmar e ativar</button>
        <button type="button" class="btn-sair" id="btnCancelarTotp">Cancelar</button>
      </form>
    `;

    document.getElementById('btnCancelarTotp').addEventListener('click', () => renderizarTotpStatus(obterUsuario()));

    document.getElementById('formConfirmarTotp').addEventListener('submit', async (event) => {
      event.preventDefault();
      const erroEl = document.getElementById('totpConfirmarErro');
      erroEl.hidden = true;
      try {
        const resp = await fetch(`${API_BASE}/auth/2fa/confirmar`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${obterToken()}` },
          body: JSON.stringify({ codigo: event.target.codigo.value.trim() }),
        });
        const corpo = await resp.json();
        if (!resp.ok) throw new Error(corpo.detail || 'Código inválido');

        mostrarToast('✅ 2FA ativada');
        const usuarioAtual = { ...obterUsuario(), totp_ativado: true };
        localStorage.setItem('logjobs-usuario', JSON.stringify(usuarioAtual));
        renderizarTotpStatus(usuarioAtual);
      } catch (erro) {
        erroEl.textContent = erro.message;
        erroEl.hidden = false;
      }
    });
  } catch (erro) {
    mostrarToast(erro.message || 'Não foi possível iniciar a ativação');
  }
}

async function carregarConquistas() {
  try {
    const resposta = await fetch(`${API_BASE}/conquistas`, {
      headers: { Authorization: `Bearer ${obterToken()}` },
    });
    const dados = await resposta.json();

    document.getElementById('conquistasNivel').textContent = `${dados.nivel} · ${dados.total_conquistado}/${dados.total}`;

    perfilConquistasEl.innerHTML = `<div class="conquistas-grid">${dados.badges.map((b) => `
      <div class="badge-conquista${b.conquistado ? ' conquistado' : ''}">
        <span class="badge-icone">${b.icone}</span>
        <div>
          <h3>${escapeHtml(b.titulo)}</h3>
          <p>${escapeHtml(b.descricao)}</p>
        </div>
      </div>
    `).join('')}</div>`;
  } catch {
    perfilConquistasEl.innerHTML = '<p class="vagas-carregando">Não foi possível carregar suas conquistas.</p>';
  }
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
  if (botao) alternarFavorito(botao.dataset.vagaId, botao).then(() => {
    carregarFavoritosPerfil();
    carregarConquistas();
  });
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
        habilidades: formPerfil.habilidades.value.trim(),
        pretensao_salarial: formPerfil.pretensao_salarial.value ? Number(formPerfil.pretensao_salarial.value) : null,
        disponibilidade: formPerfil.disponibilidade.value,
        possui_cnh: formPerfil.possui_cnh.value,
        veiculo_proprio: formPerfil.veiculo_proprio.value,
        linkedin_url: formPerfil.linkedin_url.value.trim(),
        github_url: formPerfil.github_url.value.trim(),
        portfolio_url: formPerfil.portfolio_url.value.trim(),
      }),
    });
    const usuarioAtualizado = await resposta.json();
    if (!resposta.ok) throw new Error(usuarioAtualizado.detail || 'Não foi possível salvar');

    localStorage.setItem('logjobs-usuario', JSON.stringify(usuarioAtualizado));
    renderAreaConta();
    if (usuarioAtualizado.tipo === 'candidato') {
      carregarRecomendacoes();
      carregarConquistas();
      renderizarCompletude(usuarioAtualizado.perfil_completude);
    }
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
    if (obterUsuario()?.tipo === 'candidato') carregarConquistas();
  });
});

/* ===== Alertas de vagas ===== */

function criterioAlertaTexto(alerta) {
  const partes = [];
  if (alerta.cargo) partes.push(`cargo: "${alerta.cargo}"`);
  if (alerta.categoria) partes.push(`categoria: "${alerta.categoria}"`);
  if (alerta.cidade) partes.push(`cidade: "${alerta.cidade}"`);
  if (alerta.estado) partes.push(`estado: ${alerta.estado}`);
  return partes.join(' · ') || 'Todas as vagas';
}

function linkAlerta(alerta) {
  const params = new URLSearchParams();
  if (alerta.cargo) params.set('cargo', alerta.cargo);
  if (alerta.cidade) params.set('cidade', alerta.cidade);
  if (alerta.estado) params.set('estado', alerta.estado);
  if (alerta.categoria) params.set('categoria', alerta.categoria);
  return `index.html?${params.toString()}#vagas`;
}

async function carregarAlertas() {
  try {
    const resposta = await fetch(`${API_BASE}/alertas`, {
      headers: { Authorization: `Bearer ${obterToken()}` },
    });
    const alertas = await resposta.json();

    if (!alertas.length) {
      perfilAlertasEl.innerHTML = '<p class="vagas-carregando">Você ainda não salvou nenhum alerta.</p>';
      return;
    }

    perfilAlertasEl.innerHTML = alertas.map((a) => `
      <div class="comparador-card" style="margin-bottom: 12px;">
        <div class="comparador-linha">
          <span>${escapeHtml(criterioAlertaTexto(a))}</span>
          <strong>${a.total_vagas} vaga${a.total_vagas === 1 ? '' : 's'} ${a.vagas_novas > 0 ? `<span class="tag compatibilidade">+${a.vagas_novas} nova${a.vagas_novas === 1 ? '' : 's'}</span>` : ''}</strong>
        </div>
        <div class="vaga-acoes" style="margin-top: 10px;">
          <a class="btn-candidatar" href="${linkAlerta(a)}" data-alerta-visto="${a.id}">Ver vagas</a>
          <button class="admin-acao-btn excluir" data-alerta-id="${a.id}">Excluir</button>
        </div>
      </div>
    `).join('');
  } catch {
    perfilAlertasEl.innerHTML = '<p class="vagas-carregando">Não foi possível carregar seus alertas.</p>';
  }
}

document.getElementById('formAlerta')?.addEventListener('submit', async (event) => {
  event.preventDefault();
  const form = event.target;
  const erroEl = document.getElementById('alertaErro');
  erroEl.hidden = true;

  try {
    const resposta = await fetch(`${API_BASE}/alertas`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${obterToken()}`,
      },
      body: JSON.stringify({
        cargo: form.cargo.value.trim() || null,
        categoria: form.categoria.value.trim() || null,
        cidade: form.cidade.value.trim() || null,
        estado: form.estado.value.trim().toUpperCase() || null,
      }),
    });
    const dados = await resposta.json();
    if (!resposta.ok) throw new Error(dados.detail || 'Não foi possível salvar o alerta');

    form.reset();
    mostrarToast('🔔 Alerta salvo!');
    carregarAlertas();
  } catch (erro) {
    erroEl.textContent = erro.message;
    erroEl.hidden = false;
  }
});

perfilAlertasEl?.addEventListener('click', async (event) => {
  const botaoExcluir = event.target.closest('[data-alerta-id]');
  if (botaoExcluir) {
    await fetch(`${API_BASE}/alertas/${botaoExcluir.dataset.alertaId}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${obterToken()}` },
    });
    mostrarToast('Alerta removido');
    carregarAlertas();
    return;
  }

  const linkVer = event.target.closest('[data-alerta-visto]');
  if (linkVer) {
    fetch(`${API_BASE}/alertas/${linkVer.dataset.alertaVisto}/marcar-visto`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${obterToken()}` },
    });
  }
});

/* ===== Histórico de candidaturas ===== */

async function carregarCandidaturasHistorico() {
  try {
    const resposta = await fetch(`${API_BASE}/minhas-candidaturas`, {
      headers: { Authorization: `Bearer ${obterToken()}` },
    });
    const candidaturas = await resposta.json();

    if (!candidaturas.length) {
      perfilCandidaturasEl.innerHTML = '<p class="vagas-carregando">Você ainda não se candidatou a nenhuma vaga por aqui.</p>';
      return;
    }

    perfilCandidaturasEl.innerHTML = `
      <div class="admin-tabela-wrap">
        <table class="admin-tabela">
          <thead><tr><th>Vaga</th><th>Empresa</th><th>Data</th></tr></thead>
          <tbody>
            ${candidaturas.map((c) => `
              <tr>
                <td>${c.vaga_id ? `<a href="/vagas/${escapeHtml(c.vaga_id)}">${escapeHtml(c.cargo || 'Vaga removida')}</a>` : escapeHtml(c.cargo || 'Vaga removida')}</td>
                <td>${escapeHtml(c.empresa || '—')}</td>
                <td>${new Date(c.criada_em).toLocaleDateString('pt-BR')}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `;
  } catch {
    perfilCandidaturasEl.innerHTML = '<p class="vagas-carregando">Não foi possível carregar seu histórico.</p>';
  }
}

/* ===== IA sob demanda: análise de perfil, gerador de currículo, simulador de entrevista ===== */

async function carregarAnalisePerfil() {
  const el = document.getElementById('iaAnalisePerfil');
  try {
    const resposta = await apiFetch(`${API_BASE}/ia/analise-perfil`);
    if (!resposta.ok) throw new Error();
    const dados = await resposta.json();

    el.innerHTML = `
      ${dados.pontos_fortes.length ? `
        <p><strong>Pontos fortes:</strong></p>
        <ul>${dados.pontos_fortes.map((p) => `<li>✅ ${escapeHtml(p)}</li>`).join('')}</ul>
      ` : ''}
      ${dados.sugestoes.length ? `
        <p><strong>Sugestões de melhoria:</strong></p>
        <ul>${dados.sugestoes.map((s) => `<li>💡 ${escapeHtml(s)}</li>`).join('')}</ul>
      ` : '<p>Seu perfil está completo, mandou bem! 🎉</p>'}
    `;
  } catch {
    el.innerHTML = '<p class="vagas-carregando">Não foi possível carregar a análise do perfil.</p>';
  }
}

document.getElementById('btnGerarCurriculo')?.addEventListener('click', async () => {
  try {
    const resposta = await apiFetch(`${API_BASE}/ia/gerar-curriculo`);
    if (!resposta.ok) throw new Error();
    const texto = await resposta.text();
    const blob = new Blob([texto], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'curriculo.txt';
    link.click();
    URL.revokeObjectURL(url);
  } catch {
    mostrarToast('Não foi possível gerar o currículo.');
  }
});

async function carregarCategoriasSimulador() {
  const select = document.getElementById('simuladorCategoria');
  try {
    const resposta = await fetch(`${API_BASE}/ia/simulador-entrevista/categorias`);
    if (!resposta.ok) throw new Error();
    const dados = await resposta.json();
    dados.categorias.forEach((categoria) => {
      const option = document.createElement('option');
      option.value = categoria;
      option.textContent = categoria;
      select.appendChild(option);
    });
  } catch {
    // sem categorias específicas, o select continua só com "Perguntas gerais"
  }
}

document.getElementById('formSimulador')?.addEventListener('submit', async (event) => {
  event.preventDefault();
  const categoria = event.target.categoria.value;
  const resultadoEl = document.getElementById('iaSimuladorResultado');
  resultadoEl.innerHTML = '<p class="vagas-carregando">Gerando perguntas...</p>';

  try {
    const query = categoria ? `?categoria=${encodeURIComponent(categoria)}` : '';
    const resposta = await apiFetch(`${API_BASE}/ia/simulador-entrevista${query}`);
    if (!resposta.ok) throw new Error();
    const dados = await resposta.json();

    resultadoEl.innerHTML = `
      <ol class="ia-simulador-lista">
        ${dados.perguntas.map((p) => `<li>${escapeHtml(p)}</li>`).join('')}
      </ol>
      <p class="modal-subtitulo">💡 ${escapeHtml(dados.dica)}</p>
    `;
  } catch {
    resultadoEl.innerHTML = '<p class="vagas-carregando">Não foi possível gerar as perguntas.</p>';
  }
});

function aoAutenticar() {
  iniciarPerfil();
}

renderAreaConta();
iniciarPerfil();
