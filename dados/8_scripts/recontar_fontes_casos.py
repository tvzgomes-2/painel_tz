#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""recontar_fontes_casos.py — Frente 2 (25/09/2026): quais levantamentos externos registram cada caso da base-mestre.

Levantamentos (contam no nº): Brinco (2017), Santini (2019), Vermander (2021), Fernandes Pereira et al. (2023),
Angelo (2023), NTU (2024) [arquivo 'NTU 2023.csv' / coluna 'NTU (2023)' do Quadro — é a 1ª ed. da NTU 2024, ver
DB - NTU §10.3], NTU (2025), NTU (2026), UnB/Geourb (2025), Santini (Dataverse Z927PD, versões mar/2024 → abr/2026).
Flags das cinco fontes acadêmicas e da NTU 2024 vêm da aba 'Gomes (2024)' do Quadro TZ Brasil; NTU 2025/2026 e
UnB/Geourb só existem como marcação anterior na base-mestre (coluna 'Fontes que registram o caso', 11/09), que é
preservada e somada. Corroboração (não conta no nº, fica em coluna própria): MUNIC 2020 (autodeclaração de
isenção a toda a população), RSL (fichamentos que citam o município, do bloco gerado da ficha) e imprensa
(acervo de reportagens). Compilação própria anterior (Observatório/Quadro TZ) NÃO conta como fonte independente.
Read-only; com --gravar-mestre escreve 3 colunas novas no fim da base-mestre (backup antes)."""
import os, re, sys, glob, shutil, datetime, unicodedata, collections
import pandas as pd

R = os.environ.get("TZ_VAULT") or os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
K = os.path.join(R, "03 - Dados", "_data", "casos por fonte")
MES = os.path.join(K, "Municípios TZ - consolidado.xlsx")
FIC = os.path.join(R, "04 - Análises", "Casos municipais", "Fichas por município")
REP = os.path.join(R, "05 - Referências", "Reportagens por município")
BIB = os.path.join(R, "05 - Referências", "_zotero", "biblioteca.bib")
MUNS = os.path.join(R, "03 - Dados", "_data", "CNPJ", "Receita Federal - dados brutos", "municipios.csv")
RSLCSV = os.path.join(R, "05 - Referências", "Rede bibliométrica", "cobertura_literatura_municipios.csv")
HOJE = datetime.date.today().isoformat()
ACAD = re.compile(r"journal|revista|research|studies|review|cadernos?|policy|cities|transportation|transport |mobilit|urban|rbeur|estud|environment|behaviou?r|economi|geogra|anais|boletim|annals|sustainab|planning|science|sociedade|territ|ciencia|anpet|antp|ipea|scielo|lua nova|cebrap", re.I)
UF_NOME = {"AC": "acre", "AL": "alagoas", "AP": "amapa", "AM": "amazonas", "BA": "bahia", "CE": "ceara", "DF": "distrito federal", "ES": "espirito santo", "GO": "goias", "MA": "maranhao", "MT": "mato grosso", "MS": "mato grosso do sul", "MG": "minas gerais", "PA": "para", "PB": "paraiba", "PR": "parana", "PE": "pernambuco", "PI": "piaui", "RJ": "rio de janeiro", "RN": "rio grande do norte", "RS": "rio grande do sul", "RO": "rondonia", "RR": "roraima", "SC": "santa catarina", "SP": "sao paulo", "SE": "sergipe", "TO": "tocantins"}
PALAVRA_COMUM = {"portao", "palma", "palmas", "vargem", "colina", "castelo", "carmo", "aparecida", "conchas", "pains", "piedade", "brotas", "tiete", "salto", "machado", "cacoal", "picos", "claudio", "aruana", "faxinal", "antonina", "cianorte", "assis", "lins", "itapeva", "mariana", "caete", "jales", "irati", "sorriso", "vilhena", "tambau", "belo vale", "ijaci", "igarata", "morretes", "matinhos", "leopoldina", "pirapora", "formosa", "mendes", "canoas", "conchal"}
ACENTO = {"a": "áàâãä", "e": "éèêë", "i": "íìîï", "o": "óòôõö", "u": "úùûü", "c": "ç", "n": "ñ"}
def latex(s):
    s = re.sub(r"\\c\s*\{?c\}?", "c", s)
    s = re.sub(r"\\[\\'`^~\"vu]\{?([A-Za-z])\}?", r"\1", s)
    return re.sub(r"[{}\\$]", "", s)
def campo(corpo, c):
    m = re.search(r"^\s*" + c + r" = (\{.*?\}|\d+),?\s*$", corpo, re.S | re.M)
    return latex(m.group(1)) if m else ""
def zotero_noticias():
    """Itens de imprensa do export do Zotero: @article de veículo não acadêmico (sem DOI) e @misc com URL que não é catálogo de norma."""
    if not os.path.exists(BIB): return []
    txt = open(BIB, encoding="utf-8", errors="ignore").read()
    itens = []
    for m in re.finditer(r"^@(\w+)\{([^,]+),(.*?)(?=^@\w+\{|\Z)", txt, re.S | re.M):
        tipo, chave, corpo = m.group(1).lower(), m.group(2), m.group(3)
        jr, url, tit = campo(corpo, "journal"), campo(corpo, "url"), campo(corpo, "title")
        if tipo == "article" and jr and not ACAD.search(jr) and not campo(corpo, "doi"):
            veic = jr
        elif tipo == "misc" and url and not re.search(r"\blei\b|decreto", campo(corpo, "volume"), re.I) and not n(tit).startswith("tarifa zero de "):
            veic = re.sub(r"^https?://(www\.)?([^/]+).*", r"\2", url)
        else:
            continue
        itens.append({"chave": chave, "veiculo": veic, "titulo": tit, "ano": campo(corpo, "year") or campo(corpo, "date")[:4],
                      "texto": n(" ".join([tit, campo(corpo, "abstract"), campo(corpo, "keywords"), campo(corpo, "address"), campo(corpo, "note")]))})
    return itens
OUT = os.path.join(K, f"Recontagem de fontes por caso ({HOJE}).xlsx")
def split_topo(s, sep=";"):
    """Divide por `sep` só fora de parênteses (ex.: 'PNCP (PE 1/2026; Contrato 2/2026)' fica inteiro)."""
    out, cur, d = [], "", 0
    for ch in s:
        if ch == "(": d += 1
        elif ch == ")": d = max(0, d - 1)
        if ch == sep and d == 0: out.append(cur); cur = ""
        else: cur += ch
    out.append(cur)
    return out


UFS = set("AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split())
def n(s): return re.sub(r"\s+", " ", unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower().replace("'", "").replace("’", "")).strip()
ALIAS = {"arthur nogueira": "artur nogueira"}
def cidade_uf(txt, uf=None):
    k = _cidade_uf(txt, uf)
    return (ALIAS.get(k[0], k[0]), k[1])
def _cidade_uf(txt, uf=None):
    s = str(txt or "").strip()
    m = re.match(r"^(.*?)\s*(?:[-–(/,]\s*)([A-Z]{2})\)?\s*$", s)
    if m and m.group(2) in UFS: return n(m.group(1)), m.group(2)
    return n(s), (str(uf).strip().upper() if uf else None)

def main():
    fontes = collections.defaultdict(set)   # (mun,uf) -> {rótulo}
    santini_v = collections.defaultdict(list)
    q = pd.read_excel(os.path.join(K, "Quadro TZ Brasil.xlsx"), sheet_name="Gomes (2024)")
    q.columns = [c.strip() for c in q.columns]
    MAPQ = {"Brinco (2017)": "Brinco (2017)", "Santini (2019)": "Santini (2019)", "Vermander (2021)": "Vermander (2021)",
            "Fernandes Pereira et al. (2023)": "Fernandes Pereira et al. (2023)", "Angelo (2023)": "Angelo (2023)", "NTU (2023)": "NTU (2024)"}
    for r in q.itertuples(index=False):
        d = dict(zip(q.columns, r)); k = (n(d["Cidade"]), str(d["Estado"]).strip())
        for c, lab in MAPQ.items():
            if str(d.get(c)).strip() in ("1", "1.0"): fontes[k].add(lab)
    ntu25 = pd.read_csv(os.path.join(K, "NTU 2025 - TZ maiores cidades.csv"), sep=None, engine="python", on_bad_lines="skip")
    for c in ntu25.get("Cidade", []):
        k = cidade_uf(c)
        if k[1]: fontes[k].add("NTU (2025)")
    VERS = [("Fare-Free - March 2024.xlsx", "mar/2024"), ("Brazilian municipalities with full Fare-Free Public Transport policies - July 2024.xlsx", "jul/2024"),
            ("Brazilian municipalities with full Fare-Free Public Transport - January 2025-1.xlsx", "jan/2025"), ("Brazilian municipalities with full Fare-Free Public Transport - July 2025.xlsx", "jul/2025"),
            ("Brazilian municipalities with full Fare-Free Public Transport - September 2025.xlsx", "set/2025"), ("Brazilian municipalities with full Fare-Free Public Transport - April 2026-1.xlsx", "abr/2026")]
    for f, v in VERS:
        x = pd.read_excel(os.path.join(K, "Dataverse Santini", f), sheet_name=None)
        for s, d in x.items():
            if s == "about": continue
            cols = [str(c).strip() for c in d.columns]
            ci = 1 if cols[0] == "#" else 0
            cu = next((i for i, c in enumerate(cols) if c.lower().startswith("state")), None)
            for r in d.itertuples(index=False):
                cid = r[ci]
                if not isinstance(cid, str) or not cid.strip(): continue
                k = cidade_uf(cid, r[cu] if cu is not None else None)
                if k[1] in UFS and v not in santini_v[k]: santini_v[k].append(v)
    for k in santini_v: fontes[k].add("Santini (Dataverse)")
    # corroboração
    munic, rsl, imp = {}, {}, collections.Counter()
    for p in glob.glob(os.path.join(FIC, "Ficha - *.md")):
        if "BACKUP" in p: continue
        t = open(p, encoding="utf-8").read()
        mm = re.search(r"^municipio:\s*(.+)$", t, re.M); uu = re.search(r"^uf:\s*(.+)$", t, re.M)
        if not (mm and uu): continue
        k = (n(mm.group(1).strip().strip('"')), uu.group(1).strip().strip('"'))
        pass
    rc = pd.read_csv(RSLCSV, sep=";", dtype=str)
    ordemniv = {"A": 0, "B": 1, "C": 2}
    for (a, b), d in rc.groupby(["municipio", "uf"]):
        niv = sorted(d["nivel_municipio"].dropna(), key=lambda x: ordemniv.get(x, 9))
        rsl[(n(a), b)] = (d["fichamento"].nunique(), niv[0] if niv else "")
    zot = zotero_noticias()
    homon = collections.Counter(n(x) for x in pd.read_csv(MUNS, dtype=str)["nome"])
    zmatch = collections.defaultdict(list)
    mm0 = pd.read_excel(MES, sheet_name="consolidado")
    for _, r0 in mm0.iterrows():
        if r0["Situação"] not in ("Ativa", "Encerrada", "Pista (a verificar)"): continue
        nm, uf = n(r0["Município"]), r0["UF"]
        pat = re.compile(r"(?<![a-z])" + re.escape(nm) + r"(?![a-z])")
        exige_uf = homon[nm] > 1 or nm in PALAVRA_COMUM or len(nm) <= 5
        pat_uf = re.compile(r"(?<![a-z])(" + uf.lower() + "|" + UF_NOME[uf] + r")(?![a-z])")
        for it in zot:
            tx = it["texto"]
            if nm in UF_NOME.values():  # município com nome de estado (Goiás/GO): só com "cidade de <nome>"
                ok = bool(re.search(r"cidade de " + re.escape(nm), tx))
            elif not exige_uf:
                ok = bool(pat.search(tx))
            else:  # UF a até 40 caracteres da ocorrência (mesmo critério do mapear_rsl_municipios.py)
                ok = any(pat_uf.search(tx[max(0, mo.start() - 40):mo.end() + 40]) for mo in pat.finditer(tx))
            if ok:
                zmatch[(nm, uf)].append(it)
    rp = pd.read_csv(os.path.join(K, "reportagens_por_municipio.csv"), sep=";", dtype=str)
    urls = collections.defaultdict(set)
    for r in rp.itertuples(): urls[(n(r.Município), str(r.UF))].add(r.URL)
    for p in glob.glob(os.path.join(REP, "Reportagens - *.md")):
        mm = re.match(r"Reportagens - (.+) \(([A-Z]{2})\)\.md$", os.path.basename(p))
        if mm: urls[(n(mm.group(1)), mm.group(2))] |= set(re.findall(r"https?://[^\s)\]>]+", open(p, encoding="utf-8").read()))

    m = pd.read_excel(MES, sheet_name="consolidado")
    rows = []
    for _, r in m.iterrows():
        if r["Situação"] not in ("Ativa", "Encerrada", "Pista (a verificar)"): continue
        k = (n(r["Município"]), r["UF"])
        antes = [x.strip() for x in split_topo(str(r.get("Fontes que registram o caso") or "")) if x.strip() and x.strip() != "nan"]
        f = set(antes) | fontes.get(k, set())
        ordem = ["Brinco (2017)", "Santini (2019)", "Vermander (2021)", "Fernandes Pereira et al. (2023)", "Angelo (2023)", "NTU (2024)", "NTU (2025)", "NTU (2026)", "UnB/Geourb (2025)", "Santini (Dataverse)"]
        fl = [x for x in ordem if x in f] + sorted(x for x in f if x not in ordem)
        fl = [x + (f" [{santini_v[k][0]}–{santini_v[k][-1]}]" if x == "Santini (Dataverse)" and santini_v.get(k) else "") for x in fl]
        cor = []
        if str(r.get("MUNIC 2020 (autodeclarado) — isenção 'toda a população'")) == "Sim": cor.append("MUNIC 2020: declara isenção a toda a população")
        if k in rsl: cor.append(f"RSL: {rsl[k][0]} fichamento(s), nível {rsl[k][1]}")
        else: cor.append("RSL: nenhuma menção nos fichamentos")
        zk = {x["chave"]: x for x in zmatch.get(k, [])}
        cor.append(f"imprensa no acervo: {len(urls.get(k, ()))} URL(s)")
        cor.append(f"imprensa no Zotero: {len(zk)} item(ns)" + ((" — " + "; ".join(f"{x['veiculo']} {x['ano']} [@{c}]" for c, x in list(zk.items())[:6]) + ("…" if len(zk) > 6 else "")) if zk else ""))
        rows.append({"Município": r["Município"], "UF": r["UF"], "Situação": r["Situação"], "Levantamentos": "; ".join(fl), "Nº de levantamentos": len(fl),
                     "Antes (coluna de 11/09)": "; ".join(antes), "Nº antes": r.get("Nº de fontes"), "Corroboração": " · ".join(cor),
                     "Santini — versões": ", ".join(santini_v.get(k, [])),
                     "RSL — fichamentos": rsl.get(k, (0, ""))[0], "RSL — nível": rsl.get(k, (0, ""))[1],
                     "Imprensa — acervo (URLs)": len(urls.get(k, ())), "Imprensa — Zotero (itens)": len(zk),
                     "Imprensa — acervo ou Zotero": "sim" if (urls.get(k) or zk) else "não"})
    T = pd.DataFrame(rows)
    esc = T[T.Situação.isin(["Ativa", "Encerrada"])]
    dist = esc["Nº de levantamentos"].value_counts().sort_index()
    so_santini = (esc.Levantamentos.str.fullmatch(r"Santini \(Dataverse\)( \[.*\])?")).sum()
    zero = esc[esc["Nº de levantamentos"] == 0]
    leia = ["Recontagem de fontes por caso — " + HOJE + " (_meta/scripts/recontar_fontes_casos.py).",
            "Autor: Thiago Von Zeidler Gomes · Orientadora: Prof.ª Dra. Silvana Zioni", "",
            f"Registros em escopo: {len(esc)}", "Distribuição do nº de levantamentos: " + ", ".join(f"{i}: {v}" for i, v in dist.items()),
            f"Só no Santini (Dataverse): {so_santini}", f"Nenhum levantamento externo: {len(zero)} — " + "; ".join(f"{a}/{b}" for a, b in zip(zero.Município, zero.UF)),
            f"RSL (cobertura_literatura_municipios.csv, regerado por mapear_rsl_municipios.py): {int((esc['RSL — fichamentos'] > 0).sum())} registros mencionados em algum fichamento — A {int((esc['RSL — nível'] == 'A').sum())} · B {int((esc['RSL — nível'] == 'B').sum())} · C {int((esc['RSL — nível'] == 'C').sum())}.",
            f"Imprensa: Zotero ({len(zot)} itens de imprensa no biblioteca.bib) casa com {int((esc['Imprensa — Zotero (itens)'] > 0).sum())} registros; acervo de reportagens, {int((esc['Imprensa — acervo (URLs)'] > 0).sum())}; pelo menos um dos dois, {int((esc['Imprensa — acervo ou Zotero'] == 'sim').sum())}.",
            "Zotero: casamento por nome do município no título/resumo/palavras-chave/nota; nome homônimo em outra UF, palavra comum ou nome curto exige a UF (sigla ou nome do estado) no texto. Conferir a aba 'Zotero — casamentos'.",
            "", "Nota: 'Pereira et al. (2023)' do Quadro (335 marcações) não foi usada — o significado da coluna não está documentado; conferir antes de somar."]
    with pd.ExcelWriter(OUT) as w:
        pd.DataFrame({"Leia-me": leia}).to_excel(w, sheet_name="Leia-me", index=False); T.to_excel(w, sheet_name="Por caso", index=False)
        pd.DataFrame([{"Município": a, "UF": b, "Chave Zotero": "@" + x["chave"], "Veículo": x["veiculo"], "Ano": x["ano"], "Título": x["titulo"]} for (a, b), L in zmatch.items() for x in L]).to_excel(w, sheet_name="Zotero — casamentos", index=False)
    print("\n".join(leia[3:10])); print("->", OUT)
    if "--gravar-mestre" in sys.argv:
        import openpyxl
        bk = os.path.join(R, "_meta", "_backups", f"recontar-fontes-{datetime.datetime.now():%Y%m%d-%H%M%S}"); os.makedirs(bk); shutil.copy2(MES, bk)
        wb = openpyxl.load_workbook(MES); ws = wb["consolidado"]; h = [c.value for c in ws[1]]
        novas = ["Fontes — levantamentos (recontagem)", "Fontes — nº de levantamentos (recontagem)", "Fontes — corroboração (MUNIC, RSL, imprensa)"]
        for c in novas:
            if c not in h: ws.cell(row=1, column=len(h) + 1, value=c); h.append(c)
        idx = {(n(x["Município"]), x["UF"], x["Situação"]): x for x in rows}
        for rr in ws.iter_rows(min_row=2):
            x = idx.get((n(rr[0].value), rr[1].value, rr[3].value))
            if not x: continue
            for c, v in zip(novas, (x["Levantamentos"], x["Nº de levantamentos"], x["Corroboração"] + f" (recontagem {HOJE})")):
                ws.cell(row=rr[0].row, column=h.index(c) + 1, value=v)
        wb.save(MES); print("mestre gravada; backup", bk)

if __name__ == "__main__":
    main()
