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

const searchForm = document.querySelector('.search-box');

if (searchForm) {
  searchForm.addEventListener('submit', (event) => {
    event.preventDefault();
    const [cargoInput, cidadeInput] = searchForm.querySelectorAll('input');
    console.log('Buscar vagas:', {
      cargo: cargoInput.value.trim(),
      cidade: cidadeInput.value.trim(),
    });
  });
}

document.querySelectorAll('.btn-candidatar').forEach((botao) => {
  botao.addEventListener('click', () => {
    const vaga = botao.closest('.vaga').querySelector('h3').textContent;
    console.log('Candidatura iniciada para:', vaga);
  });
});
