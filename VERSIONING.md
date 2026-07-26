# Política de versionamento

Adotada em 25/07/2026. Documento canônico da regra — o CHANGELOG.md registra o histórico de mudanças por versão, mas a regra em si vive aqui.

**Escopo: por página, não por site.** O repositório é um site com páginas independentes (Painel Brasil, Rede da ARS, futuras) — cada uma com seu próprio banco de dados e seu próprio ciclo de vida. A regra abaixo é uma só, mas o número de versão é contado separadamente por página (ex.: Painel Brasil pode estar em v0.3 enquanto Rede da ARS ainda não tem nenhuma versão publicada).

O site como um todo não tem número de versão — tem uma **era**, nomeada com um modo de transporte, em ordem alfabética (como o Android fazia com sobremesas: Cupcake, Donut, Eclair...) — a primeira letra disponível de cada vez, sem precisar planejar a lista inteira com antecedência. A era muda só em eventos "major" no sentido definido abaixo (novo painel irmão publicado, ou redesign completo de alguma página) — não a cada patch/minor de uma página isolada. Era atual: **Andarilho** (A — desde a publicação do hub com 2 páginas, 25/07/2026). Próxima letra: B.

## Fase de prototipagem — v0.x

Enquanto o painel circula só entre orientação e equipe próxima (antes de ir para grupos de pesquisa), cada iteração soma um patch: v0.1, v0.2, v0.3...

Não há distinção patch/minor/major nessa fase — qualquer mudança (dado, feature, correção **ou regressão/hotfix**) sobe o número seguinte (+0.1). Não existe granularidade extra de hotfix (tipo "v0.3.1") no pré-lançamento — mesmo consertar algo que quebrou soma +0.1 normalmente.

## Lançamento — v1.0.0

Marca a saída da prototipagem: o painel é considerado pronto para circular fora do círculo próximo, em grupos de pesquisa.

## Pós-lançamento

| Tipo | Formato | Quando usar |
|---|---|---|
| Patch | v1.0.1, v1.0.2... | Dados atualizados/enriquecidos, correções pontuais, ou **renomear** coluna/variável existente. Estrutura de banco de dados igual. |
| Minor | v1.1.0, v1.2.0... | **Adicionar ou remover** variável/coluna no banco de dados. Reseta o patch para zero. |
| Major | v2.0.0 | Adição de um painel irmão (ex.: painel de empresas/grupos econômicos) **ou** redesign completo da interface. |

## Hierarquia de precedência

Quando várias mudanças acontecem na mesma iteração, vale a de maior peso — as outras não geram versão própria, entram "de carona":

1. Mudança estrutural de BD → sobe **minor** (mesmo que também tenha vindo com features novas ou dados atualizados).
2. Feature/melhoria implementada (sem mudança estrutural) → sobe **patch**.
3. Enriquecimento de dados (sem mudança estrutural, sem feature nova) → **não gera versão sozinho**, entra dentro do patch da vez.

## Exemplos aplicados

- Só atualizou o CSV com dados mais recentes, mesma estrutura → patch.
- Adicionou um gráfico novo, dados intactos → patch.
- Renomeou uma coluna existente (ex.: `tz_ano` → `ano_inicio_tz`), sem adicionar/remover variável → patch.
- Adicionou uma coluna nova na base municipal e um gráfico que a usa → minor (adicionar/remover coluna é o que manda, não a renomeação).
- Um patch (v1.0.1) sai numa segunda; na sexta da mesma semana entra uma mudança estrutural → o próximo é v1.1.0. O que mudou no v1.0.1 fica registrado só no CHANGELOG dessa versão, sem precisar ser repetido na entrada do v1.1.0.
- Lançou um painel irmão (ex.: painel de grupos econômicos/empresas) ou refez a interface do zero → major.

## Nota de remapeamento retroativo

As versões antes chamadas de v1, v2 e v3 (no CHANGELOG.md, na UI e no ROADMAP.md) foram renomeadas para v0.1, v0.2 e v0.3 em 25/07/2026 — mudança só de rótulo, sem alteração de conteúdo, para alinhar o histórico a esta política (Opção A entre as alternativas consideradas; ver ROADMAP.md § Registro de decisões).

## Refinamentos (25/07/2026)

Quatro ambiguidades da primeira versão desta regra foram resolvidas com o autor:

- Mudança estrutural de BD = **só adicionar ou remover** variável/coluna. Renomear não conta como estrutural (vira patch).
- Quando um patch e uma mudança estrutural coincidem na mesma janela de tempo, o que aconteceu no patch **fica só no CHANGELOG** — não precisa ser referenciado de novo na entrada do minor.
- Gatilhos de major: **adição de um painel irmão** ou **redesign completo de UI**. (Mudança de escopo territorial não entra como gatilho — o painel já cobre todo o território nacional com granularidade municipal, o nível mais fino possível; não há "escopo maior" para expandir.)
- Na fase de prototipagem (v0.x), regressões/hotfixes não têm marcação própria — **qualquer mudança soma +0.1**, sem granularidade extra.
