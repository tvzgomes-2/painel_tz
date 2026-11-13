#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""empresas_ligadas_holdings.py — camada de diversificação/financeirização
(04/08/2026), a pedido do autor: "gostaria que incluíssemos nessa rede esses
sócios das holdings e empresas vinculadas a transporte. quais indicadores de
proximidade... Conseguimos ampliar... qualquer setor (mostra diversificação)".

Pergunta: os sócios das 98 holdings-hub (rede médio+grande, v4) têm OUTRAS
empresas, de qualquer setor — não só transporte? Se sim, quais setores?

Método (3 passos, cada um streaming — nunca materializar os arquivos brutos
inteiros em memória nem em disco; ver ressalva de disco em
mesclar_capital_social.py, que vale igual aqui):

1) Sócios das 98 holdings (2ª camada) — já levantado no Passo 7
   (`socios_segunda_camada.csv`), filtrado às 98 holdings-hub da rede v4
   (reconstruir_identificacao_componentes.py). 265 sócios distintos (PF+PJ).

2) Para cada um dos 265 sócios, escanear SOCIO0..9.csv (bruto, ~2 GB total,
   SEM filtro de CNAE) casando por identidade (nome+CPF/CNPJ mascarado) —
   devolve TODAS as empresas (qualquer CNAE) onde esse sócio aparece.
   awk (~20s/arquivo maior, ~5s os demais):
     awk -F';' '
       NR==FNR{a[$0]=1; next}
       { nome=$3; gsub(/"/,"",nome); doc=$4; gsub(/"/,"",doc);
         if ((nome"|"doc) in a) { cnpj=$1; gsub(/"/,"",cnpj);
           qual=$5; gsub(/"/,"",qual); print cnpj";"nome";"doc";"qual } }
     ' alvo_socios_holdings.txt SOCIO<N>.csv >> empresas_ligadas_raw.csv

3) Excluir empresas já no universo de transporte (6 CNAEs) e as próprias
   holdings (auto-vínculo) — sobra o conjunto de "empresas novas". Buscar
   CNAE fiscal principal (ESTABELECIMENTOS*.csv, campo matriz) e razão social
   (empresas*.csv) para essas novas, classificar por seção CNAE (2 primeiros
   dígitos da CNAE 2.0 classe).

⚠️ ESTABELECIMENTOS0.csv tem 4 GB (as outras 9 partes têm ~1 GB cada) — não
processar de uma vez. Usar `dd if=ESTABELECIMENTOS0.csv bs=1M count=1000
skip=<N*1000> | awk ...` em ~4 pedaços de 1000 MB, cada um piped diretamente
pro awk (nunca salvar o pedaço em disco) — assim não há risco de encher o
/tmp (já aconteceu uma vez nesta pesquisa, ao tentar fatiar o arquivo em
disco com `split`).

RESULTADO (04/08/2026): 1.164 empresas novas (fora do recorte de transporte)
ligadas aos 265 sócios das 98 holdings. Distribuição por setor (top 5):
Serviços financeiros 255 · Transporte terrestre 227 (fora do recorte de 6
CNAEs, mas ainda transporte) · Atividades imobiliárias 144 · Comércio 106 ·
Construção 96. Amostra de "Serviços financeiros" inclui banco (Banco
Guanabara S/A), securitizadoras de crédito, corretoras de seguro, gestoras de
recursos e dezenas de holdings "Participações"/"Empreendimentos" — indício
relevante para o argumento de financeirização dos grupos econômicos (Cap 5/6),
a aprofundar com pesquisa qualitativa antes de virar afirmação no texto.

⚠️ RESSALVA (Becker — dado vs. inferência): esta camada mostra que o SÓCIO
tem vínculo formal (RFB) com a empresa nova — não estabelece controle
(percentual de participação não consta no QSA público da Receita), nem que a
empresa nova seja necessariamente controlada pelo MESMO grupo econômico do
transporte (o sócio pode ter papéis distintos e não relacionados em cada
empresa). Não afirmar "o grupo X controla a financeira Y" sem evidência
adicional (ata societária, percentual de capital, notícia).

SAÍDA: empresas_ligadas_holdings_qualquer_setor.csv (cnpj_basico, razao_social,
situacao, cnae, uf, setor).
"""
print(__doc__)
