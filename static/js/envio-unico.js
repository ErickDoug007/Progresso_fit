// Evita envio duplicado: depois do primeiro envio de um formulário, o botão de enviar fica
// desabilitado até a página responder. O servidor também bloqueia duplicatas (core/security.py);
// isto é só a camada de conveniência no navegador.
(function () {
  document.addEventListener('submit', function (evento) {
    const form = evento.target;
    if (!(form instanceof HTMLFormElement) || evento.defaultPrevented) return;

    if (form.dataset.enviando === '1') {   // segundo envio enquanto o primeiro está em andamento
      evento.preventDefault();
      return;
    }
    form.dataset.enviando = '1';

    // Desabilita depois que o navegador montou os dados do envio (senão o botão não seria enviado).
    setTimeout(function () {
      form.querySelectorAll('button[type="submit"], button:not([type]), input[type="submit"]')
        .forEach(function (botao) { botao.disabled = true; });
    }, 0);
  });

  // Voltar pelo histórico (cache do navegador) não pode deixar o formulário travado.
  window.addEventListener('pageshow', function (evento) {
    if (!evento.persisted) return;
    document.querySelectorAll('form').forEach(function (form) {
      delete form.dataset.enviando;
      form.querySelectorAll('button, input[type="submit"]').forEach(function (b) { b.disabled = false; });
    });
  });
})();
