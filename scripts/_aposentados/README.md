# Scripts aposentados (13/11/2026, v1.0.0)

Ficam aqui para consulta do histórico; nenhum entra no build (`scripts/build_tudo.sh`).

| Script | Por que saiu |
|---|---|
| `build_legislacao.py`, `build_legislacao_padrao.py` | liam o levantamento legal de 18/09/2026 e uma tabela consolidada que não está mais no cofre. Substituídos por `build_legislacao_base.py`, que lê a base congelada de 11/11/2026. |
| `build_crosswalk_sandbox.py` | rascunho do `build_crosswalk.py`. |
| `remontar_de_painel.py` | remontava o painel herdando os blocos pesados do próprio `painel.html`; com a base nova, herdaria dado antigo. O build completo (`build_tudo.sh`) roda. |
