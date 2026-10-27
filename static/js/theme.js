// Aplica o tema salvo assim que a página carrega, ANTES de qualquer coisa aparecer.
// Roda em toda página que incluir esse script.
(function () {
  const tema = localStorage.getItem('tema') || 'dark';
  if (tema === 'light') {
    document.documentElement.setAttribute('data-theme', 'light');
  }
})();