#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cruzar_operador_grupo.py — Frente 1 (25/09/2026): operador da Tarifa Zero × grupo econômico.

Para cada registro da base-mestre (Ativa, Encerrada, Pista):
  1. junta os CNPJs de operador já registrados (mestre: Operador, Operador — CNPJ, outras versões, Obs. legal,
     Lacuna contratual; Base integrada: aba Atos contratuais; log jurídico: bloco do município), descartando
     CNPJs de órgão público (texto vizinho com Município/Prefeitura/Fundo/Câmara/Secretaria);
  2. para operador nomeado sem CNPJ, procura o nome entre os estabelecimentos do recorte de 6 CNAEs de transporte
     no MESMO município (ponte SIAFI→IBGE); fora do município só aceita nome quase idêntico na mesma UF;
  3. para cada CNPJ básico, busca o componente societário (tabela mestre empresa×grupo×cluster, rede v4) e o
     rótulo de grupo da tabela mestre XLSX (12/08/2026, 327 grupos; coincide com a identificação v4 —
     o CSV de 04/08 com 165 grupos está superado, ver nota de 25/09/2026); e procura ligação INDIRETA por sócio PJ (o operador tem sócio PJ que
     está num grupo, ou é sócio de empresa de grupo) — o caso Terra Auto Viação/Rápido Sumaré.
NA ≠ 0: prestação direta → "sem operador privado" (dado); operador não apurado → "não apurado" (lacuna).
Casamento por nome é SUGESTÃO ("a conferir") até conferência em documento. Read-only sobre as fontes;
grava só as saídas abaixo. Com --gravar-mestre, escreve 4 colunas novas no fim da base-mestre (backup antes).
v2.1 (31/10/2026): "[A CONFIRMAR]" e "não confirmado" no início do campo Operador contam como operador não nomeado (F.8).
v2 (17/10/2026), opção --vigente: usa só o operador VIGENTE (campo "Operador — CNPJ" e "Operador" até a palavra "antes");
não lê atos contratuais nem o log, que hoje guardam contratos descartados, operadores anteriores e órgãos. Sem a opção, comportamento antigo.
Saídas: 03 - Dados/_data/CNPJ/Operador x grupo economico — cruzamento (AAAA-MM-DD).xlsx
"""
import os, re, sys, glob, shutil, datetime, unicodedata, collections
import pandas as pd
from rapidfuzz import fuzz

R = os.environ.get("TZ_VAULT") or os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
D = os.path.join(R, "03 - Dados", "_data")
CF = os.path.join(D, "CNPJ", "filtrados (6 CNAEs transporte, 24-07-2026)")
MES = os.path.join(D, "casos por fonte", "Municípios TZ - consolidado.xlsx")
BI = os.path.join(D, "casos por fonte", "Base integrada - casos TZ (23-09-2026).xlsx")
LOG = os.path.join(R, "04 - Análises", "Pesquisa legal", "Log de busca jurídica e contratual — municípios.md")
HOJE = datetime.date.today().isoformat()
OUT = os.path.join(D, "CNPJ", f"Operador x grupo economico — cruzamento ({HOJE}{', vigente' if '--vigente' in sys.argv else ''}).xlsx")

def n(s): return re.sub(r"\s+", " ", unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()).strip()
RE_CNPJ = re.compile(r"\b(\d{2})\.(\d{3})\.(\d{3})/(\d{4})-(\d{2})\b")
PUBLICO = re.compile(r"munic[ií]pio|prefeitura|fundo|c[aâ]mara|secretaria|[oó]rg[aã]o|fmas|autarquia municipal", re.I)
GENERICO = re.compile(r"^(estrutura municipal|frota pr[oó]pria|prefeitura|governo municipal|poder executivo|munic[ií]pio|secretaria|central de ve|empresa p[uú]blica|autarquia|ept\b|n[aã]o (apurado|identificad|localizad|nomead|informad|confirmad)|a apurar|\[a confirmar|—|-|privad|empresa privada|nan$)", re.I)
STOP = r"\b(ltda|me|epp|eireli|s ?a|s/a|cia|companhia|empresa|de|da|do|das|dos|e|transportes?|transporte|viacao|auto|onibus|turismo|servicos?|locacao|veiculos|passageiros|coletivos?|urbano|rodoviario|expresso|mei)\b"
def core(s): return re.sub(r"\s+", " ", re.sub(STOP, " ", re.sub(r"[^a-z0-9 ]", " ", n(s)))).strip()

def cnpjs_em(texto, ctx=70):
    out = []
    for m in RE_CNPJ.finditer(str(texto or "")):
        viz = str(texto)[max(0, m.start() - ctx):m.start()]
        if PUBLICO.search(viz.split(";")[-1].split("·")[-1]): continue
        out.append("".join(m.groups()))
    return out

VIGENTE = False
ANTES = re.compile(r"[;·,]?\s*\bantes\b[,:]?|\boutras vers", re.I)
def nomes_operador(s):
    s = str(s or "")
    if not s or GENERICO.search(s.strip()): return []
    partes = re.split(r"\s*(?:;|→|‖|\)\s+e\s+|\s\+\s)\s*", s)
    out = []
    for p in partes:
        p = re.split(r"\s+—\s+|\s+\(|,\s*CNPJ|\s+-\s+Contrato", p)[0].strip(" .;,")
        if len(core(p)) >= 3 and not GENERICO.search(p): out.append(p)
    return out

def main():
    grava = "--gravar-mestre" in sys.argv
    global VIGENTE; VIGENTE = "--vigente" in sys.argv
    m = pd.read_excel(MES, sheet_name="consolidado")
    m = m[m["Situação"].isin(["Ativa", "Encerrada", "Pista (a verificar)"])].copy()
    m["ibge7"] = pd.to_numeric(m["Código IBGE"], errors="coerce")
    # ponte 6→7 dígitos
    mun = pd.read_csv(os.path.join(D, "CNPJ", "Receita Federal - dados brutos", "municipios.csv"), dtype=str)
    mun["codigo_ibge"] = pd.to_numeric(mun["codigo_ibge"], errors="coerce")
    seis = {int(c) // 10: int(c) for c in mun["codigo_ibge"].dropna()}
    m["ibge7"] = m["ibge7"].map(lambda c: seis.get(int(c), c) if pd.notna(c) and c < 1_000_000 else c)
    siafi2ibge = dict(zip(pd.to_numeric(mun["siafi_id"], errors="coerce"), mun["codigo_ibge"]))

    # universo RFB (6 CNAEs)
    emp = pd.read_csv(os.path.join(CF, "empresas_filtrado_6cnaes.csv"), dtype=str, usecols=["cnpj_basico", "razao_social", "natureza_juridica"])
    razao = dict(zip(emp.cnpj_basico, emp.razao_social))
    natjur = dict(zip(emp.cnpj_basico, emp.natureza_juridica))
    def publica(b): return str(natjur.get(b, "")).startswith("1") or bool(re.search(r"municipal|prefeitura|autarquia|companhia de desenvolvimento", n(razao.get(b, ""))))
    est = pd.read_csv(os.path.join(CF, "estabelecimentos_filtrado_6cnaes.csv"), dtype=str,
                      usecols=["cnpj_basico", "nome_fantasia", "situacao_cadastral", "uf", "municipio_codigo_rfb", "camada"])
    est["ibge7"] = pd.to_numeric(est["municipio_codigo_rfb"], errors="coerce").map(siafi2ibge)
    est["razao"] = est.cnpj_basico.map(razao)
    # numeração canônica: a tabela mestre XLSX (12/08/2026, 327 grupos, renumerada por capital social) — idêntica à
    # identificação v4 onde esta existe. O CSV homônimo em _data/CNPJ é de 04/08 (165 grupos) e ficou superado.
    tm = pd.read_excel(os.path.join(R, "03 - Dados", "Tabela mestre - Empresas, Grupos e Clusters (ago-2026).xlsx"), sheet_name="Empresas", dtype=str)
    tm = tm.replace({"None": None, "nan": None})
    iv4 = pd.read_csv(os.path.join(CF, "identificacao_componentes_medios_grandes_v4.csv"), dtype=str)
    comp_id4 = iv4.set_index("componente_id")[["id_grupo", "nome_sugerido_unico", "confianca"]].to_dict("index")
    tmi = tm.set_index("cnpj_basico").to_dict("index")
    comp_nome = {}
    for r in tm.itertuples():
        if isinstance(r.nome_grupo, str): comp_nome.setdefault(r.componente_id_v4, r.nome_grupo)
    soc = pd.read_csv(os.path.join(CF, "socios_filtrado_6cnaes.csv"), dtype=str, usecols=["cnpj_basico", "tipo_socio", "nome_socio_ou_razao_social", "cnpj_cpf_socio"])
    spj = soc[soc.tipo_socio == "PJ"].copy(); spj["socio_basico"] = spj.cnpj_cpf_socio.str[:8]
    eh_cons = lambda b: str(natjur.get(b, "")) == "2151" or "consorcio" in n(razao.get(b, ""))
    spj["consorcio"] = spj.cnpj_basico.map(eh_cons)
    consorcios_de = spj[spj.consorcio].groupby("socio_basico")["cnpj_basico"].apply(set).to_dict()
    membros_de = spj[spj.consorcio].groupby("cnpj_basico")["socio_basico"].apply(set).to_dict()
    spj = spj[~spj.consorcio]  # consórcio não é vínculo de controle (método v3/v4)
    socios_de = spj.groupby("cnpj_basico")["socio_basico"].apply(set).to_dict()
    empresas_do_socio = spj.groupby("socio_basico")["cnpj_basico"].apply(set).to_dict()

    def grupo_de(b):
        r = tmi.get(b)
        if r is None: return None
        c = r.get("componente_id_v4")
        if not isinstance(c, str): return {"comp": "", "tm": "", "v4": "", "nome": ""}
        v = comp_id4.get(c, {})
        return {"comp": c, "tm": r.get("id_grupo") if isinstance(r.get("id_grupo"), str) else "",
                "v4": v.get("id_grupo", ""), "nome": v.get("nome_sugerido_unico") or (r.get("nome_grupo") if isinstance(r.get("nome_grupo"), str) else "") or comp_nome.get(c, "")}

    def rotulo(g):
        if not g or not g["comp"]: return ""
        ids = g["tm"] or g["v4"]
        return f"{g['nome'] or 'componente sem nome'} — componente {g['comp']}" + (f"; {ids}" if ids else "; componente pequeno, sem id de grupo")

    def parceria(b):
        out = []
        for c in consorcios_de.get(b, ()):
            for o in membros_de.get(c, ()) - {b}:
                g = grupo_de(o)
                if g and g["comp"]: out.append(f"consorciada com {razao.get(o, o)} ({o}; grupo {rotulo(g)}) em {razao.get(c, c)} ({c})")
        return out

    def indireta(b):
        achados = []
        for s in socios_de.get(b, ()):
            g = grupo_de(s)
            if g and g["comp"]: achados.append(f"tem como sócio PJ {razao.get(s, s)} ({s}), do grupo {rotulo(g)}")
        for e in empresas_do_socio.get(b, ()):
            g = grupo_de(e)
            if g and g["comp"]: achados.append(f"é sócio PJ de {razao.get(e, e)} ({e}), do grupo {rotulo(g)}")
        return achados

    # CNPJs da Base integrada (atos contratuais) e do log
    atos = pd.read_excel(BI, sheet_name="Atos contratuais", dtype=str)
    atos_c = collections.defaultdict(set)
    for r in atos.itertuples():
        for c in cnpjs_em(f"x {r.cnpj}"): atos_c[(n(r.municipio), str(r.uf).upper())].add(c[:8])
    log = open(LOG, encoding="utf-8").read()
    blocos = {}
    for mm in re.finditer(r"^#### (.+?) \(([A-Z]{2})\)\n(.*?)(?=^#### |\Z)", log, re.S | re.M):
        blocos[(n(mm.group(1)), mm.group(2))] = mm.group(3)

    linhas, ents = [], []
    for r in m.itertuples(index=False):
        d = r._asdict() if hasattr(r, "_asdict") else dict(zip(m.columns, r))
        row = dict(zip(m.columns, r))
        k = (n(row["Município"]), row["UF"])
        prest = str(row.get("Prestação (eixo 2)") or "")
        op = str(row.get("Operador") or "")
        if VIGENTE:   # v2 (17/10/2026): só o operador vigente — o texto depois de "antes" é trajetória, não operador atual
            op = ANTES.split(op)[0]
            fontes_txt = ANTES.split(str(row.get("Operador — CNPJ") or ""))[0]
            if re.match(r"\s*\[a confirmar", fontes_txt, re.I): fontes_txt = ""   # v2.1 (31/10/2026, F.8): CNPJ candidato não conta
        else:
            fontes_txt = " ".join(str(row.get(c) or "") for c in ("Operador — CNPJ", "Operador", "Operador — outras versões", "Obs. legal", "Lacuna contratual"))
        base = collections.OrderedDict()
        for c in cnpjs_em(fontes_txt): base.setdefault(c[:8], ("documento (base-mestre)", c))
        if not VIGENTE:
            for c in atos_c.get(k, ()): base.setdefault(c, ("documento (atos contratuais)", c))
            for c in cnpjs_em(blocos.get(k, "")): base.setdefault(c[:8], ("documento (log jurídico)", c))
        # nomes sem CNPJ
        sugestoes = []
        nomes = nomes_operador(op)
        cand_m = est[est.ibge7 == row["ibge7"]] if pd.notna(row["ibge7"]) else est.iloc[0:0]
        cand_uf = est[est.uf == row["UF"]]
        for nome in nomes:
            cn = core(nome)
            ja = any(fuzz.token_set_ratio(cn, core(razao.get(b, ""))) >= 85 for b in base)
            if ja: continue
            best = None
            for pool, lim, onde in ((cand_m, 85, "mesmo município"), (cand_uf, 95, "mesma UF, fora do município")):
                for e in pool.itertuples():
                    for alvo in (e.razao, e.nome_fantasia):
                        if not isinstance(alvo, str): continue
                        ca = core(alvo)
                        if not ca: continue
                        if len(cn.split()) >= 2 and len(ca.split()) >= 2: sc = fuzz.token_sort_ratio(cn, ca)
                        else: sc = 100 if cn == ca else (90 if (ca.startswith(cn + " ") and onde == "mesmo município") else 0)
                        if sc >= lim and (best is None or sc > best[0]): best = (sc, e.cnpj_basico, alvo, onde)
                if best: break
            if best: sugestoes.append((nome,) + best)
        # classifica
        diretos, indiretos, fora, parcerias, publicas, singletons = [], [], [], [], [], []
        for b, (orig, c) in base.items():
            g = grupo_de(b)
            ind = indireta(b); par = parceria(b)
            nomeb = razao.get(b, "(fora do recorte de 6 CNAEs)")
            if publica(b): publicas.append(nomeb)
            parcerias += [f"{nomeb}: {p}" for p in par]
            ents.append({"Município": row["Município"], "UF": row["UF"], "CNPJ": f"{c[:2]}.{c[2:5]}.{c[5:8]}/{c[8:12]}-{c[12:]}" if len(c) == 14 else b,
                         "Razão social (RFB)": nomeb, "Origem": orig, "Grupo (componente societário)": rotulo(g) if g else "",
                         "Ligação indireta (sócio PJ)": " ‖ ".join(ind), "Consórcio com empresa de grupo (não é controle)": " ‖ ".join(par), "Natureza pública": "sim" if publica(b) else "", "No recorte 6 CNAEs": "sim" if b in razao else "não"})
            if g and g["comp"] and str(g["comp"]).startswith("SINGLETON"): singletons.append(f"{nomeb}: empresa sem vínculo societário, promovida a grupo por capital ≥ R$ 5 mi ({g['tm'] or g['v4']})")
            elif g and g["comp"]: diretos.append(f"{nomeb}: {rotulo(g)}")
            elif ind: indiretos.append(f"{nomeb}: " + " ‖ ".join(ind))
            elif b not in razao: fora.append(nomeb if nomeb else b)
        for nome, sc, b, alvo, onde in sugestoes:
            g = grupo_de(b); ind = indireta(b)
            ents.append({"Município": row["Município"], "UF": row["UF"], "CNPJ": b + " (básico)", "Razão social (RFB)": razao.get(b, alvo),
                         "Origem": f"SUGESTÃO por nome — '{nome}' ≈ '{alvo}' (score {sc:.0f}, {onde}) — a conferir",
                         "Grupo (componente societário)": rotulo(g) if g else "", "Ligação indireta (sócio PJ)": " ‖ ".join(ind), "No recorte 6 CNAEs": "sim"})
        if re.search(r"direta|autarquia|empresa p[uú]blica", prest, re.I) and not base and not sugestoes and not nomes:
            situ = "sem operador privado (prestação direta)"
        elif not base and not sugestoes and re.search(r"^(prefeitura|governo municipal|poder executivo|munic)", op.strip(), re.I):
            situ = "sem operador privado (declarado pela fonte, a confirmar)"
        elif base and len(publicas) == len(base): situ = "operador público (empresa/autarquia municipal)"
        elif diretos: situ = "operador em grupo econômico (componente societário)"
        elif singletons: situ = "operador é empresa isolada de grande capital (singleton promovido a grupo)"
        elif indiretos: situ = "operador ligado a grupo por sócio PJ (a revisar)"
        elif base: situ = "operador identificado, isolado na rede (sem grupo)" if not fora or len(fora) < len(base) else "operador fora do recorte de 6 CNAEs (sem grupo mapeável)"
        elif sugestoes: situ = "sugestão por nome (a conferir)"
        elif nomes: situ = "operador nomeado, sem CNPJ e sem correspondência no recorte"
        else: situ = "não apurado"
        linhas.append({"Município": row["Município"], "UF": row["UF"], "Situação": row["Situação"], "Prestação (eixo 2)": prest[:120], "Operador (base-mestre)": op[:200],
                       "CNPJs citados como contratada/operador (documento)": "; ".join(f"{c[:2]}.{c[2:5]}.{c[5:8]}/{c[8:12]}-{c[12:]}" for b, (o, c) in base.items() if len(c) == 14),
                       "Resultado": situ, "Grupo — ligação direta": " ‖ ".join(diretos + singletons), "Grupo — ligação indireta (sócio PJ)": " ‖ ".join(indiretos), "Consórcio com empresa de grupo (não é controle)": " ‖ ".join(parcerias),
                       "Sugestões por nome (a conferir)": " ‖ ".join(f"'{a}' ≈ {razao.get(b, al)}" + (f" [casou com o nome fantasia '{al}']" if al != razao.get(b) else "") + f" ({b}; score {s:.0f}; {o})" for a, s, b, al, o in sugestoes),
                       "Grupo econômico (coluna antiga — presença no município)": str(row.get("Grupo econômico") or "")[:200]})
    L = pd.DataFrame(linhas); E = pd.DataFrame(ents)
    res = L["Resultado"].value_counts()
    leia = pd.DataFrame({"Leia-me": [
        f"Cruzamento operador × grupo econômico — gerado em {HOJE} por _meta/scripts/cruzar_operador_grupo.py (read-only sobre as fontes).",
        "Autor: Thiago Von Zeidler Gomes · Orientadora: Prof.ª Dra. Silvana Zioni",
        "Unidade: registro da base-mestre (Ativa, Encerrada, Pista). Grupo = componente societário da rede v4 (tabela mestre empresa×grupo×cluster, ago/2026).",
        "Numeração de grupo: tabela mestre XLSX (12/08/2026, 327 grupos), idêntica à identificação v4; o CSV de 04/08 (165 grupos) está superado.",
        "Consórcio (natureza 2151) NÃO é vínculo de controle (método v3/v4): parceria em consórcio com empresa de grupo aparece em coluna própria, sem mudar o resultado.",
        "'Sugestão por nome' não é achado: é candidato a conferir em contrato. Prestação direta = sem operador privado (dado, não lacuna).",
        "Base RFB: recorte de 6 CNAEs de transporte (maio/2024). Operador fora do recorte (ex.: construtora ou locadora) não tem grupo mapeável por este método.",
        ""] + [f"{k}: {v}" for k, v in res.items()]})
    with pd.ExcelWriter(OUT) as w:
        leia.to_excel(w, sheet_name="Leia-me", index=False); L.to_excel(w, sheet_name="Por caso", index=False); E.to_excel(w, sheet_name="Por CNPJ", index=False)
    print(res.to_string()); print("->", OUT)
    if grava:
        import openpyxl
        bk = os.path.join(R, "_meta", "_backups", f"cruzar-operador-grupo-{datetime.datetime.now():%Y%m%d-%H%M%S}"); os.makedirs(bk)
        shutil.copy2(MES, bk)
        wb = openpyxl.load_workbook(MES); ws = wb["consolidado"]; h = [c.value for c in ws[1]]
        novas = ["Operador × GE — resultado (cruzamento)", "Operador × GE — ligação", "Operador × GE — sugestão por nome (a conferir)", "Operador × GE — data"]
        for c in novas:
            if c not in h: ws.cell(row=1, column=len(h) + 1, value=c); h.append(c)
        idx = {(n(x["Município"]), x["UF"], x["Situação"]): x for x in linhas}
        for rr in ws.iter_rows(min_row=2):
            x = idx.get((n(rr[0].value), rr[1].value, rr[3].value))
            if not x: continue
            rr_vals = {novas[0]: x["Resultado"], novas[1]: " ‖ ".join(v for v in (x["Grupo — ligação direta"], x["Grupo — ligação indireta (sócio PJ)"], ("consórcio (não é controle): " + x["Consórcio com empresa de grupo (não é controle)"]) if x["Consórcio com empresa de grupo (não é controle)"] else "") if v)[:3000],
                       novas[2]: x["Sugestões por nome (a conferir)"][:3000], novas[3]: HOJE}
            for c, v in rr_vals.items(): ws.cell(row=rr[0].row, column=h.index(c) + 1, value=v)
        wb.save(MES); print("mestre gravada; backup", bk)

if __name__ == "__main__":
    main()
