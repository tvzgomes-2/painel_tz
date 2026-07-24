# Log de feedback

Registro cronológico de comentários recebidos sobre o painel. Cada entrada vira um item no backlog abaixo. Marcar `[x]` ao corrigir e anotar em qual versão/commit entrou.

## Backlog (itens acionáveis)

- [x] Aumentar o tamanho do título do painel — **v3 (24/07/2026)**
- [x] Adicionar "(TZ)" no título, depois de "Tarifa Zero" — **v3**
- [x] ~~Outer glow bem sutil nos municípios ativos~~ — **descartado pelo autor (24/07/2026)**: preferência estética + risco de performance; na v3 os TZ ganharam contorno/stroke claro destacado (ver ROADMAP, registro de decisões)
- [x] **Borda dos estados (UF) sempre visível no mapa** — pedido 3x (Ivan, Carol, Ivan de novo) — **v3** (camada de UFs dissolvida dos municípios)
- [x] Deixar as bordas municipais mais visíveis no mapa em geral — **v3**
- [x] Destacar mais o título "TZ × Não-TZ — comparação (recorte atual)" (maior ou em negrito) — **v3**
- [x] Alinhar as caixas de resumo (cards) com os controles de filtro logo abaixo — **v3** (mesmo grid)
- [ ] Opção de minimizar/colapsar os painéis de gráficos (comparação TZ×Não-TZ e % por eixo) para ver o mapa junto com a tabela de municípios TZ sem rolar a página — *pendente (v4); glossário já é colapsável na v3*
- [x] Tooltip ao passar o mouse num município com TZ: mostrar as mesmas informações da linha dele na tabela — **v3**
- [x] Mais espaçamento entre o mapa e o painel lateral — **v3**
- [ ] Considerar cores/fontes de título diferentes por seção, para diferenciar visualmente os blocos (Gabriel) — *pendente (v4)*
- [x] Fundo branco (preferência do Gabriel) — **v3** como toggle claro/escuro, tema escuro continua o padrão
- [ ] (Futuro, depende de dados ainda não coletados) Número de viagens antes × depois da adoção da TZ, por município
- [ ] (Futuro, depende de dados ainda não coletados) Investimento em infraestrutura antes × depois da adoção da TZ
- [x] No bloco "% de municípios com Tarifa Zero por eixo": deixar claro que a % é dentro de cada categoria — **v3** (subtítulo)
- [ ] Diferenciar visualmente o bloco "% por eixo" do bloco "TZ × Não-TZ — comparação" (formas de apresentação distintas) — *pendente (v4); na v3 os dois blocos ganharam subtítulos explicando o que cada um compara, mitigação parcial*
- [x] Corrigir a associação visual barra↔legenda no bloco "% por eixo" — **v3** (rótulo acima da própria barra)
- [x] Auto-encaixe do mapa na seleção (UF filtrada → enquadra a UF; duplo clique → zoom local; botão "↺ Brasil") — **v3**; zoom/pan livre segue adiado (ver ROADMAP)
- [x] Ao selecionar uma UF no filtro, suprimir tooltip/hover dos municípios de fora do recorte — **v3**
- [x] Glossário de siglas (IBEU, IDH, PDMU, REGIC, NTU, arranjo metropolitano) — **v3** (bloco colapsável)

**Extras entregues na v3 (pedido da orientação):** cards de grandes números dinâmicos (reagem ao recorte, com aviso de amostra pequena; novo indicador "pessoas vivendo com TZ ativa" ≈ 7,6 mi) e linha do tempo das adoções/revogações por ano.

## Entradas

### 2026-07-23 — Ivan Pereira Pereira (WhatsApp)

> Ficou bom, eu deixaria o título um pouco maior
> E para um futuro, se conseguir os dados, o número de viagens antes e depois da adoção, investimento antes e depois em infra...
> No mapa eu colocaria uma borda luminosa bem leve nos municípios que tem
> Deixaria a borda das UF tb, quando vc filtra só municípios com TZ eles aparecem flutuando
> Borda das UF é importante tb para referência de quem está vendo os mapas

Itens derivados: título maior; glow leve nos municípios TZ; borda de UF sempre visível; wishlist de dados (viagens e investimento antes/depois — eixo temporal, não está na base atual).

### 2026-07-24 — Carol Mesquita (print anotado)

> Acho que colocar as bordas dos limites municipais e estaduais, pq fica difícil ver assim muito escuro.
> No item "TZ × Não-TZ — comparação (recorte atual)", colocaria o título do tema um pouco maior ou em negrito, para destacar.
> Gostei que na tabela de tarifa zero, se clicar no tema, ela organiza de menor pra maior e maior pra menor.
> E de layout, deixaria as caixas alinhadas.

Itens derivados: bordas municipais/estaduais mais visíveis (reforça pedido do Ivan); título da seção de comparação maior/negrito; positivo — ordenação por clique na tabela TZ está funcionando bem, manter; alinhar cards de resumo com a linha de controles abaixo.

### 2026-07-24 — Ivan Pereira Pereira (WhatsApp, com imagens de referência)

> Deixa um outer glow nos municípios ativos que tira um pouco a cara de Excel
> Mas bem de leve
> No título depois de tarifa zero coloca um (TZ)
> Bota uma opção para poder minimizar esses gráficos todos e aí dá para visualizar o mapa junto com a tabela
> Insisto na ideia de colocar as divisões estaduais para ter referência de localização
> Quando vc passa com o mouse por cima de um município com TZ pede para ele mostrar as informações daquele município que estão na tabela

Anexou 2 imagens de mapa-múndi com efeito de glow (verde, sobre fundo escuro) como referência de estilo, e um print do celular mostrando o painel já publicado (tvzgomes-2.github.io) para dar o contexto do que estava comentando.

Itens derivados: glow sutil nos municípios TZ (com referência visual agora); "(TZ)" no título; opção de colapsar os gráficos pra ver mapa+tabela juntos; bordas estaduais — 3º pedido, o mais insistido; tooltip do mapa mostrar os dados completos do município (mesmas colunas da tabela), não só a métrica do colorBy.

### 2026-07-24 — Gabriel Idu (áudio transcrito)

> Eu acho que a visualização fica bem melhor quando o fundo é branco. Não sei se você concorda, mas isso é questão de gosto. [...] Achei todos os dados aqui bem fáceis de analisar. Talvez separar mais aqui, tem o mapa, e à direita esse painel com vários gráficos ao mesmo tempo — dar um espaço maior entre eles, está muito junto na minha opinião. Ou se desse, cada um ter uma cor diferente, ou título em fonte maior, pra dar pra enxergar melhor. [...] Acho que está sensacional, ficou muito bom. Acho que o outro [v1] não tinha as notas metodológicas — isso é muito útil também para quem for consultar.

Itens derivados: preferência por fundo branco (opinião pessoal, ele mesmo relativiza); mais espaçamento entre mapa e painel lateral; cores/títulos diferentes por seção; positivo — notas metodológicas são um diferencial útil, manter e não cortar em versões futuras.

### 2026-07-24 — Daniel Fontoura (comentário sobre o bloco "% por eixo")

> O n junto das % deixa um pouco confuso a leitura pq dá a entender que dá pra comparar os municípios as categorias entre si. Acho que dá pra revisar o título pra deixar mais claro que as proporções são sobre cada categoria
> Já tem um outro gráfico de barras muito parecido na sessão de cima que faz outra coisa (compara os municípios TZ com Não TZ). Acho que vale trocar a forma de apresentação de um deles pra dividir melhor cada informação. [...] quando vc bate o olho nesse segundo bloco a mente já puxa pra ideia de que deveria comparar entre eles tb - o que não reflete 100% do dado
> Tenta mexer um pouquinho no espaçamento entre a barra e a legenda tb, eu demorei pra entender que a legenda se refere à barra de cima e não a debaixo pq ele acabou ficando mais colado na inferior que na superior

Itens derivados: deixar explícito que % é dentro de cada categoria (não comparável entre categorias); diferenciar visualmente os dois blocos de barras (comparação pareada × proporção por categoria); corrigir agrupamento visual barra↔legenda (padronizar label→barra, igual ao bloco de cima).

> [mensagem separada] uma dúvida que não sei se dá pra fazer ou não [...] dá pra incluir um jeito de dar zoom no mapa coroplético. Como os municípios tão muito concentrados no sudeste, com ele travado na escala nacional fica difícil de selecionar um município específico pelo mapa.

Item derivado: zoom/pan no mapa (ver backlog — Claude confirmou que é tecnicamente viável).

### 2026-07-24 — Ricardo Gomes (e-mail)

> Mapa coroplético - aumentar a escala (tamanho) do mapa quando há seleção de uma UF específica, o ideal seria mostrar o mapa grande só da UF selecionada. Porque não consigo selecionar um Município específico qdo a dimensão dele é pequena (exemplo não consegui achar SCS);
> Quando seleciono uma UF específica e ando com o cursor no mapa fora da UF continua aparecendo os nomes dos municípios não selecionados;
> Acho que uma legenda ajudaria aos leigos no entendimento das seguintes siglas: IBEU, IDH, PDMU, Hierarquia REGIC, NTU, Arranjo Metropolitano (fora do arranjo, satélite do arranjo, sede/co-sede do arranjo)

Itens derivados: auto-zoom pra UF selecionada (reforça o pedido do Daniel, com proposta de implementação mais específica); suprimir tooltip fora do recorte de UF; glossário de siglas pra leigos.
