#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RSL1 — CAPES legado (1987-2012): filtra os XLSX JA BAIXADOS localmente,
sem nenhuma chamada de rede/CKAN.

Por que este script existe (12/09/2026): o
`rsl1_capes_baixar_e_filtrar_v2_janela_estendida.py` precisa descobrir os
recursos via CKAN mesmo em --so-filtrar, para saber o NOME do arquivo
esperado (`recurso["arquivo"]`). O pacote CKAN do legado 1987-2012 nao e o
mesmo do moderno (2021-2024) e o nome de arquivo que o CKAN devolve nao
bate com "dados_<ano>.xlsx" (o nome ja usado em disco, herdado do
diagnostico de cabecalho). Em vez de reconciliar pacote/nome via rede so
para filtrar arquivos que ja estao no disco, este script ignora a camada
de descoberta/download inteira e chama a MESMA logica de filtro (importada
do script v2, para nao duplicar e arriscar as duas copias divergirem)
direto sobre `dest/dados_<ano>.xlsx`.

Uso:
    python rsl1_capes_filtrar_legado_offline.py ^
        --dest "C:\\Users\\HOME\\OneDrive\\doutorado\\03 - Dados\\_data\\CAPES" ^
        --out  "C:\\Users\\HOME\\OneDrive\\doutorado\\04 - Análises\\RSL (revisão sistemática)" ^
        --anos 1987 1988 1989 1990 1991 1992 1993 1994 1995 1996 1997 1998 1999 2000 2001 2002 2003 2004 2005 2006 2007 2008 2009 2010 2011 2012

Requer que `rsl1_capes_baixar_e_filtrar_v2_janela_estendida.py` (ja
corrigido para o layout legado) esteja na MESMA PASTA que este script.
"""

import argparse
import importlib.util
import os
import sys
from datetime import date

_AQUI = os.path.dirname(os.path.abspath(__file__))
_CAMINHO_V2 = os.path.join(_AQUI, "rsl1_capes_baixar_e_filtrar_v2_janela_estendida.py")


def _importar_v2():
    if not os.path.exists(_CAMINHO_V2):
        sys.exit(f"ERRO: nao encontrei {_CAMINHO_V2}. Este script precisa estar na mesma "
                  f"pasta que rsl1_capes_baixar_e_filtrar_v2_janela_estendida.py (ja corrigido "
                  f"para o layout legado).")
    spec = importlib.util.spec_from_file_location("rsl1_v2", _CAMINHO_V2)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dest", required=True, help="pasta onde os dados_<ano>.xlsx ja estao")
    ap.add_argument("--out", required=True, help="pasta para os CSVs de resultado")
    ap.add_argument("--anos", nargs="+", type=int, required=True, help="anos a filtrar, ex.: --anos 1987 1988")
    args = ap.parse_args()

    v2 = _importar_v2()
    os.makedirs(args.out, exist_ok=True)

    padroes = v2.compilar_padroes()
    contagem_por_string = {}
    candidatos = []
    anos_ok = []
    anos_falhos = []
    anos_sem_arquivo = []

    for ano in sorted(args.anos):
        caminho = os.path.join(args.dest, f"dados_{ano}.xlsx")
        if not os.path.exists(caminho):
            print(f"[{ano}] AVISO: {caminho} nao existe - pulando.")
            anos_sem_arquivo.append(ano)
            continue
        try:
            v2.filtrar_arquivo(caminho, ano, padroes, contagem_por_string, candidatos)
            anos_ok.append(ano)
        except SystemExit:
            raise
        except Exception as e:
            print(f"\n[{ano}] FALHA AO FILTRAR - pulando este ano: {e}\n")
            anos_falhos.append(ano)

    hoje = date.today().isoformat()

    campos_candidatos = ["ano", "blocos_e_strings", "campos_com_match", "trechos"] + v2.CAMPOS_ID
    caminho_candidatos = os.path.join(args.out, f"CAPES_candidatos_legado_{hoje}.csv")
    v2.gravar_csv_validado(caminho_candidatos, candidatos, campos_candidatos)
    print(f"\nGravado: {caminho_candidatos}  ({len(candidatos)} candidatos)")

    linhas_execucao = []
    for ano in anos_ok:
        for bloco, legivel, tipo, dado in v2.PADROES:
            n = contagem_por_string.get((ano, bloco, legivel), 0)
            linhas_execucao.append({
                "data": hoje, "estrato": "RSL1",
                "base": f"Catalogo de Teses CAPES - XLSX {ano} (legado, filtragem offline)",
                "string": legivel, "bloco": bloco,
                "filtro_data": "sem recorte", "n_resultados": n,
            })
    campos_execucao = ["data", "estrato", "base", "string", "bloco", "filtro_data", "n_resultados"]
    caminho_execucao = os.path.join(args.out, f"CAPES_execucao_por_string_legado_{hoje}.csv")
    v2.gravar_csv_validado(caminho_execucao, linhas_execucao, campos_execucao)
    print(f"Gravado: {caminho_execucao}  ({len(linhas_execucao)} linhas)")

    print("\nPROXIMO PASSO: nenhum destes candidatos entra em corpus_rsl.csv sem leitura "
          "e sem passar pelos filtros 1 e 2 do protocolo. Junte este CSV aos da v1 (2021-2024) "
          "e da janela estendida antes de rodar a triagem por titulo e resumo.")

    if anos_sem_arquivo or anos_falhos:
        print(f"\n⚠️  Anos nao processados - sem arquivo: {anos_sem_arquivo or '(nenhum)'}; "
              f"falha ao filtrar: {anos_falhos or '(nenhum)'}. Cobertos: {anos_ok}")
        sys.exit(1)


if __name__ == "__main__":
    main()
