# Correções aplicadas

**Bugs**
- `.env`: `ANTROPIC_API_KEY` -> `ANTHROPIC_API_KEY` (faça isso no seu `.env`; ele não vem neste zip). `env-example` também ganhou a chave.
- Mensagens: removidos `message_storage.py` e `MESSAGE_STORAGE`. Agora o `base.html` exibe `messages` uma vez (blocos locais de `enviar_ranking.html` e `formulario_treino.html` removidos). `messages/logged_in.txt` e `logged_out.txt` ficaram vazios para não aparecer "Signed in as...".
- `metricas.js`: reescrito. Usa os ids reais do Django (`id_peso`, `id_altura`, `id_percentual_gordura`), calcula IMC e massa magra ao digitar, sem gráficos fictícios nem `salvarMedicao`.
- `metricas/models.py`: `quadril` duplicado removido (sem migration nova).
- `metricas/views.py`: campos herdados agora vêm de `form.fields` (inclui `deltoide`).
- `requirements.txt`: UTF-16 -> UTF-8.
- `treinos/views.py`: erro inesperado mostra mensagem fixa.

**Removidos**: 64 templates de `templates/account/` idênticos aos do allauth, `templates/fragmentos/`, `freeze`, `ShapeEvoluty/message_storage.py`, `core.views.home`, `admin/` duplicado em `core/urls.py`, `Perfil.NIVEL_CHOICES`, `clean_dias`, `EMAIL_BACKEND`, `ACCOUNT_UNIQUE_EMAIL`, provider `instagram`, `.distinct()`, parâmetro `usuario` de `_gerar_e_salvar_plano`.

**Encurtados**: `calcular_tempo_membro`, `CAMPOS_HERDAVEIS`, `imc`, admin do ranking (`list_editable`), `metricas_evolucao.js`, `configuracoes.js`.

**Fora do zip (faça você)**: trocar SECRET_KEY, senha de app do Gmail e chave da Anthropic (estão no histórico do git); `git rm -r --cached media`.
