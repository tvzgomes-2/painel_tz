#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Controle unificado dos casos de Tarifa Zero — um Excel, uma linha por município.

Junta quatro fontes vivas que antes geravam planilhas que não se cruzavam:
  1. Base-mestre   03 - Dados/_data/casos por fonte/Municípios TZ - consolidado.xlsx (universo)
  2. Régua         03 - Dados/_data/casos por fonte/Tipologias TZ - consolidado.xlsx (aba, subtipo, portão)
  3. Log jurídico  04 - Análises/Pesquisa legal/Log de busca jurídica e contratual — municípios.md
  4. Leitura crítica 23/09/2026 _meta/scripts/_scratch/leitura_20260923/leitura_consolidada.json (classe ORIGINAL, congelada)
  + fila do e-SIC  04 - Análises/Pesquisa legal/e-SIC — pedidos de informação por município.md

A leitura crítica é um instantâneo de 23/09 (antes das frentes A e B); a coluna
"Situação unificada" combina a classe original com o que o log registrou depois.
Read-only sobre as fontes. Saída com nome estável (sobrescreve).
"""
import re, json, os, sys, unicodedata, datetime
from collections import Counter
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill
from openpyxl.utils import get_column_letter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from exportar_log_juridico_excel import parse_block, bucket, SRC as LOG

MESTRE = "03 - Dados/_data/casos por fonte/Municípios TZ - consolidado.xlsx"
REGUA = "03 - Dados/_data/casos por fonte/Tipologias TZ - consolidado.xlsx"
LEIT = "_meta/scripts/_scratch/leitura_20260923/leitura_consolidada.json"
ESIC = "04 - Análises/Pesquisa legal/e-SIC — pedidos de informação por município.md"
OUT = "04 - Análises/Pesquisa legal/Controle unificado dos casos — base, régua, log e leitura.xlsx"

def k(m, uf):
    s = unicodedata.normalize("NFKD", str(m)).encode("ascii", "ignore").decode().lower().strip()
    return (re.sub(r"\s+", " ", s), str(uf).strip().upper())

def load_mestre():
    ws = openpyxl.load_workbook(MESTRE, read_only=True)["consolidado"]
    rows = list(ws.iter_rows(values_only=True)); h = rows[0]; out = {}
    for r in rows[1:]:
        if not r[h.index("Município")]: continue
        d = dict(zip(h, r)); key = k(d["Município"], d["UF"])
        if key in out:  # município com duas políticas (ex.: Palmas/TO): agrega a situação
            prev = out[key]
            sits = [s for s in (prev["Situação"], d["Situação"]) if s]
            prev["Situação"] = " + ".join(dict.fromkeys(sits)); prev["_n_politicas"] = prev.get("_n_politicas", 1) + 1
        else:
            out[key] = d
    return out

def load_regua():
    wb = openpyxl.load_workbook(REGUA, read_only=True); out = {}
    for sh in wb.sheetnames:
        rows = list(wb[sh].iter_rows(values_only=True))
        if not rows: continue
        h = list(rows[0])
        if "Município" not in h or "UF" not in h: continue
        for r in rows[1:]:
            d = dict(zip(h, r))
            if not d.get("Município"): continue
            out.setdefault(k(d["Município"], d["UF"]), []).append((sh, d))
    return out

def load_log():
    c = open(LOG, encoding="utf-8").read()
    det = re.search(r"## Detalhe por município\n\n(.*)", c, re.S).group(1)
    out = {}
    for b in re.split(r"\n(?=#### )", det):
        if not b.strip().startswith("#### "): continue
        m, uf, data = parse_block(b)
        # última ação datada registrada no bloco (Frente B > Leitura > Propagação)
        acoes = re.findall(r"^- \*\*((?:Frente [AB]|Leitura|Propagação|Achado)[^*]*):\*\*\s*(.+)$", b, re.M)
        ult = (acoes[-1][0] + ": " + acoes[-1][1]) if acoes else ""
        data["_ultima"] = ult[:600]
        data["_bloco"] = b
        key = k(m, uf)
        if key in out:  # bloco duplicado (ex.: grafia com/sem acento): mantém o que não é marcado como DUPLICATA
            if "DUPLICATA" in data.get("Status", ""): out[key][2]["_dup"] = True; continue
            data["_dup"] = True
        out[key] = (m, uf, data)
    return out

LEIT2 = "_meta/scripts/_scratch/leitura_20260923/leitura_complementar_20261001.json"  # 01/10/2026: casos que entraram depois de 23/09

def load_leitura():
    out = {}
    if os.path.exists(LEIT): out.update({k(r["municipio"], r["uf"]): r for r in json.load(open(LEIT, encoding="utf-8"))})
    if os.path.exists(LEIT2):  # complementar: só preenche quem não tem leitura de 23/09 (a de 23/09 segue congelada)
        for r in json.load(open(LEIT2, encoding="utf-8")): out.setdefault(k(r["municipio"], r["uf"]), r)
    return out

def load_esic():
    out = {}; fase = 1
    for line in open(ESIC, encoding="utf-8"):
        if line.startswith("## Fase 2"): fase = 2
        elif line.startswith("## Fase 1"): fase = 1
        elif line.startswith("## ") and "Fase" not in line and out: fase = 0  # saiu das tabelas
        m = re.match(r"\| (\d+) \| ([^|]+?) \| ([A-Z]{2}) \| ([^|]*)\|", line)
        if m and fase: out[k(m.group(2), m.group(3))] = (int(m.group(1)), m.group(4).strip(), fase)
    return out

def fora_escopo(sit):
    return str(sit).startswith(("Excluída", "Reclassificada"))

def fora_contagem(sit):
    # balanço 26/09/2026: pistas (A.2) e 'Regulamentada — não implantada' (A.1.6) estão na base-mestre mas fora dos 179
    return str(sit).startswith(("Pista", "Regulamentada"))

FECHA_LEIT = {"OK", "OK c/ ressalva", "Reconciliar (ficha sabe, planilha não)"}

def situacao(mest, reg, log, lei, esic):
    flags = []
    sit_m = (mest or {}).get("Situação") or ""
    if not mest:
        return "Fora da base-mestre", "Decidir: incluir (varredura) ou manter fora (stub RSL / candidato)", flags
    if fora_escopo(sit_m):
        return f"{sit_m.split(' (')[0]} na base-mestre", "—", flags
    lb = bucket(log[2].get("Status", "")) if log else None
    cls = (lei or {}).get("classe", "")
    recente = bool(log and re.search(r"(2[3-9]|30)/09/2026|(2[3-9]|30)/09\)|\d{2}/1[0-2]/2026", log[2].get("Status", "") + log[2].get("_ultima", "") + log[2].get("Última atualização deste log", "")))
    if lb and lb.startswith("Fora do universo"):
        return "Fora do universo (parcial)", "Mover para 2 Parcial / retirar do panorama", flags
    if lb == "Resolvido":
        if cls in FECHA_LEIT or recente or not cls:
            return "Fechado", "—", flags
        flags.append(f"log Resolvido × leitura '{cls}'")
        return "Fechado no log — revisar", (lei or {}).get("busca_recomendada", ""), flags
    if esic and esic[2] == 1:
        return f"Aguarda e-SIC nº {esic[0]}", "Enviar pedido nº %d (modelo no arquivo do e-SIC)" % esic[0], flags
    if esic and esic[2] == 2:
        return "Varredura manual (antes do e-SIC)", "Varredura manual — roteiro nº %d no arquivo do e-SIC; se não fechar, sobe para e-SIC" % esic[0], flags
    if lb == "Verificar":
        return "Em verificação", (log[2].get("Próximo passo") or (lei or {}).get("busca_recomendada", "")), flags
    if cls:
        return "A fazer — " + cls, (lei or {}).get("busca_recomendada", ""), flags
    return "A fazer — sem leitura", (log[2].get("Próximo passo", "") if log else ""), flags

def main():
    mestre, regua, log, leit, esic = load_mestre(), load_regua(), load_log(), load_leitura(), load_esic()
    keys = set(mestre) | set(log) | set(leit)
    rows = []
    for key in keys:
        mest = mestre.get(key); lg = log.get(key); le = leit.get(key); es = esic.get(key)
        regs = regua.get(key, [])
        nome = (mest or {}).get("Município") or (lg[0] if lg else None) or le["municipio"]
        uf = (mest or {}).get("UF") or (lg[1] if lg else None) or le["uf"]
        sit, prox, flags = situacao(mest, regs, lg, le, es)
        sit_m = (mest or {}).get("Situação") or ""
        em_escopo = bool(mest) and not fora_escopo(sit_m) and not fora_contagem(sit_m)
        rni = any(s == "Regulamentada não implantada" for s, _ in regs)
        # linhas 2d do lote 'temporaria/0' = gratuidade eleitoral do levantamento IDEC + IPEA (autor, 23/09/2026):
        # são política distinta (2d) e coexistem com a da aba 1; falta só a referência na coluna Fonte
        elei = [(s, d) for s, d in regs if d.get("Modelo") == "temporaria" and str(d.get("Início/Ano")) == "0"]
        if elei and not any((d.get("Fonte") or "").strip() for _, d in elei): flags.append("2d eleitoral (IDEC+IPEA) sem referência na coluna Fonte")
        elei += [(s, d) for s, d in regs if s == "Eleitoral — piso e trajetória" and (s, d) not in elei]  # A.1.7 item 5 (06/10/2026): piso/trajetória, fora das camadas
        regs_sub = [x for x in regs if x not in elei]
        if rni:  # A.1.6: a linha 2d do episódio eleitoral coexiste com a aba própria (decisão do autor, 26/09/2026)
            regs_sub = [x for x in regs_sub if x[0] == "Regulamentada não implantada"]
        abas = "; ".join(sorted({s for s, _ in regs})) or "ausente"
        sub = "; ".join(str(d.get("Subtipo")) for _, d in regs_sub if d.get("Subtipo")) or ""
        por = " | ".join(str(d.get("Portão")) for _, d in regs if d.get("Portão")) or ""
        # divergências entre controles
        if em_escopo and not regs: flags.append("em escopo e ausente da régua")
        if not em_escopo and regs and mest and not fora_contagem(sit_m): flags.append(f"{sit_m} na mestre mas presente na régua ({abas})")
        if em_escopo and not lg: flags.append("em escopo e ausente do log")
        if em_escopo and not le: flags.append("em escopo e sem leitura crítica")
        if em_escopo and sit_m.startswith("Encerrada") and regs and "3 Encerradas" not in abas: flags.append("Encerrada na mestre, fora da aba 3")
        if em_escopo and sit_m == "Ativa" and abas == "3 Encerradas": flags.append("Ativa na mestre, na aba 3")
        if lg and lg[2].get("_dup"): flags.append("bloco duplicado no log")
        if len(regs_sub) > 1: flags.append(f"em {len(regs_sub)} linhas da régua (fora a 2d eleitoral)")
        if sub and not rni and lg and bucket(lg[2].get("Status", "")) != "Resolvido": flags.append("subtipo na régua sem log Resolvido")
        rows.append({
            "Município": nome, "UF": uf,
            "Universo": "em escopo" if em_escopo else (sit_m or "fora da base-mestre"),
            "Situação (mestre)": sit_m + (f" ({mest['_n_politicas']} políticas)" if mest and mest.get("_n_politicas") else ""), "Ano início (mestre)": (mest or {}).get("Ano início"),
            "Aba na régua": abas, "Subtipo (régua)": sub, "Portão (régua)": por[:400],
            "Situação unificada": sit,
            "Estado terminal (A.2e)": (mest or {}).get("Estado terminal (completude)") or "",
            "Status no log": lg[2].get("Status", "") if lg else "(ausente do log)",
            "Resumo do log": bucket(lg[2].get("Status", "")) if lg else "",
            "Classe da leitura 23/09 (original)": (le["classe"] + (f" [leitura complementar de {le['data_leitura']}]" if le.get("data_leitura") else "")) if le else "(sem leitura)",
            "Camada recomendada (leitura)": le["camada_recomendada"] if le else "",
            "e-SIC / varredura nº": (f"{es[0]} ({'e-SIC' if es[2] == 1 else 'varredura'})" if es else None),
            "Próximo passo": (prox or "")[:500],
            "Última ação registrada (log)": lg[2].get("_ultima", "") if lg else "",
            "Divergências entre controles": "; ".join(flags),
            "Confiança (log)": lg[2].get("Confiança real", "") if lg else "",
            "Confiab. (mestre)": (mest or {}).get("Confiab."),
            "Operador (mestre)": (mest or {}).get("Operador"),
        })
    ordem = lambda s: (0 if s.startswith("Fechado no log") else 1 if s.startswith("A fazer") else 2 if s.startswith("Varredura") else 3 if s.startswith("Aguarda") else 4 if s.startswith("Em verif") else 5 if s == "Fechado" else 6)
    rows.sort(key=lambda r: (r["Universo"] != "em escopo", ordem(r["Situação unificada"]), r["Município"]))
    H = list(rows[0].keys())

    wb = openpyxl.Workbook(); ws0 = wb.active; ws0.title = "Resumo"
    hoje = datetime.date.today().strftime("%d/%m/%Y")
    ws0["A1"] = "Controle unificado dos casos — base-mestre × régua × log jurídico × leitura crítica"; ws0["A1"].font = Font(bold=True, size=13)
    ws0["A2"] = f"Gerado em {hoje} por _meta/scripts/exportar_controle_unificado.py (read-only; regenerar em vez de editar)."
    esc = [r for r in rows if r["Universo"] == "em escopo"]
    r0 = 4
    def bloco(titulo, cont):
        nonlocal r0
        ws0.cell(row=r0, column=1, value=titulo).font = Font(bold=True); r0 += 1
        for a, b in cont:
            ws0.cell(row=r0, column=1, value=a); ws0.cell(row=r0, column=2, value=b); r0 += 1
        r0 += 1
    bloco("Universo", [("Linhas no total (união das fontes)", len(rows)), ("Em escopo na base-mestre", len(esc))] +
          sorted(Counter(r["Universo"] for r in rows if r["Universo"] != "em escopo").items()))
    bloco("Completude da base (A.2e) — em escopo", sorted(Counter((r["Estado terminal (A.2e)"] or "(sem estado)").split(";")[0] for r in esc).items()))  # 30/09/2026
    bloco("Situação unificada (em escopo)", sorted(Counter(re.sub(r" nº \d+", "", r["Situação unificada"]) for r in esc).items(), key=lambda x: -x[1]))
    bloco("Aba na régua (em escopo)", sorted(Counter(r["Aba na régua"] for r in esc).items(), key=lambda x: -x[1]))
    bloco("Casos com divergência entre controles (em escopo)", [("com pelo menos uma", sum(1 for r in esc if r["Divergências entre controles"]))] +
          sorted(Counter(f.split(" (")[0].split(" × ")[0] for r in esc for f in r["Divergências entre controles"].split("; ") if f).items(), key=lambda x: -x[1]))
    notas = [
        "Como ler:",
        "• 'Situação unificada' é a coluna de trabalho. Ordem da aba: Fechado no log — revisar → A fazer → Varredura manual (antes do e-SIC) → Aguarda e-SIC → Em verificação → Fechado.",
        "• 'Classe da leitura 23/09 (original)' é congelada (instantâneo antes das frentes A e B); o que mudou depois está em 'Status no log' e 'Última ação'.",
        "• 'Fechado' = log Resolvido e (leitura OK/Reconciliar ou atualização de 23/09). 'Fechado no log — revisar' = o log diz Resolvido mas a leitura achou problema e nada foi feito depois.",
        "• 'Divergências' lista onde base-mestre, régua, log e leitura não batem — é a lista de reconciliação.",
        "• Fonte da verdade continua sendo: universo = base-mestre; camada = régua (abas); evidência = log e notas de norma. Este Excel não é editado de volta.",
    ]
    for n in notas:
        ws0.cell(row=r0, column=1, value=n); r0 += 1
    ws0.column_dimensions["A"].width = 95; ws0.column_dimensions["B"].width = 12

    ws = wb.create_sheet("Controle"); ws.append(H)
    for c in range(1, len(H) + 1):
        cell = ws.cell(row=1, column=c); cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="4472C4"); cell.alignment = Alignment(vertical="top", wrap_text=True)
    fills = {"Fechado no": "F8CBAD", "A fazer": "FCE4E4", "Varredura": "EADCF8", "Aguarda": "DDEBF7", "Em verif": "FFF3CD", "Fechado": "E2F0D9"}
    sc = H.index("Situação unificada") + 1; dc = H.index("Divergências entre controles") + 1
    for i, r in enumerate(rows, start=2):
        ws.append([r[h] for h in H])
        for pref, col in fills.items():
            if r["Situação unificada"].startswith(pref):
                ws.cell(row=i, column=sc).fill = PatternFill("solid", fgColor=col); break
        if r["Divergências entre controles"]:
            ws.cell(row=i, column=dc).fill = PatternFill("solid", fgColor="F8CBAD")
        if r["Universo"] != "em escopo":
            for c in (1, 2, 3): ws.cell(row=i, column=c).font = Font(color="808080")
        for c in range(1, len(H) + 1):
            ws.cell(row=i, column=c).alignment = Alignment(vertical="top", wrap_text=True)
    W = {"Município": 22, "UF": 5, "Universo": 14, "Situação (mestre)": 12, "Ano início (mestre)": 9, "Aba na régua": 16,
         "Subtipo (régua)": 9, "Portão (régua)": 34, "Situação unificada": 26, "Estado terminal (A.2e)": 34, "Status no log": 40, "Resumo do log": 12,
         "Classe da leitura 23/09 (original)": 26, "Camada recomendada (leitura)": 12, "e-SIC / varredura nº": 12, "Próximo passo": 48,
         "Última ação registrada (log)": 60, "Divergências entre controles": 36, "Confiança (log)": 22, "Confiab. (mestre)": 18, "Operador (mestre)": 26}
    for i, h in enumerate(H, start=1): ws.column_dimensions[get_column_letter(i)].width = W.get(h, 18)
    ws.freeze_panes = "C2"; ws.auto_filter.ref = f"A1:{get_column_letter(len(H))}{len(rows) + 1}"
    wb.save(OUT)
    print("OK ->", OUT, "| linhas:", len(rows), "| em escopo:", len(esc))
    print(dict(Counter(re.sub(r" nº \d+", "", r["Situação unificada"]) for r in esc)))
    print("com divergência:", sum(1 for r in esc if r["Divergências entre controles"]))

if __name__ == "__main__":
    main()
