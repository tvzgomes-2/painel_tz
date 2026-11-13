#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
buscar_querido_diario_candidatos.py

Companheiro de `buscar_querido_diario.py` (nao o modifica, nao o substitui).

Motivo de existir: o modo `--municipios-arquivo` de `buscar_querido_diario.py`
resolve municipio/UF batendo o `cod_ibge` pedido contra o "Controle unico -
176 casos" - ou seja, so sabe rodar sobre municipios QUE JA ESTAO na nossa
base. Para os 37 candidatos "fora do canonico" (17 pistas do Gemini + 20
alta-prioridade do indice ENANPUR "Quem tem onibus?"), isso da join vazio:
rodei `buscar_querido_diario.py --municipios-arquivo alvo_tz_37...csv` em
16/09/2026 e o resultado foi "0 municipios a varrer" seguido de um
KeyError (resumo.csv fica sem a coluna 'algum_achado' quando a lista de
alvos e vazia) - script nao pensado para esse caso de uso, nao bug urgente,
so nao serve pra isso.

Este script reaproveita as MESMAS funcoes de busca (`buscar_termo`,
`chamar_com_retentativas`, os 6 TERMOS padrao, a mesma pausa/retentativa)
importando-as diretamente de `buscar_querido_diario.py`, e roda o mesmo
laco "modo padrao" (um territorio por vez, `territory_ids=cod_ibge`, sem
depender do Controle unico) sobre uma lista explicita de municipio/UF/IBGE
fornecida a parte (nao precisa estar nos 176 casos).

Uso:
    python3 buscar_querido_diario_candidatos.py \
        --arquivo alvo_tz_37_candidatos_20260916.csv \
        --saida saida_querido_diario_candidatos

CSV de entrada precisa das colunas: municipio,uf,cod_ibge

Saida: <saida>/resumo.csv (mesmas colunas do modo padrao do script original)
+ um .json por municipio com achado.

Autor: Thiago Von Zeidler Gomes
Orientadora: Prof.a Silvana Zioni
"""

import argparse
import json
import time
from pathlib import Path

import pandas as pd
import requests

import buscar_querido_diario as bqd  # mesmo diretorio


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--arquivo", required=True,
                     help="CSV com colunas municipio,uf,cod_ibge (candidatos fora do Controle unico)")
    ap.add_argument("--saida", default="saida_querido_diario_candidatos")
    ap.add_argument("--pausa", type=float, default=1.0)
    ap.add_argument("--do-zero", action="store_true",
                     help="Ignora o resumo.csv parcial ja existente e reprocessa "
                          "todos os municipios do --arquivo, mesmo os ja feitos.")
    args = ap.parse_args()

    alvos = pd.read_csv(args.arquivo, dtype={"cod_ibge": str})
    alvos["cod_ibge"] = alvos["cod_ibge"].str.strip()

    saida = Path(args.saida)
    saida.mkdir(exist_ok=True, parents=True)
    resumo_path = saida / "resumo.csv"

    # Retomada: pula municipios que ja tem linha em resumo.csv de uma rodada
    # anterior (o script antigo so gravava resumo.csv no final do loop inteiro
    # -- uma queda no meio perdia o progresso inteiro sem deixar rastro para
    # municipios sem achado. Agora cada municipio e gravado assim que termina.)
    ja_feitos = set()
    if resumo_path.exists() and not args.do_zero:
        resumo_existente = pd.read_csv(resumo_path, dtype={"cod_ibge": str})
        ja_feitos = set(resumo_existente["cod_ibge"].str.strip())
        print(f"Retomando: {len(ja_feitos)} municipios ja processados em "
              f"{resumo_path} (rodada anterior). Use --do-zero para ignorar.")

    total_antes = len(alvos)
    if ja_feitos:
        alvos = alvos[~alvos["cod_ibge"].isin(ja_feitos)].reset_index(drop=True)

    print(f"{len(alvos)} de {total_antes} municipios candidatos faltando varrer "
          f"({len(bqd.TERMOS)} termos cada = {len(alvos) * len(bqd.TERMOS)} "
          f"chamadas a API restantes).")

    escreve_cabecalho = not resumo_path.exists() or args.do_zero
    if args.do_zero and resumo_path.exists():
        escreve_cabecalho = True
    modo_arquivo = "w" if (args.do_zero or not resumo_path.exists()) else "a"
    resumo_f = open(resumo_path, modo_arquivo, encoding="utf-8-sig", newline="")
    import csv as _csv
    campos = ["municipio", "uf", "cod_ibge", "algum_achado", "termo_do_1o_achado",
              "data_diario", "url_diario", "excerto", "erro"]
    resumo_writer = _csv.DictWriter(resumo_f, fieldnames=campos)
    if escreve_cabecalho:
        resumo_writer.writeheader()
        resumo_f.flush()

    for i, row in alvos.iterrows():
        municipio, uf, ibge = row["municipio"], row["uf"], row["cod_ibge"]
        print(f"\n=== [{i+1}/{len(alvos)}] {municipio}/{uf} (IBGE {ibge}) ===")

        achados_municipio = {}
        algum_achado = False
        erro = ""

        for termo in bqd.TERMOS:
            try:
                resp = bqd.buscar_termo(ibge, termo)
            except requests.HTTPError as e:
                print(f"  erro HTTP em '{termo}': {e}")
                erro = str(e)
                time.sleep(args.pausa)
                continue
            except requests.RequestException as e:
                print(f"  erro de rede em '{termo}': {e}")
                erro = str(e)
                time.sleep(args.pausa)
                continue

            gazettes_brutos = resp.get("gazettes", [])
            gazettes = [g for g in gazettes_brutos if bqd.bate_frase_exata(termo, g)]
            total = len(gazettes)
            if total:
                algum_achado = True
                if len(gazettes) != len(gazettes_brutos):
                    print(f"  ACHOU '{termo}': {total} diario(s) com a FRASE confirmada "
                          f"(de {len(gazettes_brutos)} devolvido(s) pela API -- "
                          f"{len(gazettes_brutos) - total} descartado(s) por nao "
                          f"terem a frase contigua no excerto).")
                else:
                    print(f"  ACHOU '{termo}': {total} diario(s) com o termo.")
                achados_municipio[termo] = gazettes
            else:
                print(f"  .  '{termo}': 0.")
            time.sleep(args.pausa)

        if achados_municipio:
            arq = saida / f"{municipio}-{uf}.json".replace("/", "-")
            arq.write_text(
                json.dumps(achados_municipio, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"  salvo: {arq}")

        top_termo, top_excerto, top_data, top_url = "", "", "", ""
        for termo, gzs in achados_municipio.items():
            if gzs:
                top_termo = termo
                g = gzs[0]
                top_data = g.get("date", "")
                top_url = g.get("txt_url") or g.get("url") or ""
                excertos = g.get("excerpts", [])
                top_excerto = excertos[0] if excertos else ""
                break

        resumo_writer.writerow({
            "municipio": municipio, "uf": uf, "cod_ibge": ibge,
            "algum_achado": algum_achado,
            "termo_do_1o_achado": top_termo,
            "data_diario": top_data,
            "url_diario": top_url,
            "excerto": top_excerto.replace("\n", " ")[:500],
            "erro": erro,
        })
        resumo_f.flush()

    resumo_f.close()
    resumo_final = pd.read_csv(resumo_path, dtype={"cod_ibge": str})
    n_achados = int(resumo_final["algum_achado"].astype(str).str.lower().eq("true").sum())
    print(f"\n=== Resumo acumulado: {n_achados}/{len(resumo_final)} municipios "
          f"candidatos com algum achado por palavra-chave no Querido Diario "
          f"(desde o inicio, somando rodadas retomadas) ===")
    print(f"Detalhe em {resumo_path} e um .json por municipio com achado.")
    print("\nLembrete: achado aqui e TRIAGEM LEXICAL num diario oficial, nao e "
          "a lei em si - abrir o excerto/URL e confirmar antes de citar. E ausencia "
          "de achado pode ser cobertura incompleta do Querido Diario para esse "
          "municipio/ano, nao prova de ausencia da lei.")


if __name__ == "__main__":
    main()
