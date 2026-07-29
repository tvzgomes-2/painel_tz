# Log de feedback

Registro cronológico de comentários recebidos sobre o painel, na forma de relatos brutos por rodada. Identidades anonimizadas (rótulo por papel/ordem de aparição — arquivo público no repositório, não nomes reais). Cada relato foi decomposto em itens de trabalho, mas o **status de implementação (feito/pendente, em qual versão) vive só no `ROADMAP.md`** (Fases 1-5, tabelas com coluna Status) **e no `CHANGELOG.md`** (o que de fato foi publicado) — não duplicado aqui, para não ter duas fontes de verdade divergentes.

## Entradas

### 2026-07-23 — Colega 1 (WhatsApp)

> Ficou bom, eu deixaria o título um pouco maior
> E para um futuro, se conseguir os dados, o número de viagens antes e depois da adoção, investimento antes e depois em infra...
> No mapa eu colocaria uma borda luminosa bem leve nos municípios que tem
> Deixaria a borda das UF tb, quando vc filtra só municípios com TZ eles aparecem flutuando
> Borda das UF é importante tb para referência de quem está vendo os mapas

Itens derivados: título maior; glow leve nos municípios TZ; borda de UF sempre visível; wishlist de dados (viagens e investimento antes/depois — eixo temporal, não está na base atual).

### 2026-07-24 — Colega 2 (print anotado)

> Acho que colocar as bordas dos limites municipais e estaduais, pq fica difícil ver assim muito escuro.
> No item "TZ × Não-TZ — comparação (recorte atual)", colocaria o título do tema um pouco maior ou em negrito, para destacar.
> Gostei que na tabela de tarifa zero, se clicar no tema, ela organiza de menor pra maior e maior pra menor.
> E de layout, deixaria as caixas alinhadas.

Itens derivados: bordas municipais/estaduais mais visíveis (reforça pedido do Colega 1); título da seção de comparação maior/negrito; positivo — ordenação por clique na tabela TZ está funcionando bem, manter; alinhar cards de resumo com a linha de controles abaixo.

### 2026-07-24 — Colega 1 (WhatsApp, com imagens de referência)

> Deixa um outer glow nos municípios ativos que tira um pouco a cara de Excel
> Mas bem de leve
> No título depois de tarifa zero coloca um (TZ)
> Bota uma opção para poder minimizar esses gráficos todos e aí dá para visualizar o mapa junto com a tabela
> Insisto na ideia de colocar as divisões estaduais para ter referência de localização
> Quando vc passa com o mouse por cima de um município com TZ pede para ele mostrar as informações daquele município que estão na tabela

Anexou 2 imagens de mapa-múndi com efeito de glow (verde, sobre fundo escuro) como referência de estilo, e um print do celular mostrando o painel já publicado (tvzgomes-2.github.io) para dar o contexto do que estava comentando.

Itens derivados: glow sutil nos municípios TZ (com referência visual agora); "(TZ)" no título; opção de colapsar os gráficos pra ver mapa+tabela juntos; bordas estaduais — 3º pedido, o mais insistido; tooltip do mapa mostrar os dados completos do município (mesmas colunas da tabela), não só a métrica do colorBy.

### 2026-07-24 — Colega 3 (áudio transcrito)

> Eu acho que a visualização fica bem melhor quando o fundo é branco. Não sei se você concorda, mas isso é questão de gosto. [...] Achei todos os dados aqui bem fáceis de analisar. Talvez separar mais aqui, tem o mapa, e à direita esse painel com vários gráficos ao mesmo tempo — dar um espaço maior entre eles, está muito junto na minha opinião. Ou se desse, cada um ter uma cor diferente, ou título em fonte maior, pra dar pra enxergar melhor. [...] Acho que está sensacional, ficou muito bom. Acho que o outro [v0.1] não tinha as notas metodológicas — isso é muito útil também para quem for consultar.

Itens derivados: preferência por fundo branco (opinião pessoal, ele mesmo relativiza); mais espaçamento entre mapa e painel lateral; cores/títulos diferentes por seção; positivo — notas metodológicas são um diferencial útil, manter e não cortar em versões futuras.

### 2026-07-24 — Colega 4 (comentário sobre o bloco "% por eixo")

> O n junto das % deixa um pouco confuso a leitura pq dá a entender que dá pra comparar os municípios as categorias entre si. Acho que dá pra revisar o título pra deixar mais claro que as proporções são sobre cada categoria
> Já tem um outro gráfico de barras muito parecido na sessão de cima que faz outra coisa (compara os municípios TZ com Não TZ). Acho que vale trocar a forma de apresentação de um deles pra dividir melhor cada informação. [...] quando vc bate o olho nesse segundo bloco a mente já puxa pra ideia de que deveria comparar entre eles tb - o que não reflete 100% do dado
> Tenta mexer um pouquinho no espaçamento entre a barra e a legenda tb, eu demorei pra entender que a legenda se refere à barra de cima e não a debaixo pq ele acabou ficando mais colado na inferior que na superior

Itens derivados: deixar explícito que % é dentro de cada categoria (não comparável entre categorias); diferenciar visualmente os dois blocos de barras (comparação pareada × proporção por categoria); corrigir agrupamento visual barra↔legenda (padronizar label→barra, igual ao bloco de cima).

> [mensagem separada] uma dúvida que não sei se dá pra fazer ou não [...] dá pra incluir um jeito de dar zoom no mapa coroplético. Como os municípios tão muito concentrados no sudeste, com ele travado na escala nacional fica difícil de selecionar um município específico pelo mapa.

Item derivado: zoom/pan no mapa (ver ROADMAP — Claude confirmou que é tecnicamente viável).

### 2026-07-24 — Colega 5 (e-mail)

> Mapa coroplético - aumentar a escala (tamanho) do mapa quando há seleção de uma UF específica, o ideal seria mostrar o mapa grande só da UF selecionada. Porque não consigo selecionar um Município específico qdo a dimensão dele é pequena (exemplo não consegui achar SCS);
> Quando seleciono uma UF específica e ando com o cursor no mapa fora da UF continua aparecendo os nomes dos municípios não selecionados;
> Acho que uma legenda ajudaria aos leigos no entendimento das seguintes siglas: IBEU, IDH, PDMU, Hierarquia REGIC, NTU, Arranjo Metropolitano (fora do arranjo, satélite do arranjo, sede/co-sede do arranjo)

Itens derivados: auto-zoom pra UF selecionada (reforça o pedido do Colega 4, com proposta de implementação mais específica); suprimir tooltip fora do recorte de UF; glossário de siglas pra leigos.
