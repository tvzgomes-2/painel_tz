#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""espacializar_grupos_clusters.py — pipeline de espacialização por município
dos grupos econômicos (rede v4) e dos clusters (rede estendida 3 níveis),
a pedido do autor (04/08/2026): "Vamos ajustar uma tabela que tenha todas
empresas, sócios, qual grupo (numero) e segundo qual cluster (grupo do
segundo grafico) - criar indicadores dessa rede na planilha de empresas.
Queria espacializar duas coisas: grupos e clusters" + "para espacializar
usar cor por município (não usar centroide)".

Passo a passo (reproduzível):

1. PONTE RFB→IBGE. O campo `municipio_codigo_rfb` dos dumps ESTABELECIMENTOS
   da Receita NÃO é código IBGE — é código SIAFI. A ponte correta é
   siafi_id → codigo_ibge via `Receita Federal - dados brutos/municipios.csv`,
   já validada e usada por `georreferenciar_e_cruzar_munic.py` (script
   pré-existente do cofre) — reaproveitada aqui, incluindo a função `c7(x)`
   de zero-padding a 7 dígitos.
   Monta `/tmp/municipio_por_cnpj.json` (cnpj_basico de 8 dígitos →
   lista de códigos IBGE de 7 dígitos onde a empresa tem estabelecimento
   ativo), a partir de `estabelecimentos_ativos_6cnaes.csv`. Cobertura:
   269.201/279.658 estabelecimentos (99.99%).

2. TABELA MESTRE. Junta, por cnpj_basico, as 7.680 empresas do universo
   núcleo+ativa+equity (pré-exclusão de consórcio) com:
   - capital_social (capital_social_por_cnpj.csv)
   - id_grupo / nome_grupo / origem_nome_grupo (identificacao_componentes_
     medios_grandes_v4.csv — Teste 14, atribuição por sócio-âncora)
   - cluster_id / cluster_tamanho_nos / cluster_componentes_originais
     (a partir de componentes_expandidos.json — Teste 17, rede 3 níveis).
     Regra: cluster_id = "GE-XXX" (igual ao id_grupo) quando a rede
     estendida NÃO fundiu esse componente com nenhum outro; cluster_id =
     "CL-NN" quando 2+ componentes originais da rede v4 se fundiram ao
     abrir sócios de nível 2/2b/3 (mesmo que só 1 dos componentes fundidos
     seja documentado/nomeado).
   - municipios_atuacao / n_municipios (via municipio_por_cnpj.json).
   Exportada como CSV (`tabela_mestre_empresas_grupos_clusters.csv`) e como
   planilha formatada (skill xlsx) com 3 abas: Empresas, Resumo por grupo,
   Resumo por cluster — salva em
   `03 - Dados/Tabela mestre - Empresas, Grupos e Clusters (ago-2026).xlsx`.

3. AGREGAÇÃO POR MUNICÍPIO. A partir da tabela mestre, monta
   `grupos_por_municipio.json` e `clusters_por_municipio.json`
   (código IBGE → lista de id_grupo / cluster_id presentes nesse
   município). 719 municípios têm ao menos 1 grupo médio/grande do
   recorte.

4. MAPA COROPLÉTICO (não centroide — cor preenche o polígono do
   município inteiro, por instrução explícita do autor). Usa
   `BR_Municipios_2022.shp` (IBGE 2022, 5.572 municípios). A geometria
   original em SVG gera um arquivo de ~420MB (inviável) — corrigido
   simplificando com `gdf.geometry.simplify(0.01, preserve_topology=True)`
   e salvando direto em PNG via matplotlib (não SVG; exceção deliberada
   à preferência geral por SVG do cofre, justificada pela natureza do
   dado — mapa nacional de alta resolução, não peça gráfica de
   divulgação).

   4a. Mapa de GRUPOS: colore cada município pela cor do "sócio-âncora"
       presente (13 grupos documentados com paleta categórica de 13 cores
       bem distintas), cinza escuro para grupo médio/grande não
       documentado, cinza claro para "sem grupo no recorte", preto puro
       para "2+ grupos distintos no mesmo município".
   4b. Mapa de CLUSTERS: destaca só os clusters de FUSÃO — aqueles em
       que 2+ grupos documentados (por sócio-âncora) caem no mesmo
       componente da rede estendida (7 clusters: CL-01 a CL-08, ver
       fusoes_clusters.json). Cinza escuro para "cluster sem fusão" (1
       único grupo/sócio-hub, é o caso degenerado cluster_id==id_grupo ou
       cluster que só juntou nós não documentados), cinza claro para
       "sem grupo", preto puro para "2+ clusters distintos no mesmo
       município".

⚠️ RESSALVA (Becker, mandatória): a cor de um município no mapa indica
presença de sede/estabelecimento de uma empresa vinculada ao grupo/cluster
– não é medida de porte da operação nem de participação de mercado local
(p.ex. um município pode ter 1 CNPJ-satélite de capital social baixo e
aparecer colorido igual a outro onde o grupo concentra sua frota principal).
Também vale a ressalva já registrada no Teste 17: cluster (fusão via sócio)
não é sinônimo de grupo econômico unificado — é vínculo no QSA da Receita,
a confirmar com evidência documental antes de tratar como achado fechado.

SAÍDAS:
  `_attachments/Mapa - Espacializacao dos grupos economicos por municipio
  (ago-2026).png`
  `_attachments/Mapa - Espacializacao dos clusters societarios por
  municipio (ago-2026).png`
  `03 - Dados/Tabela mestre - Empresas, Grupos e Clusters (ago-2026).xlsx`
"""
print(__doc__)
