# Configuração de e-mail

Em modo de desenvolvimento (`DEBUG=True`), o projeto usa SMTP quando
`EMAIL_HOST_USER` e `EMAIL_HOST_PASSWORD` estão definidos. Sem essas
credenciais, usa o backend de console do Django: os conteúdos e links dos
e-mails de confirmação são exibidos no terminal do `runserver`, sem envio real.

Para enviar e-mails pelo Gmail, defina no `.env`:

```dotenv
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_HOST_USER=seu-endereco@gmail.com
EMAIL_HOST_PASSWORD=sua-senha-de-aplicativo
DEFAULT_FROM_EMAIL=ProgressoFit <seu-endereco@gmail.com>
```

Com Gmail, `EMAIL_HOST_USER` deve ser a conta que envia a mensagem e
`EMAIL_HOST_PASSWORD` deve ser uma senha de aplicativo gerada nessa conta
Google; a senha normal da conta geralmente não autentica no SMTP. Se o servidor
continuar encerrando a conexão durante a autenticação, gere uma nova senha de
aplicativo e atualize o `.env`. Configure `DEFAULT_FROM_EMAIL` com o mesmo
endereço de `EMAIL_HOST_USER`. Mantenha essas credenciais privadas e não as
envie junto com o código.
