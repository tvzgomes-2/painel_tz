#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""regua_descritiva_da_base.py — regera a subseção "Régua descritiva" (§5) das fichas a partir da BASE-MESTRE
(campos Régua — aba, Régua — subtipo, Régua — portão, Classificação provisória, Cobertura da rede).
Decisão do autor, 30/10/2026 (releitura das normas, item 10): o gerador antigo (enriquecer_prosa_municipal.py) lia só a régua e
escrevia "candidato … sem evidência documentada" para casos já decididos. Usa os mesmos marcadores com hash: texto editado à mão
(hash divergente) NÃO é sobrescrito. Simula por padrão; --gravar grava com backup.
Uso (da raiz do cofre): python _meta/scripts/regua_descritiva_da_base.py [--gravar] [--so "Município" UF]"""
import os, sys, re, glob, shutil, datetime, argparse, unicodedata, openpyxl
RAIZ = os.environ.get("TZ_VAULT") or os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import enriquecer_prosa_municipal as EP
from enriquecer_regua_portao import CAMADA
nz = lambda s: unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower().strip()
def rot(sub):
    r = CAMADA.get(sub, (sub, None))[0]
    return r.split("**")[1] if "**" in r else r
def limpa(s):
    s = re.sub(r"\s+", " ", str(s or "")).strip().rstrip(".")
    return s
def texto(r, g):
    mun = g(r, "Município"); aba = str(g(r, "Régua — aba") or ""); sub = str(g(r, "Régua — subtipo") or "").strip()
    por = limpa(g(r, "Régua — portão")); hip = limpa(g(r, "Classificação provisória (hipótese pré-e-SIC)")); cob = limpa(g(r, "Cobertura da rede"))
    subs = [x.strip() for x in sub.split("+") if x.strip()]
    rots = " e ".join(rot(x) for x in subs) if subs else ""
    if por.lower() in ("", "none", "a verificar"): por = ""
    if aba.startswith("3"):
        s = f"{mun} está entre as **encerradas** (camada 3)" + (f"; o último desenho foi {rots}" if rots else "; o subtipo do último desenho está a decidir")
    elif rots:
        s = f"{mun} está na camada {rots}" + (" — por hipótese pré-e-SIC, até a resposta do pedido" if hip else "")
    else:
        s = f"A camada de {mun} ainda não está determinada na base"
    s += (f". Portão: {por}." if por else ".")
    if hip: s += f" Hipótese registrada: {hip}."
    if cob and not cob.lower().startswith(("não verificada", "nao verificada", "none")):
        s += f" Cobertura da rede: {cob}."
    else:
        s += " Cobertura da rede: não aferida na base-mestre."
    s += " (Texto gerado da base-mestre; a classificação é da base, não desta ficha.)"
    return "### Régua descritiva\n\n" + s
def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--gravar", action="store_true"); ap.add_argument("--so", nargs=2); a = ap.parse_args()
    ws = openpyxl.load_workbook(os.path.join(RAIZ, "03 - Dados/_data/casos por fonte/Municípios TZ - consolidado.xlsx"), read_only=True)["consolidado"]
    rows = list(ws.iter_rows(values_only=True)); H = list(rows[0]); g = lambda r, k: r[H.index(k)]
    base = {(nz(r[0]), r[1]): r for r in rows[1:] if r[0]}
    st = {}; plano = []
    for p in sorted(glob.glob(os.path.join(RAIZ, "04 - Análises/Casos municipais/Fichas por município/Ficha - *.md"))):
        t = open(p, encoding="utf-8").read()
        mm = re.search(r"^municipio:\s*(.+)$", t, re.M); uu = re.search(r"^uf:\s*(.+)$", t, re.M)
        if not (mm and uu): continue
        mun, uf = mm.group(1).strip().strip('"'), uu.group(1).strip().strip('"')
        if a.so and (nz(mun), uf) != (nz(a.so[0]), a.so[1]): continue
        r = base.get((nz(mun), uf))
        if r is None or g(r, "Situação") not in ("Ativa", "Encerrada"): st["fora da base/escopo"] = st.get("fora da base/escopo", 0) + 1; continue
        novo, s = EP.aplicar_bloco(t, "regua_descritiva", texto(r, g), [r"^## 5\.\s*Classifica.*?$"], False)
        st[s] = st.get(s, 0) + 1
        if novo != t: plano.append((p, novo))
        if s in ("divergente-pulado", "conteudo-manual-pulado"): print("pulado (texto à mão):", os.path.basename(p))
    print(st, "| a gravar:", len(plano))
    if a.gravar and plano:
        bk = os.path.join(RAIZ, "_meta/_backups", "regua-descritiva-" + datetime.datetime.now().strftime("%Y%m%d-%H%M")); os.makedirs(bk, exist_ok=True)
        for p, novo in plano:
            shutil.copy2(p, os.path.join(bk, os.path.basename(p) + ".bak")); open(p, "w", encoding="utf-8", newline="\n").write(novo)
        print("gravado em", os.path.basename(bk))
if __name__ == "__main__": main()
