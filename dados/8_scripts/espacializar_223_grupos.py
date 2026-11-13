"""
Teste 22 (04/08/2026) — Completa a espacialização pendente desde o Teste 20:
município dos 58 componentes novos, correção de um bug em cluster_id
encontrado no processo, reconstrução da aba "Resumo por cluster" e
regeração dos 2 mapas coropléticos com os 223 grupos.

Pergunta do autor: "VAMOS PARA ESPACIALIZAÇÃO?"

MÉTODO
------
1. Município das 116 empresas novas: mesma ponte RFB→IBGE do Teste 18
   (`estabelecimentos_ativos_6cnaes.csv` → `municipio_codigo_rfb` →
   `siafi_id` → `codigo_ibge`, via `municipios.csv`). 116/116 resolvidos
   (100%). Atualizado `municipios_atuacao`/`n_municipios` na tabela mestre
   para essas linhas (antes "⚠️ pendente").

2. ⚠️ BUG ENCONTRADO E CORRIGIDO (autocorreção, mesma categoria do bug de
   cluster do Teste 17/18 — reprodutibilidade, King): ao explodir
   `cluster_id` por município para montar o mapa de clusters, apareceram 33
   valores tipo "GE-XXX" contendo 2 `id_grupo` DIFERENTES cada — pareceria,
   à primeira vista, 33 novas fusões. Investigação: não são fusões reais —
   são resíduo da renumeração do Teste 19/20. Para componentes com cluster
   degenerado (`cluster_id == id_grupo`, sem fusão real), a renumeração
   atualizou `id_grupo` para o novo número mas ESQUECEU de atualizar
   `cluster_id` junto — o valor antigo ficou parado e colidiu, por
   coincidência de string, com o `id_grupo` NOVO de outro componente
   qualquer que passou a ter aquele mesmo número.
   CORREÇÃO: para todo `cluster_id` que NÃO começa com "CL-" (ou seja, é
   degenerado por definição — só ganha prefixo CL- quando há fusão real,
   Teste 18), `cluster_id` foi igualado ao `id_grupo` vigente da própria
   linha. 417 células corrigidas. Depois da correção, sobraram exatamente
   os 7 clusters de fusão real esperados: CL-01, CL-02, CL-03, CL-05,
   CL-06, CL-09, CL-12 — bate com a contagem original do Teste 18 ("7
   clusters de fusão contêm 2+ grupos documentados").

3. Aba "Resumo por cluster" reconstruída do zero a partir da tabela mestre
   já corrigida: 207 linhas (223 grupos menos os 23 absorvidos nos 7
   clusters de fusão, mais as 7 linhas de cluster).

4. Mapas regerados (mesmo método do Teste 18): `BR_Municipios_2022.shp`
   (IBGE 2022), geometria simplificada `.simplify(0.01, preserve_topology=
   True)`, cache em pickle (`municipios_br_simpl.pkl`) para reuso entre os
   2 mapas. Mapa 1 (grupos): cor por sócio-âncora (13 grupos documentados,
   mesma paleta categórica do Teste 18, mantida por continuidade visual —
   é regeração do mesmo mapa, não peça gráfica nova), cinza-escuro para
   grupo médio/grande não documentado, preto para 2+ grupos no mesmo
   município, cinza-claro (creme) para município sem grupo no recorte.
   Mapa 2 (clusters): cor por cluster de fusão (7 categorias), cinza-escuro
   para cluster sem fusão (1 único grupo), preto para 2+ clusters de fusão
   no mesmo município.

RESULTADO
---------
887 municípios com algum grupo médio/grande no recorte (era 719 com os 165
grupos do Teste 18) — maior porque os 58 novos componentes trazem
municípios adicionais (operadores de grande porte com footprint nacional,
ex. Itapemirim, "1001", Garcia). CL-05 visivelmente maior no mapa de
clusters (mancha alaranjada mais extensa na região de Curitiba/PR),
refletindo a fusão do Teste 21. Nenhum outro cluster de fusão mudou de
tamanho.

RESSALVA (mesma do Teste 18, mandatória)
-----------------------------------------
Cor num município indica sede/estabelecimento de empresa vinculada ao
grupo/cluster ali — não é medida de porte da operação, de participação de
mercado local, nem prova de controle unificado.

DECISÃO
-------
Tabela mestre com `municipios_atuacao` dos 116 novos preenchido, `cluster_
id` corrigido (417 células), aba "Resumo por cluster" reconstruída (207
linhas), 2 mapas regerados e sobrescritos em `_attachments/` (mesmo nome de
arquivo — versão vigente é sempre a mais recente).

PENDENTE (não feito neste teste)
---------------------------------
O "tamanho do grafo expandido" de CL-05 (207 nós, nível 2/2b/3, do Teste
17/18) não foi recomputado com os 2 novos membros (Stabile, Gulin/Viação
Campos Gerais) — só a contagem de empresas no recorte de transporte (24)
foi atualizada. Recomputar o grafo completo e regerar a figura de rede
estendida fica para uma próxima rodada.

Ver [[Log de testes metodológicos - Grupos Econômicos (ago-2026)#Teste 22]]
para o registro completo e [[Pendências]] para o que ainda falta.
"""
