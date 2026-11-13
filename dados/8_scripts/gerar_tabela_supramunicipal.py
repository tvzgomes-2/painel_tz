#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""gerar_tabela_supramunicipal.py (27/09/2026) — regera a seção '## 2. Principais dados'
da [[Ficha — Políticas federais, estaduais e distritais de gratuidade]] a partir da aba
'Nacionais e estaduais' de `Tipologias TZ - consolidado.xlsx`. Idempotente; casa os
marcadores <!-- tabela:supramunicipal:inicio/fim --> e aborta se não os achar.
USO  python gerar_tabela_supramunicipal.py [--gravar]   (simula por padrão; backup em _meta/_backups/)
"""
import argparse, datetime, os, shutil, sys
RAIZ = os.environ.get("TZ_VAULT") or os.getcwd()
TIP = os.path.join(RAIZ, "03 - Dados", "_data", "casos por fonte", "Tipologias TZ - consolidado.xlsx")
FICHA = os.path.join(RAIZ, "04 - Análises", "Casos municipais", "Ficha — Políticas federais, estaduais e distritais de gratuidade.md")
INI, FIM = "<!-- tabela:supramunicipal:inicio -->", "<!-- tabela:supramunicipal:fim -->"
GRUPOS = [("F", "2.1 Federal (normas, decisões, propostas)"), ("E", "2.2 Estadual (gratuidade temporal e cofinanciamento)"),
          ("D", "2.3 Distrital"), ("G", "2.4 Gratuidades de grupo (categoriais)")]

def cel(v):
    return str(v or "—").replace("|", "/").replace("\n", " ").strip()

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--gravar", action="store_true"); a = ap.parse_args()
    import openpyxl
    ws = openpyxl.load_workbook(TIP, read_only=True, data_only=True)["Nacionais e estaduais"]
    rr = list(ws.iter_rows(values_only=True)); H = [str(x) for x in rr[0]]; I = {h: i for i, h in enumerate(H)}
    linhas = [r for r in rr[1:] if r and r[0]]
    hoje = datetime.date.today().strftime("%d/%m/%Y")
    L = [INI, "", f"_Gerado por `_meta/scripts/gerar_tabela_supramunicipal.py` da aba **Nacionais e estaduais** ({len(linhas)} linhas) em {hoje}. Não editar à mão: editar a aba e regerar._", ""]
    for pre, tit in GRUPOS:
        g = [r for r in linhas if str(r[0]).startswith(pre)]
        if not g: continue
        L += [f"### {tit}", "", "| ID | Ente | Instrumento | Data | Serviços | Portão | Situação | Confiança |", "|---|---|---|---|---|---|---|---|"]
        for r in g:
            L.append("| " + " | ".join(cel(r[I[c]]) for c in ["ID", "Ente", "Instrumento", "Data", "Serviços abrangidos", "Portão", "Situação", "Confiança"]) + " |")
        L.append("")
    L.append(FIM)
    novo_bloco = "\n".join(L)
    t = open(FICHA, encoding="utf-8").read()
    if t.count(INI) != 1 or t.count(FIM) != 1:
        sys.exit("🔴 marcadores ausentes ou duplicados — nada foi escrito")
    i, j = t.index(INI), t.index(FIM) + len(FIM)
    novo = t[:i] + novo_bloco + t[j:]
    if novo == t:
        print("sem alteração (idempotente)."); return
    if not a.gravar:
        print(f"{len(linhas)} linhas; {len(t)} → {len(novo)} caracteres. Nada escrito. Para aplicar: --gravar"); return
    bk = os.path.join(RAIZ, "_meta", "_backups", "tabela-supramunicipal-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))
    os.makedirs(bk, exist_ok=True); shutil.copy2(FICHA, bk)
    open(FICHA, "w", encoding="utf-8", newline="\n").write(novo); print(f"✅ tabela regerada ({len(linhas)} linhas) · backup {bk}")

if __name__ == "__main__":
    main()
