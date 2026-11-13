#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""MUNIC (IBGE, autodeclarado pela prefeitura) × levantamento documental/empírico da tese.
Compara, por município: existência de TZ (MUNIC 2020 MTRA2010 'toda a população' isenta), existência de ônibus
intramunicipal (MTRA19; 2017), forma de prestação/regulamentação (MTRA1911-1915; 2017) e plano de transporte (MTRA07).
Saída: xlsx de comparação + colunas 'MUNIC … (autodeclarado)' na mestre. Read-only sobre a MUNIC."""
import csv, json, re, unicodedata, collections, shutil, datetime, openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
MU = "03 - Dados/_data/MUNIC"; K = "03 - Dados/_data/casos por fonte"
M = K + "/Municípios TZ - consolidado.xlsx"; T = K + "/Tipologias TZ - consolidado.xlsx"
OUT = K + "/MUNIC x levantamento documental (24-09-2026).xlsx"
def n(s): return re.sub(r"\s+", " ", unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower().strip())
# MUNIC 2020
ws = openpyxl.load_workbook(MU + "/Base_MUNIC_2020.xlsx", read_only=True)["Transporte"]
rr = list(ws.iter_rows(values_only=True)); H = [str(x) for x in rr[0]]
M20 = {str(x[0])[:6]: {h: (str(v) if v is not None else "") for h, v in zip(H, x)} for x in rr[1:]}
M17 = {}
for r in csv.DictReader(open(MU + "/munic_transporte_2017_por_municipio.csv", encoding="utf-8")): M17[r["cod_ibge"][:6]] = r
M12 = {}
for r in csv.DictReader(open(MU + "/munic_transporte_2012_por_municipio.csv", encoding="utf-8")): M12[r["cod_ibge_6"][:6]] = r
def reg20(d):
    if d.get("Mtra19") != "Sim": return ""
    L = [lab for c, lab in (("Mtra1911", "concessão"), ("Mtra1912", "permissão"), ("Mtra1913", "autorização"), ("Mtra1914", "prestação direta"), ("Mtra1915", "não regulamentado")) if d.get(c) == "Sim"]
    return "; ".join(L)
def reg17(d):
    if not d or d.get("munic_onibus_intramun_2017") != "1": return ""
    L = [lab for c, lab in (("munic_concessao_2017", "concessão"), ("munic_permissao_2017", "permissão"), ("munic_autorizacao_2017", "autorização"), ("munic_prestacao_direta_2017", "prestação direta"), ("munic_nao_regulamentado_2017", "não regulamentado")) if d.get(c) == "1"]
    return "; ".join(L)
ISEN = [("Mtra201", "idosos"), ("Mtra202", "estud. pública"), ("Mtra203", "estud. privada"), ("Mtra204", "carteiros"), ("Mtra205", "PcD"), ("Mtra206", "policiais"), ("Mtra207", "professores"), ("Mtra208", "crianças <5"), ("Mtra209", "outros"), ("Mtra2010", "TODA A POPULAÇÃO"), ("Mtra2011", "nenhum")]
# nosso levantamento
wb = openpyxl.load_workbook(M, read_only=True); r = list(wb["consolidado"].iter_rows(values_only=True)); hm = r[0]
OUR = {}
for x in r[1:]:
    if not x[0]: continue
    d = dict(zip(hm, x)); cod = str(d.get("Código IBGE") or "")[:6]
    if cod in OUR:  # 2 políticas (Palmas/TO)
        OUR[cod]["_multi"] = True; OUR[cod]["Situação"] = f'{OUR[cod]["Situação"]} + {d["Situação"]}'; continue
    OUR[cod] = d
wt = openpyxl.load_workbook(T, read_only=True)
REG2 = {}
rr2 = list(wt["2 Parcial"].iter_rows(values_only=True)); h2 = rr2[0]
for x in rr2[1:]:
    d = dict(zip(h2, x)); cod = str(d.get("Código IBGE") or "")[:6]
    key = cod or n(d["Município"]) + "|" + str(d["UF"])
    REG2.setdefault(key, []).append(d)
REG2n = {n(d["Município"]) + "|" + str(d["UF"]): v for v in REG2.values() for d in v}
def ano(v):
    m = re.search(r"(19|20)\d{2}", str(v or "")); return int(m.group(0)) if m else None
def ativa_em(d, y):
    s = str(d.get("Situação") or "")
    if s.startswith(("Excluída", "Reclassificada")): return None
    a = ano(d.get("Ano início")); f = ano(d.get("Fim"))
    if a is None: return "sem ano"
    if a > y: return "depois"
    if f and f < y: return "encerrada antes"
    return "ativa"
def categoria(d20, our, y=2020):
    tz = d20.get("Mtra2010"); bus = d20.get("Mtra19")
    if bus in ("Recusa", "Não informou") or not d20: return "MUNIC sem resposta"
    st = ativa_em(our, y) if our else None
    if our and st == "ativa":
        if bus == "Não": return "DIVERGE — nós: TZ ativa em 2020 · MUNIC: sem ônibus intramunicipal"
        if tz == "Sim": return "CONCORDA — TZ nos dois"
        return "DIVERGE — nós: TZ ativa em 2020 · MUNIC: não declara 'toda a população'"
    if our and st == "depois":
        return "MUNIC antecipa — declara TZ antes do início que documentamos" if tz == "Sim" else "consistente — TZ começou depois de 2020"
    if our and st == "encerrada antes":
        return "MUNIC declara TZ, mas documentamos fim antes de 2020" if tz == "Sim" else "consistente — encerrada antes de 2020"
    if our and st == "sem ano":
        return "sem ano de início no levantamento (MUNIC: " + ("declara TZ)" if tz == "Sim" else "não declara TZ)")
    if tz == "Sim": return "MUNIC declara TZ — fora da nossa base (candidato ou autodeclaração não confirmada)"
    return ""
def prestacao_cmp(r20, eixo2):
    e = (eixo2 or "").lower()
    if not r20 or not e or e == "não encontrado": return ""
    direta_m = "prestação direta" in r20; direta_n = "prestação direta" in e or "empresa pública" in e
    privada_m = any(k in r20 for k in ("concessão", "permissão", "autorização"))
    privada_n = any(k in e for k in ("aditivo", "contrato", "locação", "concessão", "emergencial"))
    if direta_n and direta_m and not privada_m: return "concorda (direta)"
    if privada_n and privada_m and not direta_m: return "concorda (terceiro)"
    if direta_n and not direta_m: return "DIVERGE — nós: direta · MUNIC: " + r20
    if privada_n and direta_m and not privada_m: return "DIVERGE — nós: terceiro · MUNIC: prestação direta"
    return "parcial — MUNIC: " + r20
rows = []
cods = set(OUR) | {c for c, d in M20.items() if d.get("Mtra2010") == "Sim"}
for cod in sorted(cods):
    d20 = M20.get(cod, {}); our = OUR.get(cod); d17 = M17.get(cod, {}); d12 = M12.get(cod, {})
    nome = (our or {}).get("Município") or d20.get("Mun", ""); uf = (our or {}).get("UF") or d20.get("UF", "")
    r2 = REG2.get(cod) or REG2n.get(n(nome) + "|" + str(uf)) or []
    universo = "em escopo (mestre)" if our and ativa_em(our, 2030) is not None else ("mestre — fora de escopo" if our else ("camada 2 da régua" if any(x.get("Modelo") != "temporaria" for x in r2) else ("só 2d eleitoral" if r2 else "fora da nossa base")))
    r20 = reg20(d20); cat = categoria(d20, our)
    if not our and r2 and d20.get("Mtra2010") == "Sim":
        sub = ", ".join(sorted({str(x.get("Subtipo")) for x in r2 if x.get("Subtipo")}))
        cat = f"MUNIC declara TZ — nós classificamos como parcial ({sub})"
    rows.append({
        "Município": nome, "UF": uf, "Código IBGE": cod, "Universo no nosso levantamento": universo,
        "Nossa situação": (our or {}).get("Situação", ""), "Nosso ano de início": (our or {}).get("Ano início", ""), "Nosso fim": (our or {}).get("Fim", ""),
        "Nossa régua (aba/subtipo)": " ".join(x for x in ((our or {}).get("Régua — aba", "") or "", (our or {}).get("Régua — subtipo", "") or "") if x),
        "Nossa prestação (eixo 2)": (our or {}).get("Prestação (eixo 2)", ""), "Nosso operador": (our or {}).get("Operador", ""),
        "Nosso PlanMob (declarado)": (our or {}).get("PlanMob — declarado", ""),
        "MUNIC 2020 — ônibus intramunicipal": d20.get("Mtra19", "(sem registro)"),
        "MUNIC 2020 — isenção 'toda a população'": d20.get("Mtra2010", ""),
        "MUNIC 2020 — isenções declaradas": "; ".join(lab for c, lab in ISEN if d20.get(c) == "Sim"),
        "MUNIC 2020 — regulamentação": r20,
        "MUNIC 2020 — intermunicipal atende deslocamento interno": d20.get("Mtra231", ""),
        "MUNIC 2020 — Plano Municipal de Transporte": d20.get("Mtra07", ""),
        "MUNIC 2017 — ônibus intramunicipal": {"1": "Sim", "0": "Não"}.get(d17.get("munic_onibus_intramun_2017", ""), ""),
        "MUNIC 2017 — regulamentação": reg17(d17),
        "MUNIC 2012 — ônibus intramunicipal": {"1": "Sim", "0": "Não"}.get(d12.get("munic_onibus_intramun_2012", ""), ""),
        "Comparação — existência de TZ (2020)": cat,
        "Comparação — prestação": prestacao_cmp(r20, (our or {}).get("Prestação (eixo 2)", "")),
        "Comparação — plano de transporte": ("" if not our else ("concorda" if str((our or {}).get("PlanMob — declarado", "")).lower().startswith(("sim", "s")) == (d20.get("Mtra07") == "Sim") else f"DIVERGE — nós: {our.get('PlanMob — declarado', '')} · MUNIC: {d20.get('Mtra07', '')}")) if d20 else "",
    })
C = collections.Counter
cat_counts = C(r["Comparação — existência de TZ (2020)"] for r in rows if r["Comparação — existência de TZ (2020)"])
pre_counts = C(re.sub(r" · MUNIC:.*| — MUNIC:.*", "", r["Comparação — prestação"]) for r in rows if r["Comparação — prestação"])
# xlsx
wb = openpyxl.Workbook(); w = wb.active; w.title = "Leia-me"
L = ["MUNIC (IBGE) × levantamento documental/empírico da tese — 24/09/2026",
 "A MUNIC é AUTODECLARADA: o gestor municipal responde ao questionário do IBGE, sem exigência de documento. Nosso levantamento exige a norma lida no dispositivo e prova de operação (regras A.2 e A.2c). Os dois medem coisas diferentes e não se substituem: a MUNIC diz o que a prefeitura declara; nós dizemos o que os documentos sustentam.",
 "Variáveis usadas (MUNIC 2020, bloco 3.3): MTRA19 (ônibus intramunicipal), MTRA1911–1915 (concessão, permissão, autorização, prestação direta, não regulamentado — não exclusivas), MTRA201–2011 (isenção formal da tarifa por grupo; MTRA2010 = 'toda a população', que tratamos como TZ autodeclarada), MTRA07 (Plano Municipal de Transporte), MTRA231 (intermunicipal que atende deslocamento interno). MUNIC 2017 e 2012: ônibus intramunicipal e regulamentação.",
 "Cuidados: (1) data de referência = coleta de 2020 — casos com início depois disso não são comparáveis; (2) 'toda a população' pode ser marcada por quem tem gratuidade ampla mas com portão (cadastro, residência), ou por engano; (3) 'Recusa'/'Não informou' ≠ 'Não'; (4) 'Plano Municipal de Transporte' da MUNIC não é necessariamente o PlanMob da Lei 12.587; (5) regulamentação é múltipla (um município pode marcar concessão e prestação direta).",
 "", "Resumo — existência de TZ (2020):"]
for i, l in enumerate(L, 1): w.cell(i, 1, l)
ri = len(L) + 1
for kx, v in cat_counts.most_common(): w.cell(ri, 1, kx); w.cell(ri, 2, v); ri += 1
ri += 1; w.cell(ri, 1, "Resumo — prestação (casos com prestação documentada):").font = Font(bold=True); ri += 1
for kx, v in pre_counts.most_common(): w.cell(ri, 1, kx); w.cell(ri, 2, v); ri += 1
w["A1"].font = Font(bold=True, size=13); w.column_dimensions["A"].width = 120; w.column_dimensions["B"].width = 10
Hh = list(rows[0].keys())
def sheet(name, data):
    s = wb.create_sheet(name); s.append(Hh)
    for c in range(1, len(Hh) + 1):
        x = s.cell(1, c); x.font = Font(bold=True, color="FFFFFF"); x.alignment = Alignment(wrap_text=True, vertical="top")
        x.fill = PatternFill("solid", fgColor="C55A11" if Hh[c-1].startswith("MUNIC") else ("7030A0" if Hh[c-1].startswith("Comparação") else "4472C4"))
    for d in data: s.append([d[h] for h in Hh])
    for i, hh in enumerate(Hh, 1): s.column_dimensions[get_column_letter(i)].width = 30 if hh.startswith(("Comparação", "MUNIC 2020 — isenções")) else 16
    s.freeze_panes = "C2"; s.auto_filter.ref = f"A1:{get_column_letter(len(Hh))}{len(data) + 1}"
sheet("Nossa base", [r for r in rows if r["Universo no nosso levantamento"].startswith(("em escopo", "mestre"))])
sheet("MUNIC declara TZ — fora", [r for r in rows if not r["Universo no nosso levantamento"].startswith(("em escopo", "mestre"))])
sheet("Divergências", [r for r in rows if "DIVERGE" in (r["Comparação — existência de TZ (2020)"] + r["Comparação — prestação"]) or "antecipa" in r["Comparação — existência de TZ (2020)"] or "fim antes" in r["Comparação — existência de TZ (2020)"]])
wb.save(OUT)
# colunas na mestre
ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S"); shutil.copy2(M, M.replace(".xlsx", f".BACKUP-{ts}-munic.xlsx"))
wb = openpyxl.load_workbook(M); s = wb["consolidado"]; h = [c.value for c in s[1]]
NEW = ["MUNIC 2020 (autodeclarado) — ônibus intramunicipal", "MUNIC 2020 (autodeclarado) — isenção 'toda a população'", "MUNIC 2020 (autodeclarado) — isenções", "MUNIC 2020 (autodeclarado) — regulamentação", "MUNIC 2017 (autodeclarado) — regulamentação", "MUNIC × levantamento — existência de TZ", "MUNIC × levantamento — prestação"]
for c in NEW:
    if c not in h: s.cell(1, len(h) + 1, c); h.append(c); x = s.cell(1, len(h)); x.font = Font(bold=True, color="FFFFFF"); x.fill = PatternFill("solid", fgColor="C55A11"); x.alignment = Alignment(wrap_text=True, vertical="top")
byc = {r["Código IBGE"]: r for r in rows}
for row in s.iter_rows(min_row=2):
    if not row[0].value: continue
    r = byc.get(str(row[h.index("Código IBGE")].value or "")[:6])
    if not r: continue
    vals = [r["MUNIC 2020 — ônibus intramunicipal"], r["MUNIC 2020 — isenção 'toda a população'"], r["MUNIC 2020 — isenções declaradas"], r["MUNIC 2020 — regulamentação"], r["MUNIC 2017 — regulamentação"], r["Comparação — existência de TZ (2020)"], r["Comparação — prestação"]]
    for c, v in zip(NEW, vals): s.cell(row[0].row, h.index(c) + 1, v or None)
wb.save(M)
print("linhas", len(rows)); print(cat_counts.most_common()); print(pre_counts.most_common())
