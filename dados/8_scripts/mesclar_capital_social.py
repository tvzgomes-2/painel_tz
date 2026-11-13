#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""mesclar_capital_social.py — indicador de porte por capital social declarado
(04/08/2026), a pedido do autor ("quais indicadores de proximidade... capital
social ou empregos?").

Mescla capital_social (RFB, empresas*.csv) para: (a) todas as empresas dos
componentes médio/pequeno/grande da rede v4 (~1.523 CNPJs, tam>=2) e (b) os
1.770 sócios-PJ diretos (candidatos a holding), casando por cnpj_basico.

⚠️ IMPORTANTE (lição aprendida 04/08/2026): os arquivos brutos da Receita
Federal (empresas*.csv, ESTABELECIMENTOS*.csv) são grandes (300 MB–4 GB por
parte) e o disco do ambiente é lento (~80 MB/s) — ler com csv.reader do Python
é seguro mas pode estourar limites de tempo de execução em sessões
interativas. Prefira **awk** (10-50x mais rápido) para o primeiro filtro por
CNPJ-alvo, e só then processe o resultado (pequeno) em Python. NÃO escreva
arquivos intermediários grandes (>500 MB) em /tmp de uma vez — já causou o
disco do sandbox encher e travar a sessão (ao tentar fatiar
ESTABELECIMENTOS0.csv, 4 GB, em pedaços de 512 MB simultâneos). Prefira
processar arquivo por arquivo, acumulando só a saída filtrada (pequena).

Layout empresas*.csv (";" delim, latin1, sem header):
  [0]=cnpj_basico [1]=razao_social [2]=natureza_juridica
  [3]=qualificacao_responsavel [4]=capital_social (vírgula decimal)
  [5]=porte_empresa [6]=ente_federativo

USO (exemplo prático rodado em 04/08/2026, via awk por arquivo — não este
script Python diretamente, que serve de referência/documentação do método):

  cd ".../filtrados (6 CNAEs transporte, 24-07-2026)"
  awk -F';' '
    NR==FNR{gsub(/"/,"",$1); a[$1]=1; next}
    { cnpj=$1; gsub(/"/,"",cnpj);
      if (cnpj in a) {
        gsub(/"/,"",$2); gsub(/"/,"",$3); gsub(/"/,"",$5); gsub(/"/,"",$6);
        print cnpj";"$2";"$3";"$5";"$6
      }
    }' alvo_cnpjs.txt "../Receita Federal - dados brutos/empresas0.csv" >> capital_social_por_cnpj_raw.csv
  # repetir para empresas1.csv .. empresas9.csv, um arquivo por vez

Depois, este módulo Python consolida o raw (dedupe) e agrega por componente.

SAÍDAS:
  - capital_social_por_cnpj.csv — 1 linha por CNPJ (cnpj_basico, razao_social,
    natureza_juridica, capital_social, porte_empresa).
  - capital_social_por_grupo.csv — agregado por componente_id (soma de
    capital_social), já casado com id_grupo/nome_sugerido de
    identificacao_componentes_medios_grandes_v4.csv (rodar
    reconstruir_identificacao_componentes.py ANTES deste, para que a
    atribuição de grupo seja por sócio-âncora, não por lista de CNPJ
    documental — ver ressalva no cabeçalho daquele script).

RESULTADO (04/08/2026): 2.992/2.992 CNPJs-alvo encontrados no cadastro
(100% de cobertura). Top capital social: Barata R$ 722,4 milhões (51
empresas), Belarmino R$ 289,2 milhões, Ruas R$ 280,7 milhões.
"""
import csv
import glob
import os
from collections import defaultdict

RAIZ = r"C:\Users\HOME\OneDrive\doutorado\03 - Dados\_data\CNPJ"
PASTA_BRUTOS = os.path.join(RAIZ, "Receita Federal - dados brutos")
PASTA_SAIDA = os.path.join(RAIZ, "filtrados (6 CNAEs transporte, 24-07-2026)")


def consolidar_raw(raw_path, saida_path):
    """Deduplica o resultado bruto do awk (pode ter linhas repetidas se um
    arquivo empresas*.csv foi processado 2x por retomada manual)."""
    rows = {}
    with open(raw_path, encoding="utf-8", errors="replace") as f:
        for linha in f:
            partes = linha.rstrip("\n").split(";")
            if len(partes) != 5:
                continue
            cnpj, razao, nat, cap, porte = partes
            rows[cnpj] = (razao, nat, cap, porte)
    with open(saida_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["cnpj_basico", "razao_social", "natureza_juridica", "capital_social", "porte_empresa"])
        for cnpj in sorted(rows):
            w.writerow([cnpj, *rows[cnpj]])
    print(f"{len(rows):,} CNPJs distintos -> {saida_path}")


def agregar_por_grupo(capital_csv, componentes_csv, identificacao_csv, saida_csv):
    cap = {}
    for r in csv.DictReader(open(capital_csv, encoding="utf-8")):
        try:
            cap[r["cnpj_basico"]] = float(r["capital_social"].replace(",", "."))
        except ValueError:
            cap[r["cnpj_basico"]] = None

    ident_por_cid = {r["componente_id"]: r for r in csv.DictReader(open(identificacao_csv, encoding="utf-8"))}

    agg = defaultdict(lambda: {"n": 0, "soma": 0.0, "sem_dado": 0})
    for r in csv.DictReader(open(componentes_csv, encoding="utf-8-sig")):
        cid = r["componente_id"]
        c = cap.get(r["cnpj_basico"].zfill(8))
        agg[cid]["n"] += 1
        if c is None:
            agg[cid]["sem_dado"] += 1
        else:
            agg[cid]["soma"] += c

    out_rows = []
    for cid, v in agg.items():
        info = ident_por_cid.get(cid, {})
        out_rows.append({
            "id_grupo": info.get("id_grupo", ""), "componente_id": cid, "tamanho": v["n"],
            "nome_sugerido": info.get("nome_sugerido", ""), "origem_nome": info.get("origem_nome", ""),
            "capital_social_total_reais": round(v["soma"], 2),
            "empresas_sem_capital_encontrado": v["sem_dado"],
        })
    out_rows.sort(key=lambda r: -r["capital_social_total_reais"])
    with open(saida_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
        w.writeheader()
        w.writerows(out_rows)
    print(f"{len(out_rows)} componentes -> {saida_csv}")


if __name__ == "__main__":
    print(__doc__)
