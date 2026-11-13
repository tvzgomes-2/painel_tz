#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""renumerar_por_capital_social.py — renumeração dos IDs de grupo (GE-XXX) e
cluster (CL-XX), a pedido do autor (04/08/2026): "vamos agora reorganizar os
grupos - renumerando eles do maior capital para o menor" + "idem para os
clusters" (antes, ambos eram numerados por tamanho/nº de empresas — Teste 12
e Teste 18).

Passo a passo:
  1. GRUPOS: `capital_social_por_grupo.csv` (165 linhas, cobertura completa,
     Teste 15) ordenado por `capital_social_total_reais` decrescente
     (desempate pelo id antigo, para estabilidade). Novo `id_grupo` =
     `GE-001`..`GE-165` nessa ordem.
  2. CLUSTERS: capital de cada `CL-XX` = soma do capital social de todas as
     empresas com aquele `cluster_id` na tabela mestre (Teste 18) — cobertura
     completa para as 819 empresas com grupo/cluster atribuído. Os 55 `CL-XX`
     existentes reordenados por esse total, também decrescente. Clusters cujo
     `cluster_id` era um `GE-XXX` (caso degenerado, cluster == grupo) herdam
     a nova numeração do grupo automaticamente — não precisam de reordenação
     própria.
  3. Mapeamento antigo→novo salvo (`old_to_new_grupo.json`,
     `old_to_new_cluster.json`) e aplicado a:
     - `identificacao_componentes_medios_grandes_v4.csv` (+ coluna
       `id_grupo_ANTIGO`, preservada)
     - `capital_social_por_grupo.csv` (+ coluna `id_grupo_ANTIGO`)
     - `Tabela mestre - Empresas, Grupos e Clusters (ago-2026).xlsx` (+
       colunas `id_grupo_ANTIGO` e `cluster_id_ANTIGO` na aba Empresas)
     - `grupos_por_municipio.json` / `clusters_por_municipio.json`
     - os 2 mapas coropléticos (Teste 18), regerados com a nova numeração.

RESULTADO: 162/165 grupos mudam de número. Top 4 do novo ranking: Barata (R$
722,4 mi) · Belarmino (R$ 289,2 mi) · Ruas (R$ 280,7 mi) · Comporte (R$ 228,7
mi, único que não mudou de posição no top 5). Nos clusters, a ordem dos 2
maiores se INVERTE em relação ao ranking de grupos isolados: Barata+JAL
(R$ 772,4 mi somados) passa a ser o cluster de maior capital, à frente do
cluster Comporte+Lessa Carvalho+Rodap+holdings (R$ 496,6 mi) — a fusão de
maior capital não é a de maior nº de empresas.

⚠️ IMPORTANTE (King, reprodutibilidade): esta é uma reordenação de ÍNDICE, não
uma mudança de metodologia/composição dos grupos ou clusters — os
componentes, nomes e composição de cada grupo/cluster são exatamente os
mesmos de antes; só o número mudou. Notas anteriores a este teste (Testes 12,
14, 17, 18) que citam IDs específicos em prosa NÃO foram reescritas — elas
descrevem corretamente a numeração vigente quando cada teste rodou. Para
traduzir um ID antigo citado numa nota anterior, usar a coluna
`id_grupo_ANTIGO`/`cluster_id_ANTIGO` nos arquivos regravados, não recalcular
de memória.

Detalhe completo: [[Log de testes metodológicos - Grupos Econômicos (ago-2026)#Teste 19 — Renumeração de grupos e clusters por capital social]].
"""
print(__doc__)
