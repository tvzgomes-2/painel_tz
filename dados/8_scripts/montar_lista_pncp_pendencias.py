# -*- coding: utf-8 -*-
r"""montar_lista_pncp_pendencias.py — monta a lista de municípios com pendência de contrato ou legislação para a busca no PNCP.

Autor: Thiago Von Zeidler Gomes · Orientadora: Prof.ª Dra. Silvana Zioni · script escrito com Claude (05/11/2026).

Para quê: reproduzir, a partir da base viva, a lista usada na nota "Pendências de contratos e legislação (05-11-2026)"
e na busca do PNCP (buscar_pncp_pendencias.py). Só leitura: não altera a base.

Critério (casos em escopo = Estado terminal "Fechado…" ou "Aguarda e-SIC…"), um grupo por caso, nesta ordem:
  1. Legislação não localizada — coluna "Norma lida (A.2e)" = "não localizada".
  2. Sem contrato no cofre, operador privado ou indefinido — nenhum arquivo do município em contratos/<UF>/
     (fora .txt/.md/.json) e Operador/Prestação sem sinal de prestação direta.
  3. Sem contrato no cofre, prestação direta — idem, com sinal de prestação direta: Operador começa por Prefeitura,
     Município, estrutura municipal, frota própria, autarquia, empresa pública, EPT ou secretaria; ou Prestação diz
     "prestação/operação/execução/gestão direta", frota própria, autarquia, empresa pública ou motoristas servidores.
  4. Com contrato no cofre, remuneração ou contrapartida não apuradas — Remuneração "não apurado/não verificado/vazio"
     ou "Contrapartida — estado" = "não apurado".
Os casos de política sem norma não entram no grupo 1 (a norma "não existe", decisão do autor de 04/11/2026).
Órgãos conhecidos (CNPJ das Prefeituras) vêm das listas PNCP de 14/10 e 17/10/2026.

Uso (da raiz do cofre):  python _meta/scripts/montar_lista_pncp_pendencias.py [--saida caminho.csv]
"""
import argparse, collections, csv, glob, os, re, unicodedata
import openpyxl

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
P = lambda *x: os.path.join(RAIZ, *x)
MESTRE = P("03 - Dados", "_data", "casos por fonte", "Municípios TZ - consolidado.xlsx")
CONTRATOS = P("03 - Dados", "_data", "Legislacao e contratos TZ", "contratos")
LISTAS_ORGAOS = [P("_meta", "scripts", "_scratch", "levantar-1017", "lista_pncp_fundida_1017.csv"),
                 P("_meta", "scripts", "_scratch", "operadores-1014", "lista_pncp_operadores_1014.csv")]
SAIDA = P("_meta", "scripts", "_scratch", "releitura-1030", "lista_pncp_pendencias_1105.csv")
DIRETA_OP = re.compile(r"^\W*(prefeitura|munic[ií]pio\b|estrutura municipal|frota pr[oó]pria|autarquia|empresa p[uú]blica|\bEPT\b|secretaria)", re.I)
DIRETA_PREST = re.compile(r"(presta[cç][aã]o|opera[cç][aã]o|execu[cç][aã]o|gest[aã]o) (pr[oó]pria e )?direta|frota pr[oó]pria|autarquia|empresa p[uú]blica|motoristas? (servidores|do munic[ií]pio|pr[oó]prios)", re.I)
def direta(op, prest): return bool(DIRETA_OP.search(op) or DIRETA_PREST.search(prest))
GRUPOS = {1: "1. Legislação não localizada", 2: "2. Sem contrato, operador privado ou indefinido",
          3: "3. Sem contrato, prestação direta", 4: "4. Com contrato, remuneração/contrapartida não apuradas"}

def nz(s): return unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower().strip()
def nao_apurado(v):
    v = str(v or "").strip().lower()
    return (not v) or v.startswith(("não apurad", "nao apurad", "não verificad", "none", "não localiz", "não encontrad"))

def contratos_por_municipio():
    c = collections.Counter()
    for p in glob.glob(os.path.join(CONTRATOS, "*", "*")):
        b, uf = os.path.basename(p), os.path.basename(os.path.dirname(p))
        if f"-{uf} - " in b and not b.endswith((".txt", ".md", ".json")):
            c[(nz(b.split(f"-{uf} - ")[0]), uf)] += 1
    return c

def orgaos_conhecidos():
    org = {}
    for p in LISTAS_ORGAOS:
        if not os.path.exists(p): continue
        for m in csv.DictReader(open(p, encoding="utf-8-sig"), delimiter=";"):
            if m.get("orgaos_conhecidos"): org.setdefault((nz(m["municipio"]), m["uf"]), set()).update(m["orgaos_conhecidos"].split())
    return org

def montar():
    rows = list(openpyxl.load_workbook(MESTRE, read_only=True)["consolidado"].iter_rows(values_only=True)); H = list(rows[0])
    g = lambda r, k: str(r[H.index(k)] or "").strip()
    cont, org, out = contratos_por_municipio(), orgaos_conhecidos(), []
    for r in rows[1:]:
        if not r[0] or not g(r, "Estado terminal (completude)").startswith(("Fechado", "Aguarda")): continue
        k = (nz(r[0]), r[1]); op, prest = g(r, "Operador"), g(r, "Prestação (eixo 2)")
        if g(r, "Norma lida (A.2e)").startswith("não localizada"): gr = 1
        elif not cont[k]: gr = 3 if direta(op, prest) else 2
        elif nao_apurado(g(r, "Remuneração do operador")) or g(r, "Contrapartida — estado") == "não apurado": gr = 4
        else: continue
        out.append({"municipio": r[0], "uf": r[1], "ibge": re.sub(r"\D", "", g(r, "Código IBGE"))[:7], "grupo": GRUPOS[gr],
                    "orgaos_conhecidos": " ".join(sorted(org.get(k, set()))), "operador_atual": op[:120], "cnpj_atual": g(r, "Operador — CNPJ")[:20]})
    out.sort(key=lambda o: (o["grupo"], o["uf"], nz(o["municipio"])))
    return out

def gravar(out, saida=SAIDA):
    os.makedirs(os.path.dirname(saida), exist_ok=True)
    with open(saida, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["municipio", "uf", "ibge", "grupo", "orgaos_conhecidos", "operador_atual", "cnpj_atual"], delimiter=";")
        w.writeheader(); w.writerows(out)
    return saida

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Lista de municípios com pendência de contrato ou legislação (para o PNCP).")
    ap.add_argument("--saida", default=SAIDA); a = ap.parse_args()
    out = montar(); p = gravar(out, a.saida)
    print(f"{len(out)} municípios → {p}")
    for k, v in sorted(collections.Counter(o["grupo"] for o in out).items()): print(f"  {v:>3}  {k}")
    sem = [o["municipio"] for o in out if len(o["ibge"]) != 7]
    if sem: print("  atenção, sem código IBGE:", "; ".join(sem))
