#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""buscar_outras_contratacoes_operador.py — busca dirigida das OUTRAS contratações do operador da Tarifa Zero com a mesma prefeitura
(transporte escolar, de pacientes, fretamento, locação para secretarias…). Agenda de pesquisa (decisão do autor, 05–06/11/2026).

Autor: Thiago Von Zeidler Gomes · Orientadora: Prof.ª Dra. Silvana Zioni · script escrito com Claude (06/11/2026).
Resultado = PISTA descritiva; não altera a base. A busca é pelo CNPJ básico (8 dígitos) do operador registrado na base-mestre.

FONTES
  tcesp  Casos de SP. Despesas municipais do TCE-SP (dados abertos, despesas-AAAA.zip): TODOS os pagamentos do município a credores com o
         CNPJ básico do operador, em qualquer função (não só transporte). Valor PAGO (tp_despesa = Pago); sem pagamento, o empenhado.
         Reaproveita o cache e a leitura de buscar_incumbentes_r74.py (ZIPs fora do OneDrive em %USERPROFILE%\tz_cache\tcesp; Deflate64
         pelo 7-Zip ou zipfile-deflate64). Padrão: 2023–2025 (já baixados); --anos 2019-2025 para ampliar.
  pncp   Casos fora de SP (e de SP com --pncp-sp). Contratos publicados no PNCP (2021 em diante) pelos órgãos municipais, filtrados pelo
         CNPJ básico do fornecedor = operador. Órgãos: os já vistos nas rodadas do PNCP do cofre e, se faltar, descobertos pelas
         contratações do município. Reaproveita o cache, o intervalo e a espera em 429 de buscar_operadores_pncp.py.
  resumo Junta as duas fontes por município: classes do objeto (transporte coletivo, educação/escolar, saúde, assistência social,
         fretamento/evento, locação, outro), valores e participação do que NÃO é a política.

SAÍDAS (03 - Dados/_data/Analises_Cap6/outras-contratacoes-operador/)
  alvos.csv · tcesp_pagamentos_operador.csv · pncp_contratos_operador.csv · Outras contratações do operador — resumo (AAAA-MM-DD).csv

LIMITES (escrever na tese): TCE-SP mede pagamento, PNCP mede contrato (valor contratado); PNCP só desde 2021 e só o que a prefeitura publicou;
  CNPJ do operador só onde a base o tem (casos de prestação direta ficam de fora); empresas do mesmo grupo com outro CNPJ básico não entram.
REGRAS: robots.txt, User-Agent honesto, intervalo e espera em 429; não contorna bloqueio; pessoa física (CPF) nunca é guardada.

USO (da raiz do cofre; ambiente conda "tz-download" ou Python com openpyxl)
  python _meta/scripts/buscar_outras_contratacoes_operador.py alvos
  python _meta/scripts/buscar_outras_contratacoes_operador.py tcesp [--anos 2023-2025] [--cache D:\tz_cache\tcesp] [--municipio Tambaú]
  python _meta/scripts/buscar_outras_contratacoes_operador.py pncp [--desde 2021] [--pncp-sp] [--municipio Piumhi]
  python _meta/scripts/buscar_outras_contratacoes_operador.py resumo
  python _meta/scripts/buscar_outras_contratacoes_operador.py tudo           # o mesmo que rodar sem argumento (duplo clique no .bat)
"""
import argparse, collections, csv, datetime, glob, os, re, sys, time
for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
AQUI = os.path.dirname(os.path.abspath(__file__)); RAIZ = os.path.dirname(os.path.dirname(AQUI))
sys.path.insert(0, AQUI); sys.path.insert(0, os.path.join(AQUI, "_scratch", "r74"))
csv.field_size_limit(10**8)
BM = os.path.join(RAIZ, "03 - Dados", "_data", "casos por fonte", "Municípios TZ - consolidado.xlsx")
PL = os.path.join(RAIZ, "04 - Análises", "Pesquisa legal")
OUT = os.path.join(RAIZ, "03 - Dados", "_data", "Analises_Cap6", "outras-contratacoes-operador")
HOJE = datetime.date.today()
CNPJ_RE = re.compile(r"(\d{2})\.?(\d{3})\.?(\d{3})/?(\d{4})-?(\d{2})")
ANTES = re.compile(r"\b(antes|anterior|antigo|até \d{4})\b", re.I)
CLASSES = [("eleitoral", r"elei[cç]|eleitor"),
           ("educação/escolar", r"escolar|aluno|estudant|universit|educa|ensino|creche|merenda"),
           ("saúde", r"saude|sa[uú]de|pacient|tfd|hemodi|caps\b|hospital|ambulat|oftalm"),
           ("assistência social", r"assistencia|cras\b|creas\b|idoso|social|scfv|conviv"),
           ("fretamento/evento", r"fretamento|evento|excurs|viage|turism|atleta|esport|delega|festa|lazer|cultura"),
           ("transporte coletivo (a política)", r"transporte (publico )?(coletivo|urbano)|coletivo (urbano|rural|municipal)|tarifa zero|passe livre|circular|concess|permiss|linhas? (urbana|municipa|rura)|transporte publico"),
           ("locação", r"loca[cç][aã]o"), ("manutenção/peças/combustível", r"manuten|pe[cç]as|pneu|combust|vistoria")]
def sa(s):
    import unicodedata; return unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
def classe(*txt):
    t = sa(" ".join(str(x or "") for x in txt))
    for c, rx in CLASSES:
        if re.search(rx, t): return c
    return "outro"
PUBLICO = re.compile(r"autarquia|empresa p[uú]blica|companhia municipal|prefeitura|servi[cç]o aut[oô]nomo|codesan|\bEPT\b|presta[cç][aã]o direta", re.I)
EMPRESA = re.compile(r"ltda|eireli|\bs\.?\s?/?a\b|\bepp\b|\bme\b|consorcio|cooperativa|associa|instituto|funda|empresa|transport|viac|turism|locador|servic|mobilidade|\bcia\b", re.I)
def credor(nome):
    """pessoa física ou empresário individual com nome de pessoa: nome omitido (regra do projeto)"""
    return nome if EMPRESA.search(sa(nome)) else "[nome de pessoa omitido]"
def classe_tce(fun, sub, hist):
    """TCE-SP: a função e a subfunção do gasto decidem antes do histórico (12/2026: 'convencionais e escolares' pago na função Transporte é a política)."""
    f, s_, h = sa(fun), sa(sub), sa(hist)
    if re.search(r"folha de pagamento|pavimenta|sarjet|constru[cç]|galeria|reforma|alambrado|cerca", h): return "não é transporte"
    if re.search(r"vales?[ -]?(de )?transportes?", h): return "compra de passes/vale-transporte"
    if "transporte" in s_ and "coletiv" in s_: return "transporte coletivo (a política)"
    if "educa" in f: return "educação/escolar"
    if re.search(r"\bpasses?\b", h): return "compra de passes/vale-transporte"
    if "saude" in f: return "saúde"
    if "assistencia" in f: return "assistência social"
    if f.startswith("transporte"): return "transporte coletivo (a política)"
    return classe(hist)
def num(x):
    try: return float(str(x).replace(".", "").replace(",", ".")) if "," in str(x) else float(x)
    except Exception: return 0.0
def escreve(nome, linhas, campos=None):
    os.makedirs(OUT, exist_ok=True); p = os.path.join(OUT, nome)
    campos = campos or (list(linhas[0]) if linhas else ["vazio"])
    with open(p, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=campos, delimiter=";", extrasaction="ignore"); w.writeheader(); w.writerows(linhas)
    print(f"  → {p} ({len(linhas)} linhas)"); return p
def ler(nome):
    p = os.path.join(OUT, nome)
    if not os.path.exists(p): return []
    with open(p, encoding="utf-8-sig", newline="") as f: return list(csv.DictReader(f, delimiter=";"))

# ───────────────────────── alvos: municípios com CNPJ de operador na base
def ibge7(c):
    c = str(int(float(c))) if c not in (None, "") else ""
    if len(c) != 6: return c
    s = sum(sum(int(x) for x in str(int(d) * p)) for d, p in zip(c, (1, 2, 1, 2, 1, 2))); return c + str((10 - s % 10) % 10)
def alvos():
    import openpyxl
    ws = openpyxl.load_workbook(BM, read_only=True)["consolidado"]; it = ws.iter_rows(values_only=True); h = next(it); ix = {k: i for i, k in enumerate(h)}
    out = []
    for r in it:
        if r[ix["Situação"]] not in ("Ativa", "Encerrada"): continue
        txt = str(r[ix["Operador — CNPJ"]] or ""); atuais, anteriores = [], []
        for m in CNPJ_RE.finditer(txt):
            cb = "".join(m.groups())[:8]; viz = txt[max(0, m.start() - 25):m.start()]
            (anteriores if ANTES.search(viz) else atuais).append(cb)
        if not atuais and not anteriores: continue
        op = str(r[ix["Operador"]] or "")
        out.append(dict(municipio=r[ix["Município"]], uf=r[ix["UF"]], ibge=ibge7(r[ix["Código IBGE"]]), operador=op[:120], publico="sim" if PUBLICO.search(op) else "",
                        cnpj_basico=" ".join(dict.fromkeys(atuais)), cnpj_basico_anterior=" ".join(dict.fromkeys(a for a in anteriores if a not in atuais))))
    return out

# ───────────────────────── TCE-SP
def rodar_tcesp(a):
    import buscar_incumbentes_r74 as T          # zip_do_ano, baixar_zip, abrir_despesas, csv_extraido, L (sa, num, mascara)
    al = [x for x in alvos() if x["uf"] == "SP" and not x["publico"]]
    if a.municipio: al = [x for x in al if sa(x["municipio"]) == sa(a.municipio)]
    roots = collections.defaultdict(set)
    for x in al:
        for cb in (x["cnpj_basico"] + " " + x["cnpj_basico_anterior"]).split(): roots[sa(x["municipio"])].add(cb)
    i, _, f = (a.anos or "2023-2025").partition("-"); anos = range(int(i), int(f or i) + 1)
    cache = a.cache or os.path.join(os.path.expanduser("~"), "tz_cache", "tcesp")
    print(f"TCE-SP: {len(al)} casos de SP com CNPJ · anos {list(anos)} · cache {cache}")
    out = []
    for y in anos:
        z = T.zip_do_ano(y, cache) or T.baixar_zip(y, cache)
        if not z and not T.csv_extraido(y, cache): print(f"    {y}: sem arquivo — pulado"); continue
        t0 = time.time(); n = 0; agg = collections.OrderedDict()
        fh, como = T.abrir_despesas(y, z, cache)
        with fh:
            cab = fh.readline().decode("latin-1").strip().lstrip("\ufeff"); H = {c.strip().strip('"').lower(): j for j, c in enumerate(cab.split(";"))}
            iM, iN, iV, iF, iS, iH = (H[c] for c in ["ds_municipio", "ds_despesa", "vl_despesa", "ds_funcao_governo", "ds_subfuncao_governo", "historico_despesa"])
            iT = H.get("tp_despesa"); iO = H.get("ds_orgao")
            novo = "tp_identificador_despesa" in H
            iTi, iNi = (H["tp_identificador_despesa"], H["nr_identificador_despesa"]) if novo else (H.get("identificador_despesa"), None)
            ncol = max(H.values()) + 1
            for raw in fh:
                n += 1
                p = raw.split(b";", iM + 1)
                if len(p) <= iM: continue
                mun = sa(p[iM].decode("latin-1").strip().strip('"'))
                if mun not in roots: continue
                r = [c.strip() for c in next(csv.reader([raw.decode("latin-1").rstrip("\r\n")], delimiter=";"))]
                if len(r) < ncol: continue
                if novo: tipo, ident = sa(r[iTi]), r[iNi]
                else: tipo, _, ident = r[iTi].rpartition(" - "); tipo = sa(tipo or r[iTi])
                if not ("cnpj" in tipo or "juridica" in tipo): continue
                dig = "".join(ch for ch in ident if ch.isdigit()).zfill(14)
                if dig[:8] not in roots[mun]: continue
                cl = classe_tce(r[iF], r[iS], r[iH])
                k = (r[iM], dig, r[iF], r[iS], cl)
                v = agg.get(k) or dict(municipio=r[iM], ano=y, credor_cnpj=dig, credor_nome=credor(r[iN][:120]), orgao=(r[iO][:80] if iO is not None else ""),
                                       funcao=r[iF][:60], subfuncao=r[iS][:60], classe=cl, valor_pago=0.0, valor_empenhado=0.0, n_empenhos=0, exemplo_historico="")
                x = T.L.num(r[iV]); fase = sa(r[iT]) if iT is not None else ""
                if "pago" in fase: v["valor_pago"] += x
                elif "empenh" in fase or not fase: v["valor_empenhado"] += x; v["n_empenhos"] += 1
                if not v["exemplo_historico"]: v["exemplo_historico"] = T.L.mascara(r[iH])[:300]
                agg[k] = v
        print(f"    {y}: {n:,} linhas em {time.time() - t0:.0f} s ({como}) · grupos guardados {len(agg)}")
        for v in agg.values():
            v["valor"] = f"{(v['valor_pago'] or v['valor_empenhado']):.2f}"; v["valor_pago"] = f"{v['valor_pago']:.2f}"; v["valor_empenhado"] = f"{v['valor_empenhado']:.2f}"; out.append(v)
    escreve("tcesp_pagamentos_operador.csv", out, ["municipio", "ano", "credor_cnpj", "credor_nome", "orgao", "funcao", "subfuncao", "classe",
                                                   "valor", "valor_pago", "valor_empenhado", "n_empenhos", "exemplo_historico"])

# ───────────────────────── PNCP
def orgaos_vistos():
    """órgãos municipais já vistos nas rodadas do PNCP do cofre: {(município normalizado, UF): {cnpj: razão social}}"""
    d = collections.defaultdict(dict)
    for f in glob.glob(os.path.join(PL, "Operadoras — *PNCP*.csv")) + glob.glob(os.path.join(PL, "PNCP — pendências*.csv")):
        with open(f, encoding="utf-8-sig") as fh:
            for r in csv.DictReader(fh, delimiter=";"):
                o = sa(r.get("orgao"))
                if r.get("orgao_cnpj") and ("municipio" in o or "prefeitura" in o or "fundo municipal" in o or "secretaria municipal" in o):
                    d[(sa(r["municipio"]), r["uf"])][r["orgao_cnpj"]] = r.get("orgao", "")
    return d
def rodar_pncp(a):
    import buscar_operadores_pncp as P
    P.R = P.Rede(paralelo=2, offline=False, validade=7, espera_rede=10)
    al = [x for x in alvos() if (a.pncp_sp or x["uf"] != "SP") and not x["publico"]]
    if a.municipio: al = [x for x in al if sa(x["municipio"]) == sa(a.municipio)]
    vistos = orgaos_vistos(); out = []
    print(f"PNCP: {len(al)} municípios · desde {a.desde}")
    try:
        for n, x in enumerate(al, 1):
            roots = set((x["cnpj_basico"] + " " + x["cnpj_basico_anterior"]).split())
            orgs = dict(vistos.get((sa(x["municipio"]), x["uf"]), {}))
            if not orgs and x["ibge"]:           # descobre os órgãos pelas contratações publicadas (qualquer objeto)
                for di, df in P.janelas(a.desde):
                    for mod in P.MODALIDADES:
                        for c in P.paginas(f"{P.API}/contratacoes/publicacao?dataInicial={di}&dataFinal={df}&codigoModalidadeContratacao={mod}&codigoMunicipioIbge={x['ibge']}", maximo=10):
                            o = c.get("orgaoEntidade") or {}
                            if o.get("cnpj") and P.municipal(o.get("razaoSocial", ""), True): orgs.setdefault(o["cnpj"], o.get("razaoSocial", ""))
            achou = 0
            for cnpj in orgs:
                for di, df in P.janelas(a.desde):
                    for c in P.paginas(f"{P.API}/contratos?dataInicial={di}&dataFinal={df}&cnpjOrgao={cnpj}"):
                        ni = re.sub(r"\D", "", str(c.get("niFornecedor") or ""))
                        if len(ni) != 14 or ni[:8] not in roots: continue        # só pessoa jurídica do operador
                        oe = c.get("orgaoEntidade") or {}; ano, seq = c.get("anoContrato"), c.get("sequencialContrato")
                        out.append(dict(municipio=x["municipio"], uf=x["uf"], orgao=oe.get("razaoSocial", orgs[cnpj]), orgao_cnpj=oe.get("cnpj", cnpj),
                                        fornecedor=credor(c.get("nomeRazaoSocialFornecedor") or ""), cnpj_fornecedor=ni, anterior="sim" if ni[:8] in x["cnpj_basico_anterior"].split() else "",
                                        numero=c.get("numeroContratoEmpenho"), ano=ano, sequencial=seq, tipo=(c.get("tipoContrato") or {}).get("nome"),
                                        objeto=(c.get("objetoContrato") or "")[:400].replace("\n", " "), classe=classe(c.get("objetoContrato"), oe.get("razaoSocial")),
                                        vigencia_inicio=c.get("dataVigenciaInicio"), vigencia_fim=c.get("dataVigenciaFim"), valor_global=c.get("valorGlobal"),
                                        url=f"https://pncp.gov.br/app/contratos/{oe.get('cnpj', cnpj)}/{ano}/{seq}"))
                        achou += 1
            print(f"  [{n}/{len(al)}] {x['municipio']}/{x['uf']}: {len(orgs)} órgãos · {achou} contratos do operador", flush=True)
    except P.SemRede:
        print("  sem internet: parei aqui (rode de novo; o cache guarda o que já veio)")
    vis = set(); uniq = []
    for r in out:
        k = (r["orgao_cnpj"], r["ano"], r["sequencial"])
        if k not in vis: vis.add(k); uniq.append(r)
    escreve("pncp_contratos_operador.csv", uniq, ["municipio", "uf", "orgao", "orgao_cnpj", "fornecedor", "cnpj_fornecedor", "anterior", "numero", "ano",
                                                  "sequencial", "tipo", "objeto", "classe", "vigencia_inicio", "vigencia_fim", "valor_global", "url"])
    P.R.pool.shutdown(wait=False)

# ───────────────────────── reclassificar (aplica classe_tce e omite nome de pessoa no CSV do TCE-SP já gerado, sem reler os ZIPs)
def rodar_reclassificar(a):
    R = ler("tcesp_pagamentos_operador.csv")
    if not R: print("  sem tcesp_pagamentos_operador.csv"); return
    pub = {(sa(x["municipio"]), "SP") for x in alvos() if x["publico"]}
    agg = collections.OrderedDict(); fora = 0
    for r in R:
        if (sa(r["municipio"]), "SP") in pub: fora += 1; continue
        r["classe"] = classe_tce(r["funcao"], r["subfuncao"], r["exemplo_historico"]); r["credor_nome"] = credor(r["credor_nome"])
        k = (r["municipio"], r["ano"], r["credor_cnpj"], r["funcao"], r["subfuncao"], r["classe"])
        if k in agg:
            for c in ("valor", "valor_pago", "valor_empenhado"): agg[k][c] = f"{num(agg[k][c]) + num(r[c]):.2f}"
            agg[k]["n_empenhos"] = str(int(agg[k]["n_empenhos"] or 0) + int(r["n_empenhos"] or 0))
        else: agg[k] = dict(r)
    escreve("tcesp_pagamentos_operador.csv", list(agg.values()), list(R[0].keys()))
    print(f"  reclassificado; linhas de operador público retiradas: {fora}")

# ───────────────────────── resumo
def rodar_resumo(a):
    al = {(sa(x["municipio"]), x["uf"]): x for x in alvos()}
    S = collections.defaultdict(lambda: collections.defaultdict(float)); N = collections.defaultdict(lambda: collections.defaultdict(int)); fonte = collections.defaultdict(set)
    for r in ler("tcesp_pagamentos_operador.csv"):
        k = (sa(r["municipio"]), "SP"); S[k][r["classe"]] += num(r["valor"]); N[k][r["classe"]] += 1; fonte[k].add("TCE-SP (pago)")
    for r in ler("pncp_contratos_operador.csv"):
        k = (sa(r["municipio"]), r["uf"]); S[k][r["classe"]] += num(r["valor_global"]); N[k][r["classe"]] += 1; fonte[k].add("PNCP (contratado)")
    cls = [c for c, _ in CLASSES] + ["outro", "não é transporte", "compra de passes/vale-transporte"]; out = []
    for k, x in sorted(al.items()):
        tot = sum(S[k].values()); pol = S[k].get("transporte coletivo (a política)", 0.0)
        outras = {c: S[k][c] for c in cls if c != "transporte coletivo (a política)" and S[k].get(c)}
        out.append(dict(municipio=x["municipio"], uf=x["uf"], operador=x["operador"], cnpj_basico=x["cnpj_basico"], fontes=" + ".join(sorted(fonte[k])) or "nenhum registro",
                        n_registros=sum(N[k].values()), valor_total=f"{tot:.2f}", valor_politica=f"{pol:.2f}", valor_outros=f"{tot - pol:.2f}",
                        pct_outros=(f"{100 * (tot - pol) / tot:.1f}" if tot else ""), outras_classes=" · ".join(f"{c} R$ {v:,.0f}" for c, v in sorted(outras.items(), key=lambda t: -t[1]))))
    escreve(f"Outras contratações do operador — resumo ({HOJE:%Y-%m-%d}).csv", out)
    com = [r for r in out if float(r["valor_outros"]) > 0]
    print(f"\n  municípios com CNPJ de operador: {len(out)} · com algum registro: {sum(1 for r in out if r['n_registros'])} · com contratação além da política: {len(com)}")
    print("  (TCE-SP soma pagamentos de 2023–2025 por padrão; PNCP soma valores contratados — não somar as duas colunas entre municípios de fontes diferentes)")

def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("passo", nargs="?", default="tudo", choices=["alvos", "tcesp", "reclassificar", "pncp", "resumo", "tudo"], help="padrão: tudo (alvos + tcesp + pncp + resumo)")
    ap.add_argument("--anos"); ap.add_argument("--cache"); ap.add_argument("--municipio")
    ap.add_argument("--desde", type=int, default=2021); ap.add_argument("--pncp-sp", action="store_true")
    a = ap.parse_args()
    if a.passo in ("alvos", "tudo"):
        al = alvos(); escreve("alvos.csv", al)
        print(f"  {len(al)} municípios com CNPJ de operador: SP {sum(1 for x in al if x['uf'] == 'SP')} · outras UFs {sum(1 for x in al if x['uf'] != 'SP')}")
    if a.passo in ("tcesp", "tudo"): rodar_tcesp(a)
    if a.passo in ("pncp", "tudo"): rodar_pncp(a)
    if a.passo == "reclassificar": rodar_reclassificar(a)
    if a.passo in ("resumo", "tudo", "reclassificar"): rodar_resumo(a)

if __name__ == "__main__":
    main()
