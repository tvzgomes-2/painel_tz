# Changelog e notas de metodologia

O site tem páginas independentes, cada uma com seu próprio número de versão (ver arquitetura em `ROADMAP.md` § 0). **Tudo abaixo é sobre a página Painel Brasil (`painel.html`, tag TZ)** — é a única página com histórico até agora. Quando `rede-ge.html` (Rede da ARS) for publicada, ganha sua própria seção de changelog, separada desta.

## Política de versionamento

Regra completa (fases, patch/minor/major, hierarquia de precedência, nota de remapeamento v1/v2/v3 → v0.1/v0.2/v0.3) em [`VERSIONING.md`](./VERSIONING.md). A regra é uma só para todas as páginas do site; o que muda é que cada página conta seu próprio número.

## v0.7 (atual — 2026-09-06)

Entrada do **CadÚnico** na base municipal: quatro variáveis novas, uma opção de mapa e uma barra comparativa. Adiciona coluna ao banco — na fase de prototipagem qualquer mudança soma +0.1 (ver `VERSIONING.md`).

**Dados novos (`build_data.py` → `data-muni`), fonte MDS/SAGI (API MI Social):**

- `cadunico_cobertura` — pessoas inscritas / população × 100, competência **ago/2025**. Cobertura 5.570/5.570.
- `cadunico_cobertura_2022` — mesma medida em **set/2022**, a competência que Gonçalves e Santini (2023) usam em Mariana.
- `cadunico_pes` — pessoas inscritas (ago/2025), valor absoluto.
- `cadunico_taxa_atualizacao` — % de famílias com cadastro dentro da janela oficial de atualização; é a medida do **estoque ativo** e o antídoto contra a leitura ingênua da cobertura.

**Interface:** nova opção de coloração do mapa (escala YlGnBu, distinta das já usadas); nova barra na comparação TZ × não-TZ; três linhas na ficha do município; valor no tooltip quando o mapa está colorido por CadÚnico; verbete no glossário.

**Validação antes de publicar:** o agregado nacional bate com o oficial da competência (90,5 mi / 203,1 mi = 44,6% em set/2022). As identidades internas do CadÚnico — faixa 1 + faixa 2 = até ½ SM, e + faixa 3 = total — fecham em 5.570/5.570 municípios nas duas competências.

**Três ressalvas gravadas nas notas metodológicas do painel** (não só aqui): (1) o CadÚnico mede inscrição mediada por capacidade de busca ativa do CRAS, não pobreza; (2) é estoque de cadastros, não fotografia — 62 municípios pequenos passam de 100% de cobertura, e aplicar a taxa de atualização derruba isso para 3; (3) as duas competências não são diretamente comparáveis: desde jun/2023 a renda vem do CNIS quando maior que a autodeclarada (IN nº 1/SAGICAD/MDS), e as réguas se moveram em direções opostas em termos reais — linha da pobreza R$ 210 → R$ 218 (+3,8%), meio salário mínimo R$ 606 → R$ 759 (+25,2%).

**⚠️ A barra comparativa exige cautela e a nota diz isso na cara do leitor.** Mediana bruta: 40,3% (TZ) contra 58,6% (não-TZ). Boa parte é composição — a cobertura cai com o PIB per capita (correlação de postos −0,69) e a TZ se concentra no Sudeste/Sul, de menor cobertura. Controlando por região a diferença encolhe (Sudeste −6,7 p.p.), inverte no Sul (+4,2 p.p.) e persiste no Nordeste (−12,4 p.p.). Não é achado; é ponto de partida para o recorte.

**Correções de ferramenta (dívida técnica, sem efeito no publicado):**

- `montar_html.sh` estava **sem os blocos `data-modal`, `data-grupos` e `data-legislacao`**, que o painel usa desde as Fases 11 e 8.4 — rodá-lo como estava geraria um painel quebrado. Corrigido.
- `remontar_de_painel.py` passa a **preferir a pasta `build/`** quando ela existe, em vez de sempre herdar os blocos pesados do `painel.html`. Sem isso não havia como regerar a base municipal com colunas novas.
- `build_data.py` aceita a variável de ambiente `TZ_VAULT` para apontar o cofre, sem editar o script.

**⚠️ Pendências herdadas, não resolvidas nesta rodada:**

- O badge da interface exibia **v0.5** enquanto o CHANGELOG registrava v0.6 — corrigido agora para v0.7, mas fica o registro de que a v0.6 não atualizou o rótulo.
- A duplicata **Arthur/Artur Nogueira-SP** foi resolvida no cofre em `Tipologias TZ - consolidado.xlsx`, mas **persiste em `Municípios TZ - consolidado.xlsx`** (a fonte deste painel). O dedup por código IBGE segue tratando sem quebrar; é pendência de qualidade na planilha-mestre.
- A nota metodológica sobre São Caetano do Sul ("consta aqui como Ativa") está **desatualizada** — o painel já o classifica como parcial/grupo social. Texto do autor, não reescrito.

## v0.6 (2026-09-04)

Patch de dados — auditoria completa das 208 fichas municipais contra a base-mestre (cofre), com achados gravados e investigação dirigida (WebSearch/WebFetch) de divergências abertas. Estrutura de banco intacta (mesmo schema) — enriquecimento de dados, sem feature nova, entra como patch (ver `VERSIONING.md` § hierarquia de precedência).

**Correções na base municipal (`build_data.py` → `data-muni`):**

- **Itararé/SP:** ano de início corrigido de 2021 para 2022 (nenhuma evidência de operação antes da lei sancionada).
- **Santo Antônio de Posse/SP:** ano de início corrigido de 2024 para 2021 (fonte jornalística especializada + prefeitura, mesma data, 30/06/2021).
- Total de municípios com TZ universal no painel passa de **169 (159 ativas + 10 encerradas)** para **175 (165 ativas + 10 encerradas)** — reflete adições canônicas já feitas ao cofre desde a última atualização do painel (26/08/2026), não só as duas correções acima.
- ⚠️ Confirmada, sem alteração: a duplicata de código IBGE identificada em julho (Palmas-TO, dois episódios de universalidade) tem uma **segunda ocorrência do mesmo tipo**, achada nesta rodada — Arthur Nogueira/Artur Nogueira-SP (mesmo município, duas grafias, ambas "Ativa"/2021). O dedup por código IBGE (`keep='first'`) já tratava isso sem quebrar o pipeline; registrado aqui para constar — é uma pendência de qualidade de dado da planilha-mestre, não deste painel.

**Legislação (`data-legislacao`, 8.4 — 10 de 137 registros resolvidos ou corrigidos):**

- **Resolvidos com fonte nova (norma confirmada ou trocada):** Maricá/RJ (LC 244/2014, não a Lei 2.185/2006), Aquiraz/CE (Lei 1.279/2018, não a Lei 1.174/2016), Itapeva/SP (Decreto 11.829/2021, não a Lei 4.039/2017 — que é só reorganização geral), Eusébio/CE (Lei 1.024/2011, não a Lei 960/2010 — que trata de transporte intermunicipal), Piumhi/MG, Ilha Comprida/SP e Ijaci/MG (normas localizadas onde antes constava "não encontrei").
- **Corrigidos (ano ou data):** Itararé/SP (ano 2021→2022), Santo Antônio de Posse/SP (ano 2024→2021), Pitanga/PR (data da lei: 11/nov→22/dez/2011).
- Cobertura do crosswalk sobe de 62 para **65 normas identificadas em 137** (confiabilidade alta 37→40).
- ⚠️ **O que NÃO foi feito nesta rodada:** a sincronização de 137 para os 155(+) municípios canônicos do levantamento legal — pendência já registrada em `Pendências.md` do cofre, meramente confirmada como ainda aberta, não fechada aqui. Aparecida/SP e Igaratá/SP, por exemplo, têm norma confirmada na base-mestre do cofre mas não entraram neste crosswalk por não estarem nos 137 originais.

**Camadas da régua descritiva (`data-camadas`):**

- **São Caetano do Sul/SP adicionado** (camada 4, grupo social) — universalidade revogada em 15/07/2026; a base principal já registrava isso desde então (`tz_status = "Reclassificada (parcial — grupo social)"`), mas o crosswalk de camadas nunca tinha sido atualizado para refletir a mudança. Antes desta correção, o card do município não mostrava nenhuma camada da régua descritiva para São Caetano.
- Florianópolis continua com o flag "REVER" registrado em v0.4.02 (conflito de status não resolvido) — fora do escopo desta rodada.

**Infraestrutura de build (achado, corrigido nesta rodada):**

- 🔴 **`montar_html.sh` estava desatualizado desde a v0.5 (26/08/2026) — não incluía os blocos `data-modal`, `data-grupos` e `data-legislacao`.** Rodar o script tal como documentado no README teria remontado o `painel.html` **sem partição modal, sem grupos econômicos e sem legislação** — uma regressão silenciosa de três eixos de dado inteiros. Detectado por verificação pós-build (checagem dos 9 blocos esperados) antes de qualquer publicação; corrigido nesta rodada remontando com um script equivalente ao `remontar_de_painel.py` (mesma ordem de 9 blocos), mas alimentado com `build/` fresco em vez de herdar os blocos pesados do painel anterior. **`montar_html.sh` precisa ser atualizado para incluir os 3 blocos que faltam** — não corrigido aqui para não misturar mudança de infraestrutura de build com patch de dados; registrar como pendência.
- Geometria (`geo.topojson`) reaproveitada do `painel.html` anterior — não mudou desde a última publicação, então `preparar_geometria.sh` não foi executado.

**Verificação:** todos os 9 blocos JSON validados individualmente (`json.loads`) e todas as marcas estruturais esperadas (`#grupos`, `#regiaoUf`, `#dispersao`, `#muniSearch`, `#clearAll`) conferidas no arquivo remontado antes de sobrescrever `painel.html`. Sem navegador disponível neste ambiente para verificação visual em Chromium headless (diferente da v0.5) — spot-check feito lendo os blocos de dados diretamente (Itararé, Santo Antônio de Posse, São Caetano do Sul, Teresina, Maricá, Aquiraz, Eusébio, Itapeva).

## v0.5 (2026-08-26)

Fase 11 completa (Blocos 1–3) **mais três itens de dívida antiga** — 3.3, 3.4 e 8.4, abertos desde v0.3 e julho/2026. Ao todo: 5 correções, 5 mudanças de navegação, 2 gráficos que nunca tinham sido feitos e **três dados novos** — partição modal por município, legislação municipal e grupos econômicos do transporte. Este último é o eixo central da hipótese da tese, que até esta versão o painel registrava como "variável ainda ausente". Iteração nova por direito próprio, não sub-patch de v0.4.

**Dado novo — grupos econômicos por município (11.10, 11.11):**

- `scripts/grupos_por_municipio.json` — 796 municípios, 327 grupos, 1.603 pares, chave = código IBGE. Derivado de `_data/Cruzamento GE x TZ (ago-2026)/municipio_x_grupo.csv` (cofre).
- Painel novo "Grupos econômicos do transporte — concentração territorial": top 15 por alcance, responde ao recorte (Brasil 327 grupos → RJ 51 → SE 8 → AC 4), mostrando quantos municípios de cada grupo têm TZ. Maiores alcances: Viação Santa Cruz 58, Eurovida Holding 56, Expresso São Luiz 56, Lessa Carvalho/Aguiar-Carvalho 54, Maldonado 52, Gurgacz 51, Barata 44.
- Seção no card do município. Quando não há grupo mapeado, o card **diz** que o levantamento cobre 796 dos 5.570 e que ausência ali não é ausência de operador.
- **Exposição mínima, por decisão do autor (26/08/2026):** só nome e contagem. Ficam fora do painel CNPJ, capital, porte e qualquer narrativa de caso. O escore `cnpj_nucleo_*` embargado em 26/07/2026 **continua fora** — a decisão não o libera.
- **Homônimos (achado):** 20 nomes são sobrenomes usados por grupos distintos ("Santos" são 7 grupos). O alcance é contado por id de grupo, não por nome, e os ambíguos ganham o código no rótulo. Os 12 maiores não são homônimos, então o topo do gráfico não muda. Ver Pendência 11.15.
- Nota metodológica reescrita: a que dizia "variável ainda ausente" foi substituída por três ressalvas de leitura — cobertura não aleatória, homônimos, e o que o dado não prova (presença societária mapeada ≠ opera hoje ≠ atuou contra a TZ).

**Dado novo — partição modal por município (11.9):**

- `scripts/modal_por_municipio.json` — **5.570 municípios**, cobertura total, chave = código IBGE. Derivado de `_data/sidra_censo2022/censo2022_matriz_modal_por_municipio.csv`.
- Barra empilhada no card do município nos mesmos 5 baldes do gráfico nacional (ônibus, automóvel, motocicleta, ativo, outros), mais a frase do modo principal.
- A soma bruta dos percentuais do Censo varia (mediana 98,75%): os valores são normalizados para 100% e a soma bruta fica no campo `t`. Nos 123 municípios com soma < 95%, o card avisa que normalizou.

**Correções (Bloco 1):**

- **11.2 — ano errado ao lado das citações.** O campo `ano` do crosswalk guarda o ano de adoção da TZ no município, não o de publicação; era exibido colado na citação, de modo que as 5 fontes de Itatiaiuçu apareciam como "(2015)" e "Santini 2019 (2015)" se lia como se fosse a data da obra. O ano saiu da citação e continua onde faz sentido (linha "Início TZ", coluna "Início").
- **11.14 — 10 citações sem referência (regressão de v0.4.05).** A rodada anterior somou 15 fontes ao crosswalk mas deixou `REFERENCIAS_ABNT` com 5 entradas. A lista agora tem 15 e cobre todas as citações em uso; e ficou uma trava: `auditarReferencias()` roda no carregamento e denuncia órfãs no console e na própria seção. Foi a ausência dessa checagem que deixou a regressão passar.
- **11.3 — seção de referências.** Lista única, movida para o fim da página. A segunda lista ("Referências adicionais") saiu: expunha notas internas de trabalho ao leitor ("a conferir antes de citar", "⚠ possível duplicata") e 3 fontes de dado que não são bibliografia de TZ. As pendências bibliográficas em si continuam abertas (Pendência 11.13).

**Navegação e leitura (Bloco 2):**

- **11.4** botão "✕ Limpar tudo" — zera filtros, busca, seleção e enquadramento de uma vez; desabilitado quando não há nada a limpar. O `↺ Brasil` que já existia reseta só o mapa.
- **11.5** busca de município cobrindo os 5.570 — antes, os 5.401 não-TZ só eram acessíveis clicando no mapa. `datalist` preenchido sob demanda (máx. 40 sugestões), não 5.570 `<option>` no DOM.
- **11.6** nomes de fonte de dado saíram dos rótulos de menu e do card; a atribuição vive no glossário (verbete novo "Modelo de prestação") e no rodapé.
- **11.7** camada da régua descritiva virou tag no topo do card, ao lado do status de TZ.
- **11.8** card novo "Com sistema de ônibus declarado" (nacional 1.727), com a ressalva de amostra de 31% no próprio rótulo.

**Dívida antiga quitada — 3 itens que nunca tinham sido implementados:**

- **3.3 — TZ por região e por UF** (aberto desde v0.3). Dois blocos de barras horizontais com a proporção de municípios com TZ *dentro de* cada categoria, o `n` (TZ/total) junto de cada %, respondendo ao recorte. Deixou visível uma assimetria que o painel não mostrava: **RJ com 20,7% dos municípios em TZ (19/92)**, mais que o dobro de SP (9,0%); Nordeste com 0,3% (6/1.794) e 9 UFs zeradas.
- **3.4 — dispersão PIB per capita × motorização** (aberto desde v0.3). Os 5.570 municípios do recorte em SVG: não-TZ em cinza tênue, TZ por cima em amarelo (ativa) e rosa (encerrada). Eixo X em escala log — em escala linear quase todos virariam uma mancha à esquerda. Mostra o que a comparação de medianas comprimia em duas barras: os municípios TZ **não** estão no aglomerado de menor PIB; concentram-se na faixa média-alta, e a sobreposição com os não-TZ é grande.
- **8.4 — legislação da TZ por município** (pedido de 27/07/2026). `scripts/legislacao_tz.json`, extraído do levantamento legal do cofre (jul/2026). Os 137 municípios casaram por código IBGE sem exceção, e os totais batem com o resumo executivo da própria fonte (62 com norma, 75 sem; confiabilidade alta=37, média=22, baixa=3). No card: seção "Base legal" com a norma, etiqueta de confiabilidade, mecanismo de gratuidade (23 casos, extraídos da análise de conteúdo das 62 normas) e fundo municipal criado na própria lei (7 casos). 136 dos 169 municípios TZ têm verbete; nos 33 que entraram depois do levantamento, o card **diz** que não foi verificado, em vez de deixar o silêncio sugerir ausência de norma. Não entram no painel a coluna "Zotero" (controle bibliográfico interno) nem os fragmentos de tarefa das observações; as ressalvas substantivas entram — mostrar "Lei 2.185/2006" para Maricá sem dizer que a fonte aponta a LC 244/2014 seria pior que não mostrar.

**Infraestrutura de build:**

- `scripts/remontar_de_painel.py` (novo) — remonta `painel.html` a partir de `head.html` + `logic.js` + os crosswalks, herdando do painel atual os 3 blocos pesados que só o build gera (`geo.topojson`, `stats`, base colunar). Fecha a brecha que o CHANGELOG registrava desde 26/07/2026: sem a pasta `build/`, cada rodada vinha sendo replicada à mão em `head.html` e `painel.html`, e essa réplica manual é a origem de qualquer divergência entre fonte e publicado. Valida cada bloco como JSON e confere marcas esperadas antes de gravar. Quando a `build/` existir, o `montar_html.sh` segue sendo o fluxo canônico.
- Esta versão foi verificada em navegador (Chromium headless): zero erro de página, os 5.570 registros de modal e 796 de grupos carregados, auditoria de bibliografia sem órfãs, e o "Limpar tudo" restaurando o estado inicial.

## v0.4.05 (2026-08-26)

Sub-patch de v0.4 (mesma exceção do v0.x.NN — precedente v0.4.01, "referências bibliográficas adicionais", ver `VERSIONING.md`): 15 novas entradas de fonte acadêmica no crosswalk `scripts/casos_por_fonte.json`, extraídas do artigo de revisão sistemática do próprio autor sobre a literatura de Tarifa Zero no Brasil (Gomes, 2026 — trabalho da disciplina PGT-092/UFABC, evolução do artigo apresentado no XXIV CLATPU). Estrutura de banco intacta (mesmo schema de fonte) — sub-patch, não patch inteiro.

**Novas fontes linkadas por município** (só onde o artigo nomeia o município explicitamente — nada extrapolado de contagens agregadas):

- Mariana/MG: + Campos et al. 2023, Gonçalves \& Santini 2023, Santini 2023 (dissertação)
- Vargem Grande Paulista/SP: + Landin 2022, Costa \& Sampaio 2024, Gomes et al. 2023
- São Caetano do Sul/SP: + Santini et al. 2024
- Monte Carmelo/MG: + Lopes \& Muniz 2021
- Agudos/SP: + Angelo 2023 (o TCC já cobria o município, mas a entrada nunca tinha sido crosswalkada)
- Maricá/RJ: + Lima \& Kraus Junior 2021
- Caeté/MG, Caucaia/CE, Itapeva/SP: + Pereira 2024 (dissertação — obra diferente do já existente "Pereira 2023")
- Cerquilho/SP: + Gomes et al. 2023
- **Guararema/SP (novo no crosswalk — não tinha nenhuma fonte antes desta rodada):** + Gomes et al. 2023

**Divergências de dado encontradas na checagem cruzada, sinalizadas e não corrigidas nesta rodada** (mesma cautela do caso São Caetano do Sul/Florianópolis, v0.4.02 — ver Pendência 8.7 e nova 8.9 no ROADMAP):

- **Araçoiaba da Serra/SP** é citada no artigo do próprio autor (Gomes, Baiardi \& Zioni, 2023) como um dos 4 casos da macrometrópole paulista, mas `tz_status` no painel é **"Não TZ"** — nenhuma fonte foi adicionada para esse município até confirmação do autor contra a fonte primária.
- **Guararema/SP** — o mesmo artigo (publicado mar/2023) já trata o município como caso de TZ, mas o painel registra `tz_ano=2025` — a fonte foi adicionada, com a divergência anotada na própria descrição exibida no card.
- Cardozo et al. (2024, 106 municípios) e Cardozo et al. (2025, 44 municípios) citam volume de casos via PCA/clusterização, mas não os nomeiam individualmente no artigo disponível — não deu para crosswalkar sem o artigo/dataset completo.
- NTU citado no artigo do autor como "NTU, 2024" pode ou não ser a mesma publicação já crosswalkada como "NTU 2023" — ano diverge, não confirmado.

## v0.4.04 (2026-08-03)

Ampliação do universo canônico da pesquisa (155→170 municípios TZ universal) + parágrafo descritivo de TZ por município. Estrutura de banco intacta (mesmas colunas) — patch, não minor.

**Ampliação do universo canônico:**

- A pesquisa somou **16 casos próprios** de duas varreduras (141 candidatos verificados em 31/07/2026; funil orçamentário via SICONFI em 03/08/2026): **15 municípios com TZ universal ativa** (Maracaí/SP, Jucás/CE, Centenário do Sul/PR, Lidianópolis/PR, Venda Nova do Imigrante/ES, Brodowski/SP, Engenheiro Beltrão/PR, Tarumã/SP, Pains/MG, Rio das Flores/RJ, São Sebastião da Grama/SP, Águas de São Pedro/SP, Pedregulho/SP, Quaraí/RS, Colina/SP) e **1 encerrada** (Getulina/SP, programa "AMIGÃO", 13/04/2026→27/07/2026, encerrado por baixa demanda). Nenhum desses 16 usa a expressão "tarifa zero" nas fontes — todos usam nome próprio de programa, o que já era invisível às buscas usadas até agora.
- **5 novos casos de TZ parcial** (régua descritiva): Andrelândia/MG e Embu das Artes/SP (temporal-dias); Áurea/RS e Magé/RJ (espacial); Parauapebas/PA (grupo social, caso de transição legislativa). Áurea e Magé têm reclassificação sinalizada como **provisória** (a confirmar pelo autor) — a régua descritiva original as descrevia como "TZ ativa" bruta, mas o serviço não é circular intraurbano típico; o painel mostra a ressalva no card de detalhe do município.
- **Teresina/PI excluída do universo universal**: é um programa **estadual** de Metrô/VLT, não Tarifa Zero de ônibus municipal — a pesquisa cobre só sistemas de ônibus (decisão do autor, 03/08/2026). O registro **não foi apagado** dos dados (`tz_status` passa a `"Excluída (Metrô/VLT estadual — fora de escopo, 03/08/2026)"`, uma string que não bate com `'Ativa'`/`'Encerrada'` e por isso não conta em `tz_bin`), só sai da tabela pública e dos destaques — critério que já vinha sendo usado para casos como o de São Caetano do Sul (base desatualizada vs. cofre). Teresina era, até então, o maior "sede TZ" do painel (866 mil hab.) — o destaque agora passa para Itapetininga/SP.
- Totais recalculados com a mesma lógica de `scripts/build_stats.py` (medianas, crosstabs, cortes por faixa/REGIC/arranjo/modelo, destaques) — não só os números do topo. Painel: **159 ativas + 10 encerradas = 169** municípios TZ universal (número um pouco abaixo do canônico do cofre, 170, por uma divergência pré-existente e não resolvida nesta rodada — Palmas-TO aparece 2× no arquivo-fonte como "Encerrada" com datas diferentes, mas o modelo de dados do painel tem uma linha por município). **33 municípios** com TZ parcial (era 28).
- **Achado de qualidade de dado, registrado:** o dataset municipal do painel (base MUNIC/IBGE) usa o nome pré-2007 "Embu" para o que hoje é oficialmente Embu das Artes/SP (mesmo código IBGE, 3515004) — `camadas_tz.json` ganhou uma chave duplicada (`"Embu|SP"`) só para não perder o cruzamento; o nome exibido no painel é o do dataset ("Embu"), o vault da tese mantém o nome atual correto.
- Genealogia completa, ressalvas e decisões (inclusive as 3 reclassificações provisórias) documentadas em `CLAUDE.md` e `Pendências.md` do cofre da tese — não duplicadas aqui, ver lá para o detalhe acadêmico.

**Novo: parágrafo descritivo de TZ por município:**

- O card "Município selecionado" ganhou um parágrafo gerado por template (não escrito à mão — cobre todos os municípios do painel, TZ ou não) logo abaixo do nome, explicando a situação de Tarifa Zero daquele município: universal ativa (com início e operador, se houver), encerrada (com período), parcial (com a(s) camada(s) e ressalva de reclassificação provisória, se houver), excluída por escopo (caso Teresina) ou sem TZ mapeada (com a ressalva de que o painel já mediu subnotificação em varreduras anteriores, então ausência aqui não é prova de ausência real). Implementado em `gerarParagrafoTZ()`, reaproveitando os mesmos campos já estruturados (`tz_status`, `tz_ano`, `tz_fim`, `tz_operador`, `camadasFor()`).

## v0.4.03 (2026-07-29)

Sub-patch de v0.4 (mesma exceção do v0.x.NN, ver `VERSIONING.md`): rodada de 8 pontos de melhoria pedidos pelo autor sobre o v0.4.02 ("Tudo nesta rodada (v0.4.03)"), cobrindo rodapé, identidade visual do mapa, régua descritiva, uma página nova de conceitos e um primeiro score de população.

**Rodapé — logo do Laplan + hiperlinks:**

- Logo do Laplan processado a partir do arquivo fornecido pelo autor (recorte + conversão seletiva de preto/cinza para branco, preservando o vermelho e a transparência) e adicionado ao rodapé de `painel.html`, `index.html` e `pesquisa.html`, no mesmo tratamento negativo já usado para PGT/UFABC. **Limitação conhecida:** o arquivo de origem é um recorte de thumbnail do WordPress que trunca o texto "LABORATÓRIO DE" antes do nome completo do instituto — usado assim por falta de um arquivo-fonte melhor.
- Todos os logos do rodapé (UFABC, PGT, Laplan, POLO) ganharam hiperlink para o site oficial de cada instituição, nas três páginas.

**Régua descritiva — gradação por saturação (substitui o contorno tracejado do v0.4.02):**

- O contorno tracejado amarelo (`.tzparcial`) do v0.4.02 foi identificado pelo autor como uma visualização ruim e foi substituído por **preenchimento em variação de saturação do amarelo** (`corParcial()`): quanto mais camadas parciais (2a/3/4) um município acumula, mais perto do amarelo pleno ele fica — sem nunca chegar lá, para não ser confundido com a universal. Gradação por **contagem de camadas**, não por tipo (não há hierarquia documentada entre 2a/3/4 na régua). Fica dentro da família do amarelo já usado para TZ ativa — não introduz cor nova, mantém a regra da identidade visual.
- Legenda do mapa (quando colorido por status de TZ) passa a mostrar 3 amostras de gradação (1/2/3 camadas) em vez do símbolo de contorno tracejado.

**Filtro por camada da régua:**

- Novo seletor "Régua descritiva (camada)" nos controles do painel — filtra o mapa e a tabela por universal (1), temporal-dias (2a), espacial-periférica (3) ou grupo social (4). Reage junto com os demais filtros (UF, faixa, REGIC, arranjo, modelo).

**Seção "TZ × Não-TZ" redesenhada:**

- Sai da coluna lateral do mapa e vira uma caixa de largura total, abaixo do mapa, com as métricas organizadas em **colunas** (grid responsivo) em vez de empilhadas — mesmo conteúdo (medianas por indicador), só reorganizado.

**Nova página `verbetes.html`:**

- Página pública nova, no mesmo padrão visual do site, com os 5 verbetes já liberados no cofre da tese: **Tarifa Zero**, **Grupos econômicos** (os dois pilares da hipótese) e **A Régua da Tarifa Zero** / **Régua Descritiva** / **Régua Analítica** (o instrumento de medição, Eixo 3). Lista, sem linkar, os outros 12 verbetes já escritos mas ainda represados pelo autor — mesma decisão de liberação progressiva já adotada no cofre (`Verbetes - MOC.md`).
- Link para a página adicionado no cabeçalho de `painel.html` e `pesquisa.html`, e como novo card na página inicial (`index.html`).

**Score: população abrangida pela Tarifa Zero (v1):**

- Nova seção no painel somando quantas pessoas têm algum acesso a alguma camada de TZ. Metodologia v1 aprovada pelo autor (29/07/2026): camada universal soma 100% da população residente do município; camada 4/grupo social soma uma **estimativa** só quando há dado defensável — hoje só Belo Horizonte e Uberlândia (passe estudantil), usando "estudo_total" do Censo 2022 (proxy de deslocamento para estudo, carregado em `camadas_tz.json`) como aproximação do número de beneficiários, não a contagem real.
- **Deliberadamente não somado:** as demais camadas parciais sem dado sub-municipal defensável (temporal-dias/2a, espacial/3, e o caso de Curitiba/desempregados na camada 4) — o painel lista esses municípios como "sem estimativa" em vez de estimar sem base. Gratuidades por lei federal (idoso/PcD) também não somadas nesta v1: a base municipal não tem população idosa/PcD por município (pendência registrada em `Pendências.md` do cofre, 29/07/2026).
- Card de detalhe do município passa a mostrar a população estimada (quando existente) junto de cada camada da régua descritiva.

**Ajustes pós-uso (mesmo dia, dois pontos pedidos pelo autor depois de ver o v0.4.03 em uso):**

- Tabela "Municípios com Tarifa Zero universal" renomeada para "Municípios com Tarifa Zero (universal + parcial)": além dos 155 registros/154 municípios únicos da base-mestre universal, agora lista os **28 municípios com camada parcial** (2a/3/4, `camadas_tz.json`) que ainda não estavam no bucket universal — mesma regra de exclusividade já usada no card "TZ parciais" e no mapa (evita duplicar, por exemplo, Palmas e São Caetano do Sul, que a base principal já classifica como Ativa/Encerrada). Nova tag "Parcial" (amarelo) na coluna Situação; coluna "Início" usa uma extração best-effort de ano a partir do texto de "detalhe" de cada camada — 14 dos 28 municípios têm um ano identificável, os demais ficam "—" (sem inventar data).
- Cor de TZ ativa volta a ser **verde** (era amarelo desde a Fase 9) — mapa, tags, tabela e linha do tempo; amarelo fica reservado à gradação de TZ parcial (`corParcial`, acima), rosa continua em Encerrada/revogação. **Nota de identidade visual:** essa combinação usa verde + amarelo + rosa no mesmo painel, o que a princípio conflita com a regra de "nunca combinar duas das três cores (amarelo/azul/verde) entre si" da nota "Identidade Visual da Pesquisa" — regra pensada para peças gráficas isoladas (cartaz, slide), não para um painel com várias camadas de informação simultâneas que precisam ser distinguíveis. Registrado aqui como exceção deliberada, a formalizar na nota de identidade visual se o autor confirmar o critério para painéis multi-camada.
- Linha do tempo ganha o início das TZ parciais (amarelo), **empilhado** sobre a barra da universal (verde) em cada ano, com uma única escala vertical compartilhada — usa o mesmo `camadaAnoInicio()` da tabela. Primeira tentativa desenhou as duas séries lado a lado com escala própria cada uma; o autor notou que isso distorcia a leitura (uma barra pequena parecia tão alta quanto uma grande de outra série) — corrigido para empilhado/escala única no mesmo dia. Casos sem data identificável (passe estudantil de BH/Uberlândia, desempregados de Curitiba) não entram no gráfico. Revogações continuam abaixo do eixo, em rosa.
- Ordem de empilhamento das camadas no mapa reorganizada: não-TZ (base) → ativa → parcial → encerrada (topo) → limites de UF, cada uma em seu próprio grupo SVG (antes, ativa e encerrada dividiam um grupo único e parcial ficava junto do não-TZ). Legenda reordenada para acompanhar: Ativa, Parcial (1/2/3 camadas), Encerrada, Não TZ.
- Rampa de cor do parcial invertida: amarelo mais forte com **1** camada, decaindo (mais próximo do neutro) conforme acumula camadas — antes era o oposto (mais fraco com 1, mais forte com 3+).
- Linha do tempo ganha tooltip customizado (reaproveita o mesmo `#tooltip` do mapa) que lista os municípios ao passar o mouse sobre qualquer segmento da barra (universal, parcial ou revogação) — antes só mostrava a contagem via `<title>` nativo do SVG.
- Rodapé reestruturado em `painel.html`, `index.html`, `pesquisa.html` e `verbetes.html`: nomes (autor + orientadora) agora ficam agrupados de um lado (`.fnames`, empilhados), logos institucionais do outro (`.flogos`) — antes o autor ficava misturado com os logos de um lado e só a orientadora do outro, layout assimétrico. Logo da UFABC trocado da variante "sigla-lateral" (proporção ~1,64, lia-se pequena/quadrada) para a "extenso" (proporção ~4,95), agora com peso visual comparável a PGT/Laplan na mesma altura fixa de 46px.
- `verbetes.html`: removido o bloco de observação "Mais 12 verbetes escritos, ainda represados" — a decisão de liberação progressiva continua válida, só a caixa de aviso sobre os não publicados saiu da página pública.
- `FEEDBACK.md` e `ROADMAP.md`: identidades dos 5 leitores que deram feedback (nomes reais) substituídas por rótulos de papel (Colega 1-5, por ordem de 1ª aparição cronológica) em ambos os arquivos — são rastreados num repositório público (github.com/tvzgomes-2/painel_tz). A checklist de status que existia em `FEEDBACK.md` (desatualizada, parava em 25/07) foi removida de lá para não duplicar/divergir do que já é mantido aqui e no `ROADMAP.md`; `FEEDBACK.md` agora guarda só os relatos brutos, e o `ROADMAP.md` ganhou colunas de Status nas tabelas das Fases 1-3 (Fase 4 já tinha) para centralizar o que foi/não foi implementado.

## v0.4.02 (2026-07-29)

Sub-patch de v0.4 (mesma exceção do v0.x.NN, ver `VERSIONING.md`): leva a régua descritiva ampliada — além da universal — para o painel, a pedido do autor. Mesma estrutura de banco (novo crosswalk à parte, `camadas_tz.json`, mesmo padrão de `casos_por_fonte.json`/`casos_por_noticia.json`).

**Régua descritiva ampliada no mapa e no card de município:**

- Novo crosswalk `camadas_tz.json` — 30 municípios com camada 2a (temporal-dias, 24), 3 (espacial-periférica, 4) ou 4 (grupo social, 4) = 32 entradas (Belo Horizonte tem as três). Fontes: `camada2a_temporal_dias_analise.csv` e `tz_bairros_perifericos.csv` (cofre, `03 - Dados/_data/`) + a nota "Tipologias de Tarifa Zero (4 camadas)" para a camada 4 (sem CSV dedicado ainda).
- **Exclui de propósito a camada 2b/temporal-eventos** (324 gratuidades eleitorais/pontuais, decisão do STF) — mesma decisão já tomada para o card "TZ parciais" na Fase 8: é adesão por obrigação judicial, não escolha municipal, misturar inflaria o número e mudaria o sentido do que está sendo medido.
- **Mapa:** município com camada parcial e sem TZ universal ganha contorno tracejado amarelo (`.tzparcial`) — visualmente distinto do contorno sólido de TZ universal (`.tzpath`), sem introduzir cor nova (mesmo amarelo da identidade). Legenda atualizada quando o mapa está colorido por status de TZ.
- **Card de município:** nova seção "Camada da régua descritiva", ao lado de Fontes/Notícias, com o detalhe de cada camada e, quando existente, um alerta de conflito com a base principal.
- **Card "TZ parciais":** deixa de ser um número estático nacional (32, sem recorte por município) e passa a contar dinamicamente pelo crosswalk, reagindo ao filtro atual (UF/faixa/REGIC/arranjo/modelo) como os demais cards.
- **Achado de consistência (não resolvido aqui):** 2 dos 30 municípios têm conflito com a base principal — **São Caetano do Sul** ainda consta "Ativa" (universal) na base, mas já é grupo social desde a revogação de 15/07/2026; **Florianópolis** consta "Encerrada" (universal) na base, mas os dados novos sugerem que era, na verdade, temporal-dias (camada 2a) — sinalizado como "REVER" no crosswalk, não alterado no `tz_status` principal sem confirmação do autor. Por isso o card "TZ parciais" (28) exclui esses 2 para não contar duas vezes — ver comentário no código.

## v0.4.01 (2026-07-28)

Sub-patch de v0.4 (decisão do autor — ver `VERSIONING.md` § Exceção sub-patch v0.x.NN): terceira passagem, incorpora os achados da consolidação de referências (bibliografia + notícias mapeadas) feita no cofre a pedido do autor. Mesma estrutura de banco (nenhuma coluna nova na base municipal — dados novos entram como crosswalks à parte, no mesmo padrão do `casos_por_fonte.json` da Fase 8).

**Referências bibliográficas:**

- Bloco ABNT ganha uma segunda lista, **"Referências adicionais"**, com as 8 referências acadêmicas levantadas na consolidação de 3 documentos do autor (artigo ANPET/versão cega, PGT092, Observatório de Tarifa Zero) que **não têm citekey no Zotero** (`biblioteca.bib`) — confirmado por leitura completa do `.bib` via `bibtexparser` + similaridade de título (não só sobrenome+ano, método refinado a pedido do autor após a primeira tentativa ter gerado falsos positivos). Mantida separada da lista original (que é só sobre os 5 estudos citados no crosswalk de Fontes) porque essas 8 ainda não estão vinculadas a um município específico.
- Uma delas (Kębłowski 2024, "Fare-free public transport: An international perspective") está sinalizada com ⚠ como possível duplicata/versão anterior de `keblowski2025a` (já no Zotero, título 2025 diferente) — decisão deixada para o autor, não resolvida aqui.
- Uma referência (Campos; Santini, 2024) está com dados de publicação incompletos na fonte de origem — sinalizado no próprio texto da citação, "a conferir antes de citar".

**Notícias por município (nova seção, separada de Fontes):**

- Novo crosswalk `casos_por_noticia.json`, gerado a partir de `05 - Referências/Reportagens por município` (cofre) — 42 municípios, 70 matérias de imprensa.
- Card de detalhe do município ganha seção **"Notícias"**, ao lado (não junto) da seção "Fontes" — mantém a separação decidida na Fase 8 entre estudo acadêmico (citação pública em "Fontes") e reportagem de jornal/revista/site (agora com seção própria, sem se misturar com a citação acadêmica).
- Não altera a tabela principal nem a coluna "Fontes" (que segue restrita a estudo acadêmico) — notícias aparecem só no card expandido do município selecionado.

## v0.4 (2026-07-27)

Rodada de ajustes estéticos + Fase 8 (repositório de estudos), em duas passagens no mesmo dia — a segunda corrige e substitui partes da primeira a partir do primeiro uso real do painel (feedback direto do autor). Mesma estrutura de banco (nenhuma coluna nova na base municipal em si — os dados novos usam agregados pré-computados à parte; ver nota abaixo).

**Identidade visual:**

- Paleta corrigida dos hex antigos (`#f43f6f`/`#ffd400`/`#2b50d9`) para os oficiais (`#FF2D6B`/`#F5E400`/`#1A54C7`), com `--verde` (`#6FBE44`) adicionado — alinhado com `pesquisa.html`/`index.html` (Fase 9.1 do ROADMAP).
- Status "Ativa" passou por verde e voltou para **amarelo** (mapa, tags, tabela, linha do tempo) — decisão final do autor após ver as duas opções; rosa marca só "Encerrada".
- Tema claro removido — painel passa a ser **só escuro**; toggle, CSS e lógica de tema retirados.
- Logo do PGT trocado da sigla (raster) para o logotipo extenso oficial (SVG); todos os logos do rodapé ampliados (34px → 46px).

**Estrutura e grandes números:**

- Seções colapsáveis (comparação TZ×Não-TZ, % por eixo, notas metodológicas — glossário já era) — permite ver mapa + tabela juntos (Fase 4.1).
- CTA de contribuição ("não achou seu município? envie um caso ou estudo") como rodapé da tabela de casos, apontando para `pesquisa.html` (Fase 6.1).
- Card "TZ ativas" agora deixa explícito que é sobre a camada **universal**; novo card "TZ parciais" (32 = 24 temporal-dias + 4 espacial-periférico + 4 grupo social — exclui de propósito as 324 gratuidades eleitorais/eventuais, fenômeno distinto). Card "TZ encerradas" e o filtro "Sede × satélite" removidos do topo.

**Card "Município selecionado":**

- "PDMU (2025)" renomeado para **"PlanMob (2025)"**; "Tarifa reconciliada" renomeado para **"Tarifa"**, mostrando "Gratuito (TZ universal)" nos municípios com TZ ativa em vez de "sem dado".

**Fase 8 — repositório de estudos:**

- Crosswalk estudo/fonte → município construído a partir de 11 arquivos de `casos por fonte` (Santini 2019, Pereira 2023, Angelo 2023, Vermander 2021, brinco 2017, NTU 2023/2025, reportagens por município, TZ fim de semana, TZ bairros periféricos, municípios com FFPT) — 88 municípios, 181 entradas no crosswalk bruto (`casos_por_fonte.json`). Ainda faltam incorporar outros arquivos da pasta (ver Pendências.md).
- **Citação pública restrita a artigos acadêmicos** (decisão do autor, 27/07/2026): a coluna "Fontes" da tabela e o card de detalhe do município mostram só entradas com tipo "Estudo acadêmico" (38 municípios, 69 entradas) — relatórios institucionais (NTU), reportagens de jornal/revista e levantamentos de coleta própria (ex.: planilha "Municípios com FFPT") ficam de fora da citação, mesmo constando no crosswalk bruto.
- Nova coluna "Fontes" na tabela de municípios, com expansão inline por linha, e seção "Fontes" no card de município selecionado. Das 3 formas de exibição testadas, o painel separado "Repositório de fontes por município" foi descartado (ficaram só coluna+expansão e card).
- Novo bloco **"Referências bibliográficas"** em formato ABNT NBR 6023 para os 5 estudos acadêmicos citados no crosswalk de fontes (Santini 2019, Pereira 2023, Angelo 2023, Vermander 2021, Brinco 2017) — citekeys conferidos em `biblioteca.bib`.

**Gráfico de partição modal:**

- Testados dois gráficos novos com dados do Censo 2022/DENATRAN (evolução da motorização em linha; meio de transporte em 5 barras separadas por modo); ambos foram descartados e substituídos por um único gráfico **"Partição modal — TZ × Não-TZ"**, uma barra 100% empilhada por grupo (TZ/Não-TZ), destacando Ônibus (azul) e Ativo = a pé + bicicleta (rosa) — únicas cores da identidade usadas, sem combinar com amarelo/verde; Automóvel/Motocicleta/Outros em neutros.
- ⚠️ Os agregados usados no gráfico foram **pré-computados à parte** (script avulso, não o pipeline `montar_html.sh`/`build_stats.py` — que não roda neste ambiente) — mover para o build regular quando rodar localmente, para não depender de números "congelados" na próxima atualização de dados.

**Dois gráficos novos** (dados novos de `base_municipal_v3.csv`, adicionados fora deste ambiente — ver Pendências.md 26/07):

- **Evolução da motorização (DENATRAN, 2013-2022), TZ × Não-TZ** — grupo TZ restrito, em cada ano, aos municípios já adotantes até aquele ano (mesma correção cronológica da Análise II do Cap. 2).
- **Meio de transporte (Censo 2022), TZ × Não-TZ** — % de deslocamentos por modo, mesmo critério de corte (TZ até 2022, n=73).
- ⚠️ Os dois gráficos usam **agregados pré-computados à parte** (script avulso, não o pipeline `montar_html.sh`/`build_stats.py` — que não roda neste ambiente) — mover para o build regular quando rodar localmente, para não depender de números "congelados" na próxima atualização de dados.

## v0.3 (publicada 2026-07-24)

Release de melhorias guiada pelo feedback de 5 leitores (ver `FEEDBACK.md`) e pelo pedido da orientação (mais gráficos e grandes números). Mesmos dados da v0.2 — nenhuma mudança de base.

**Mapa:**

- Bordas estaduais sempre visíveis (camada de UFs dissolvida dos municípios, +17 KB) — o item mais pedido do feedback.
- Bordas municipais mais visíveis; contorno claro destacando os municípios TZ (decisão: contorno em vez do "glow" pedido — ver ROADMAP, registro de decisões).
- Auto-encaixe: selecionar UF no filtro enquadra o estado; duplo clique num município aproxima; botão "↺ Brasil" reseta. Strokes com `vector-effect: non-scaling-stroke` (espessura constante em qualquer zoom).
- Tooltip completo nos municípios TZ (situação, início/fim, REGIC, arranjo, população, PIB pc, motorização, operador); tooltip suprimido fora do recorte quando há filtro ativo.

**Grandes números e gráficos (pedido da orientadora):**

- Cards do topo agora são dinâmicos — recalculam conforme o recorte (UF/faixa/REGIC/arranjo/modelo), com aviso de "amostra pequena" quando há <5 municípios TZ no recorte. Novo indicador: **pessoas vivendo com TZ ativa** (soma da população dos municípios ativos; nacional: ~7,6 milhões).
- Novo gráfico: **linha do tempo das adoções** (por ano de início, com revogações abaixo do eixo), reagindo aos filtros — evidencia a aceleração recente (37 adoções só em 2023).

**Leitura e estrutura:**

- Cabeçalho reescrito: título oficial da tese ("Tarifa Zero e Grupos Econômicos no Brasil"), resumo da pesquisa (pergunta, hipótese e método — redigido a partir do projeto de qualificação, a revisar pelo autor) e link para este repositório. Sigla "(TZ)" definida na primeira menção do resumo.
- Títulos de seção maiores; cards e controles no mesmo grid (alinhados).
- Bloco "% por eixo": subtítulo explicando que a % é dentro de cada categoria; rótulo agora fica acima da própria barra (sem ambiguidade barra↔legenda).
- Glossário de siglas (IBEU, IDH, PDMU, REGIC, NTU, MUNIC, FINBRA, arranjo metropolitano, motorização) em bloco colapsável.
- **Toggle tema claro/escuro** (preferência salva no navegador); paleta neutra do mapa acompanha o tema.

**Identidade visual da pesquisa** (aplicada 24/07/2026, a partir da base de identidade do autor — rosa `#f43f6f` · amarelo `#ffd400` · azul `#2b50d9` sobre preto):

- Cores semânticas: **amarelo = TZ ativa**, **rosa = encerrada/revogação**, azul = interface (links, barras, filtros) — no mapa, na linha do tempo, nas tags e na legenda.
- Título em caixa alta com "Tarifa Zero" destacado (amarelo + sublinhado rosa); títulos de seção em caixa alta com filete amarelo; selo "painel · v0.3" no estilo do adesivo da identidade.
- Rodapé no padrão da capa: autor/programa à esquerda, orientadora à direita.
- No tema claro, os textos em amarelo usam tom escurecido para manter contraste (fills do mapa não mudam).
- Título do trabalho no cabeçalho: "Transporte Público em Crise — A influência dos grupos econômicos nas experiências de Tarifa Zero" (com "Crise" destacado, como na capa da identidade).
- Ajustes do autor: "Mapa coroplético" → "Mapa"; municípios com TZ encerrada têm contorno rosa (ativas seguem com contorno amarelo); caixa "Município selecionado" separada do bloco de comparação TZ×Não-TZ (painéis independentes).

## v0.2 (2026-07-23)

Reconstruído sobre `base_municipal_v3.csv` (234 variáveis), no lugar da v0.1 (`base_municipal_integrada_v2.csv`, 131 variáveis). Mesma geometria municipal (topojson simplificado) e mesmo cruzamento com a base-mestre de Tarifa Zero — só a base de atributos mudou.

Eixos novos:

- **Hierarquia urbana (REGIC 2018)** — nível 1 (Metrópole) a 5 (Centro Local), como proxy de centralidade/interesse comercial.
- **Sede × satélite de arranjo metropolitano** — deriva de `arranjo_pop_2018` + nome do município: "sede" quando o nome do município aparece no nome do arranjo, "satélite" caso contrário.
- **Modelo de prestação do serviço (MUNIC 2020)** — concessão / permissão / autorização / prestação direta / não regulamentado / misto. Cobertura parcial: só 1.727/5.570 municípios (31%) responderam esse módulo da pesquisa do IBGE.
- **Tarifa de ônibus reconciliada** (PEMOB > SIMU > ANTP/SIMOB) — cobertura muito baixa (111/5.570, 2%).
- **% do custo subsidiado (NTU)** — cobertura muito baixa (80/5.570, 1,4%).

### Achado descritivo (a interpretar com cautela)

Olhando só a hierarquia REGIC, municípios de nível 1 (Metrópole) têm a *maior* proporção de TZ (14,5%) — à primeira vista, o oposto do que a hipótese de bloqueio pelos grupos econômicos sugeriria. Decompondo por sede × satélite, porém: dos 31 municípios de nível 1 com TZ, **nenhum é a cidade-polo do arranjo metropolitano** — todos são satélites (ex.: Caucaia/Fortaleza, Canoas/Porto Alegre, seis municípios do entorno do Rio de Janeiro, São Caetano do Sul/São Paulo, Brumadinho/Belo Horizonte). Nenhuma das ~15-20 maiores metrópoles do país tem TZ na cidade-polo. Em arranjos menores, esse padrão não se sustenta (ex.: Teresina/PI, Itapetininga/SP e São João del Rei/MG são cidades-polo com TZ).

Isso é uma correlação descritiva, não um teste da hipótese central da tese — falta a variável de presença/atuação de grupo econômico por município (rede ARS/CNPJ) para isso.

## v0.1 (2026-07-20, preservada como histórico — não publicada neste repositório)

Primeira versão, construída sobre `base_municipal_integrada_v2.csv` (131 variáveis: FINBRA, PIB, frota, Censo 2022, Passe Livre eleitoral). Mapa coroplético + filtros por UF/faixa populacional/situação TZ + comparação TZ×não-TZ + lista dos municípios TZ. Guardada no cofre de pesquisa (não neste repositório).

## Pendências de qualidade de dados (v0.1 e v0.2, não corrigidas)

- **Duplicata no arquivo-mestre de TZ:** `Municípios TZ - consolidado.xlsx` tem 155 linhas (145 Ativa + 10 Encerrada), mas Palmas-TO aparece duas vezes como "Encerrada" (períodos 2023-02-02 e 2025-01-01/2025-02-03) — são 154 municípios únicos (145 ativas + 9 encerradas distintas). Não reconciliado ainda: pode ser duplicata de digitação ou dois episódios reais de implantação/revogação.
- **Desatualização pontual:** São Caetano do Sul consta como "Ativa" (a base-fonte é de abr/2026); a universalidade foi revogada em 15/07/2026. A planilha-mestre ainda não reflete essa mudança.

## Pipeline / reprodutibilidade

Scripts em `scripts/` (`build_data.py`, `build_stats.py`) documentam como os dados embutidos no `painel.html` foram gerados a partir das fontes brutas. As fontes brutas (CSVs/XLSX) são parte do cofre de pesquisa privado do autor e **não estão incluídas neste repositório público** — os scripts servem como documentação do método, não para execução direta por terceiros. Ver `ROADMAP.md` (Fases 1-5) para o status de cada pendência de visualização; `FEEDBACK.md` guarda só os relatos brutos que originaram esses itens.
