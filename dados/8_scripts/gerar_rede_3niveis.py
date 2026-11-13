#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""gerar_rede_3niveis.py — rede societária estendida até o 3º nível de sócio
(04/08/2026), a pedido do autor: "adicionar esses sócios dos sócios até o 3
nível no grafo (fazer um novo) destacando também os serviços financeiros como
uma categoria separada".

Camadas (a distância é contada a partir da empresa de transporte original):
  Nível 1 — sócio direto de uma empresa de transporte (6 CNAEs). É o hub já
            usado na rede v4 / identificacao_componentes_medios_grandes_v4.csv.
  Nível 2 — sócio de uma holding que é sócia de nível 1 (socios_segunda_camada.csv,
            filtrado às 98 holdings-hub da rede v4). Ver Teste 13.
  Nível 2b — empresas (qualquer setor) onde um sócio de nível 2 também é sócio
             (empresas_ligadas_holdings_qualquer_setor.csv). Ver Teste 16.
  Nível 3 — sócios dessas empresas de nível 2b (só os que aparecem em 2+
            empresas de nível 2b — "hub" real; sócio de 1 empresa só vira ruído
            visual sem acrescentar rede).

Passo a passo (reproduzível, streaming — nunca materializar os dumps brutos
inteiros; ver ressalva de disco em mesclar_capital_social.py):
  1. `montar_grafo_3niveis` monta os 4 conjuntos de nós/vínculos acima a partir
     dos CSVs/JSONs já produzidos pelos Testes 13/16 (socios_segunda_camada.csv,
     empresas_ligadas_holdings_qualquer_setor.csv, mais um novo escaneamento de
     SOCIO0-9.csv restrito às 1.164 empresas de nível 2b, para achar o nível 3).
  2. Excluir nós de nível 2b cuja razão social contenha
     ASSOCIACAO/SINDICATO/COOPERATIVA/FEDERACAO — são vínculo de participação
     associativa/profissional, não de propriedade (mesmo cuidado já usado para
     excluir consórcios e o caso Oishi/conselheiro profissional).
  3. Recalcular componentes conexos do grafo expandido (nx.connected_components)
     — verificar quais componentes ORIGINAIS (da rede v4, tam>=3) se fundem
     em um só componente ao abrir os níveis 2/2b/3. Reportar cada fusão.
  4. Para não afogar a figura em ruído, manter no nível 2b TODAS as empresas de
     "Serviços financeiros" (é a categoria que o autor pediu para destacar) e,
     das demais, só as que têm 2+ vínculos de sócio ou tocam um hub de nível 3.
  5. Layout em prateleiras (shelf packing, mesmo método das figuras anteriores),
     um "componente expandido" por ilha, com spring_layout (poucas iterações —
     30-60 bastam; testado até 581 nós em ~3s). Desenhar edges com
     matplotlib.collections.LineCollection e nós com scatter agrupado por
     (cor,marker,tamanho) — desenhar nó a nó / aresta a aresta individualmente
     é ~30x mais lento e estourou o limite de tempo do ambiente na 1ª tentativa.

RESULTADO (04/08/2026): 55 "ilhas" cresceram ao abrir os níveis 2/2b/3 (de 165
componentes médio+grande originais). Achado principal: **6 grupos de
componentes ORIGINALMENTE SEPARADOS se fundem num só componente expandido**,
o maior reunindo Barata(123)+JAL(147)+Rodap(1098)+Lessa Carvalho(247)+
Comporte/Constantino(942)+Felício(237)+outros 9 componentes menores em 581+394
= 975 nós. Setor mais frequente entre as 1.164 empresas de nível 2b: Serviços
financeiros (255) — inclui um banco (Banco Guanabara S/A) e 2 securitizadoras
de crédito.

⚠️ RESSALVA (Becker, mandatória): isto é vínculo de sócio no QSA da Receita —
não confirma controle unificado. Antes de afirmar "esses grupos são um só" no
texto, verificar: (a) se o vínculo é equity real ou só administração/procurador
profissional comum (mesmo risco já visto no caso Oishi, Teste 9); (b) se a
qualificação do sócio-ponte é consistente com controle (não é qualificação de
associação/conselho, já filtrada); (c) se há evidência documental independente
(notícia, ata) antes de tratar como achado fechado.

SAÍDAS: `_attachments/Rede societaria estendida - socios ate 3o nivel,
destaque servicos financeiros (ago-2026).svg`.
"""
print(__doc__)
