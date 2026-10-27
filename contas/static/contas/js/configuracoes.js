// Alternar tema claro/escuro. O theme.js já aplica o tema salvo ao carregar a página;
// aqui só sincronizamos o botão e salvamos a escolha.
document.addEventListener('DOMContentLoaded', () => {
  const root = document.documentElement;
  const themeBtn = document.getElementById('themeToggleBtn');

  themeBtn.classList.toggle('on', root.getAttribute('data-theme') !== 'light');

  themeBtn.addEventListener('click', () => {
    const claro = root.getAttribute('data-theme') !== 'light';
    if (claro) root.setAttribute('data-theme', 'light');
    else root.removeAttribute('data-theme');
    themeBtn.classList.toggle('on', !claro);
    localStorage.setItem('tema', claro ? 'light' : 'dark');
  });

  // Toggle de privacidade (visual por enquanto — salvar de verdade fica pra próxima etapa)
  const privacyBtn = document.getElementById('privacyToggleBtn');
  privacyBtn.addEventListener('click', () => privacyBtn.classList.toggle('on'));
});
