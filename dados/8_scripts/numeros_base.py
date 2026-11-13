#!/usr/bin/env python3
"""numeros_base.py — conta os números canônicos (universo, régua, completude, prova, norma, operador, perfil) a partir de uma
base-mestre e de uma régua. Usado por congelar_base.py; também roda sozinho para comparar a base viva com o congelamento vigente.
Autor: Thiago Von Zeidler Gomes · Orientadora: Prof.ª Dra. Silvana Zioni · escrito em 17/10/2026.
Uso (da raiz do cofre): python _meta/scripts/numeros_base.py [pasta-do-congelamento]   → imprime vivo × congelado.
Regras de agrupamento escritas aqui (reprodutíveis); a nota de 11/10/2026 agrupou a prestação à mão, e por isso pode diferir em 1 ou 2 casos."""
import os, re, sys, collections, openpyxl
R = os.getcwd()
VIVO = (os.path.join(R, "03 - Dados/_data/casos por fonte/Municípios TZ - consolidado.xlsx"), os.path.join(R, "03 - Dados/_data/casos por fonte/Tipologias TZ - consolidado.xlsx"))
CNPJ = re.compile(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}")
def ler(p, sh):
    ws = openpyxl.load_workbook(p, read_only=True)[sh]; rows = list(ws.iter_rows(values_only=True)); h = [str(x) for x in rows[0]]
    return [dict(zip(h, r)) for r in rows[1:] if r and r[0]]
def s(v): return "" if v is None else str(v).strip()
def prest(v):
    x = s(v).lower()
    # 22/10/2026: trajetória "A (anos) → B → C" — vale o último arranjo, lido fora dos parênteses (Tijucas do Sul era contada como direta)
    sem_par = re.sub(r"\([^()]*\)", "", x)
    if "→" in sem_par: x = sem_par.split("→")[-1].strip()
    if not x or x.startswith(("não encontrado", "não apurado", "a apurar")): return "não encontrada/não apurada"
    if x.startswith(("loca", "prestação direta com loca", "operação direta com veículo locado", "contratação de operador")): return "locação de veículos"
    if x.startswith(("prestação direta", "execução direta", "empresa pública", "autarquia", "operação municipal")): return "direta ou empresa pública"
    return "contrato com operador"
def opge(v):
    x = s(v).lower()
    if x.startswith("operador em grupo econômico"): return "em grupo econômico"
    if x.startswith("operador identificado, isolado"): return "isolado na rede"
    if x.startswith("sem operador privado"): return "sem operador privado"
    if not x or x.startswith("não apurado"): return "não apurado"
    if x.startswith("operador fora do recorte"): return "fora dos 6 CNAEs"
    return "outros"
def prova(v):
    x = s(v).lower()
    for k in ("atende", "a conferir", "não atende", "sem prova datada", "não se aplica"):
        if x.startswith(k): return k
    return "sem prova datada" if not x else "outro"
def norma(v):
    x = s(v).lower()
    if x.startswith("lida — arquivo"): return "lida com arquivo"
    if x.startswith("lida"): return "lida sem arquivo"
    if x.startswith("não existe"): return "não existe (política sem norma)"
    return "não localizada"
def estado(v):
    x = s(v)
    if x.startswith("Fechado — com norma"): return "Fechado — com norma"
    if x.startswith("Fechado — política sem norma"): return "Fechado — política sem norma"
    if x.startswith("Fechado — encerrada"): return "Fechado — encerrada"
    if x.startswith("Aguarda e-SIC — enviado"): return "Aguarda e-SIC — enviado"
    if x.startswith("Aguarda e-SIC — pronto"): return "Aguarda e-SIC — pronto para envio"
    if x.startswith("Lacuna declarada"): return "Lacuna declarada (fim da coleta)"  # 11/11/2026, decisão do autor
    return "Aberto/outro" if x else "vazio"
def faixa_pop(v):
    try: p = float(v)
    except Exception: return "NA"
    for lim, n in ((10e3, "< 10 mil"), (20e3, "10–20 mil"), (50e3, "20–50 mil"), (100e3, "50–100 mil"), (500e3, "100–500 mil")):
        if p < lim: return n
    return "≥ 500 mil"
def faixa_ano(v):
    m = re.search(r"(19|20)\d{2}", s(v))
    if not m: return "NA"
    a = int(m.group())
    return "≤ 2000" if a <= 2000 else "2001–2012" if a <= 2012 else "2013–2019" if a <= 2019 else "2020–2022" if a <= 2022 else str(a)
def contar(mestre, regua):
    M = ler(mestre, "consolidado"); C = collections.Counter
    esc = [d for d in M if d.get("Situação") in ("Ativa", "Encerrada")]; at = [d for d in esc if d["Situação"] == "Ativa"]
    N = {}
    N["linhas"] = len(M); N["situacao"] = C(s(d.get("Situação")) for d in M)
    N["escopo"] = len(esc); N["ativas"] = len(at); N["encerradas"] = len(esc) - len(at)
    N["aba_ativas"] = C(s(d.get("Régua — aba")) for d in at)
    N["fora"] = {k: sorted(f"{d['Município']}/{d['UF']}" for d in M if d.get("Situação") == k) for k in ("Regulamentada — não implantada", "Excluída (fora de escopo)", "Pista (a verificar)")}
    wb = openpyxl.load_workbook(regua, read_only=True); RG = {}
    for sh in wb.sheetnames:
        if sh == "RESUMO": continue
        RG[sh] = ler(regua, sh)
    N["regua"] = {k: len(v) for k, v in RG.items()}
    N["aba1"] = C((s(d.get("Subtipo")) or "sem subtipo") for d in RG.get("1 Universal", []))
    sub2 = C()
    for d in RG.get("2 Parcial", []):
        for t in re.findall(r"2[a-e]", s(d.get("Subtipo"))): sub2[t] += 1
    N["aba2_nao_exclusivo"] = sub2
    N["aba3"] = C((s(d.get("Subtipo (antes de encerrar)")) or "a decidir") for d in RG.get("3 Encerradas", []))
    N["estado"] = C(estado(d.get("Estado terminal (completude)")) for d in esc)
    N["prova"] = C(prova(d.get("Prova de operação — atualidade (2025/2026)")) for d in at)
    N["norma"] = C(norma(d.get("Norma lida (A.2e)")) for d in esc)
    N["cnpj"] = sum(1 for d in esc if CNPJ.search(s(d.get("Operador — CNPJ"))))
    N["prestacao"] = C(prest(d.get("Prestação (eixo 2)")) for d in esc)
    N["opge"] = C(opge(d.get("Operador × GE — resultado (cruzamento)")) for d in esc)
    N["contrap"] = C(s(d.get("Contrapartida — estado")) or "vazio" for d in esc if s(d.get("Régua — aba")) == "1 Universal")
    N["uf"] = C(s(d.get("UF")) for d in esc); N["pop"] = C(faixa_pop(d.get("População (2022)")) for d in esc)
    N["ano"] = C(faixa_ano(d.get("Ano início")) for d in esc)
    N["lev"] = C((lambda x: x if x in ("0", "1", "2", "3", "4") else ("NA" if not x or x == "None" else "5+"))(s(d.get("Fontes — nº de levantamentos (recontagem)"))) for d in esc)
    N["planmob"] = C(s(d.get("PlanMob — declarado")) or "NA" for d in esc)
    return N
def fmt(c, ordem=None):
    ks = ordem or [k for k, _ in c.most_common()]
    return " · ".join(f"{k} {c.get(k, 0)}" for k in ks if c.get(k, 0))
if __name__ == "__main__":
    fz = sys.argv[1] if len(sys.argv) > 1 else sorted(x for x in os.listdir(os.path.join(R, "03 - Dados/_data")) if x.startswith("congelamento-"))[-1]
    FZ = os.path.join(R, "03 - Dados/_data", fz)
    a = contar(*VIVO); b = contar(os.path.join(FZ, "Municípios TZ - consolidado.xlsx"), os.path.join(FZ, "Tipologias TZ - consolidado.xlsx"))
    for k in a:
        if a[k] != b[k]: print(f"{k}:\n  congelado ({fz}): {b[k]}\n  vivo: {a[k]}")
