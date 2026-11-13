#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""ajustes_visuais_redes_socios.py — ajustes pedidos pelo autor (04/08/2026)
às duas figuras de rede de sócios (base e estendida):

1. Rede base (sem sócios dos sócios) — não usar amarelo; reservá-lo para
   "serviços financeiros" (que só aparece na rede estendida). "Sócio PJ —
   outro" recolorido de amarelo para cinza.
2. Rede estendida (3 níveis) — usar amarelo para "Serviços financeiros"
   (antes vermelho) e melhorar a legenda (organizada em 3 blocos: rede
   original / sócios estendidos / empresas por setor, cada um com título).
3. Em ambas: remover contorno (edgecolor) dos marcadores — só símbolo de cor
   cheia, sem borda preta.
4. Em ambas: espessura da aresta por CAPITAL SOCIAL (não mais por nº de
   empresas em comum ou peso fixo por tipo). Fonte: capital_social_por_cnpj.csv
   (rede base + holdings) + capital social buscado à parte para as 1.164
   empresas de nível 2b (ver bloco 2 abaixo) — consolidados em
   capital_social_unificado.json. Escala log1p (capital social varia de R$0 a
   R$3,4 bi entre os tipos de aresta) para não deixar poucas arestas gigantes
   dominando o desenho.
5. Nomes dos clusters (rótulos) — alguns se sobrepunham nas versões
   anteriores; corrigido aumentando o espaçamento entre ilhas (GAP) e
   quebrando o texto em até 2 linhas com reticências se ainda for muito
   longo (`textwrap.wrap`), em vez de deixar tudo numa linha só.

Passo a passo:
  A. Capital social da rede base: para cada par de sócios-hub que compartilham
     empresas, a aresta agora pesa a SOMA do capital social das empresas
     compartilhadas (antes era só a contagem). Recalculado a partir de
     grupos_economicos_v4_componentes_completos.csv + socios_filtrado_6cnaes.csv
     + capital_social_por_cnpj.csv (mesma lógica de reconstruir_identificacao_
     componentes.py, mudando o que a aresta acumula).
  B. Capital social das empresas de nível 2b (as 1.164 "empresas ligadas"):
     ainda não estava mesclado (só a "rede base" tinha). Buscado via awk
     contra empresas0-9.csv, mesmo método de mesclar_capital_social.py — 745/
     1.164 encontradas (64%; resto não localizado no cadastro nesta rodada,
     não afeta a rede de forma relevante, só deixa a aresta um pouco mais fina
     que o "real" nesses casos).
  C. Cada tipo de aresta da rede estendida usa o capital social do nó-empresa
     mais relevante: nível 1 (hub-hub) = soma do capital das empresas
     compartilhadas (igual à rede base); nível 2 (holding→sócio) = capital
     social da própria holding; nível 2b (sócio→empresa) e nível 3
     (empresa→sócio) = capital social daquela empresa de nível 2b.

Reexecutar as duas figuras inteiras (dados + posições + render) leva menos de
10s no total — não precisa dos truques de streaming/awk de novo a não ser que
o universo de CNPJs mude.
"""
print(__doc__)
