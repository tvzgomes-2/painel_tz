# -*- coding: utf-8 -*-
r"""levantar_abertos_casos.py — normas e contratos ainda abertos nos 186 casos, por script (v1, 17/10/2026).

Autor: Thiago Von Zeidler Gomes · Orientadora: Prof.ª Dra. Silvana Zioni · script escrito com Claude.

Duas buscas, na sua máquina (o ambiente do Claude não alcança essas fontes), só leitura:
  1. QD — Querido Diário (API pública): para cada caso com norma ou contrato em aberto (lista alvos_casos_1017.csv, gerada da
     base-mestre de 11/10/2026 com alterações até 17/10), busca nos diários oficiais indexados: lei/decreto da gratuidade
     (se falta norma) e extrato/aditivo/contrato do transporte coletivo e o nome do operador (se falta contrato). Primeiro testa
     se o município tem diário no Querido Diário; se não tem, pula. Excertos com CPF mascarado.
  2. TCESP — despesas municipais do TCE-SP (despesas-AAAA.zip, Audesp): lê os arquivos anuais sem descompactar no disco e
     guarda só as despesas de transporte (função/subfunção de transporte, credor com CNPJ dos 6 CNAEs de transporte, CNPJ do
     operador da base, ou histórico com termos de transporte coletivo). Detalhe para os 64 casos de SP; agregado por município,
     ano e credor para os 645 municípios de SP (comparação). Pessoa física: só "PF", nunca o CPF.

Uso (Anaconda Prompt, ambiente tz-download):
  chcp 65001
  conda activate tz-download
  cd /d "%USERPROFILE%\OneDrive\doutorado"
  python _meta\scripts\levantar_abertos_casos.py                    # as duas buscas
  python _meta\scripts\levantar_abertos_casos.py --so-qd
  python _meta\scripts\levantar_abertos_casos.py --so-tcesp --anos 2019 2025
  python _meta\scripts\levantar_abertos_casos.py --so-tcesp --amostra   # só mostra o cabeçalho de um ano e para
  python _meta\scripts\levantar_abertos_casos.py --so-pncp            # 3. contratadas no PNCP numa rodada só: os 21 abertos do Pacote
                                                                     #    + os casos com contrato em aberto que nunca passaram pelo PNCP (desde 2021)
Retoma de onde parou (cache). Saídas em "04 - Análises/Pesquisa legal/" e "_a triar/".
Regras: respeita robots.txt; espera entre pedidos e em HTTP 429; não contorna bloqueio. Resultado é pista até conferência.
"""
import argparse, csv, glob, subprocess, datetime, hashlib, io, json, os, re, socket, ssl, sys, time, unicodedata, zipfile
import urllib.error, urllib.parse, urllib.request, urllib.robotparser
csv.field_size_limit(10**8)
CTX = None; SSL_FONTE = "padrão do Python"
try:
    import truststore; truststore.inject_into_ssl(); SSL_FONTE = "truststore"
except Exception:
    try:
        import certifi; CTX = ssl.create_default_context(cafile=certifi.where()); SSL_FONTE = "certifi"
    except Exception: pass
UA = "PesquisaTarifaZero-UFABC/1.0 (consulta a dados publicos para pesquisa academica)"
RAIZ = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
SC = os.path.join(RAIZ, "_meta", "scripts", "_scratch", "levantar-1017")
ALVOS = os.path.join(SC, "alvos_casos_1017.csv"); CNPJS = os.path.join(SC, "cnpj_basico_transporte.txt")
TRIAR = os.path.join(RAIZ, "03 - Dados", "_data", "Legislacao e contratos TZ", "_a triar")
PL = os.path.join(RAIZ, "04 - Análises", "Pesquisa legal")
HOJE = datetime.date.today()
sa = lambda s: unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower().strip()
CPF = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
def mascara(t): return CPF.sub("[CPF omitido]", " ".join(str(t or "").split()))
_robots = {}
def robots_ok(url):
    host = urllib.parse.urlparse(url).netloc
    if host not in _robots:
        rp = urllib.robotparser.RobotFileParser()
        try:
            with urllib.request.urlopen(urllib.request.Request(f"https://{host}/robots.txt", headers={"User-Agent": UA}), timeout=20, context=CTX) as r:
                rp.parse(r.read().decode("utf-8", "ignore").splitlines())
        except Exception: rp.parse([])
        _robots[host] = rp
    return _robots[host].can_fetch(UA, url)

def baixar(url, timeout=60, tentativas=5):
    """GET simples com espera em 429/5xx e queda de rede. Devolve bytes ou levanta."""
    for t in range(1, tentativas + 1):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=timeout, context=CTX) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 429: print("      HTTP 429: espero 60 s"); time.sleep(60); continue
            if e.code in (500, 502, 503, 504) and t < tentativas: time.sleep(10 * t); continue
            raise
        except (urllib.error.URLError, TimeoutError, ConnectionError, socket.timeout):
            if t == tentativas: raise
            print(f"      sem resposta; tento de novo em {15 * t} s"); time.sleep(15 * t)

# ---------------------------------------------------------------- 1. Querido Diário
QD = "https://api.queridodiario.org.br/gazettes"
T_NORMA = ['"tarifa zero"', '"transporte gratuito"', '"passe livre"', '"onibus circular" + gratuito', '"transporte coletivo" + gratuidade']
T_CONTR = ['"transporte coletivo" + extrato', '"transporte coletivo" + (aditivo | contrato | dispensa | pregao)', '"onibus circular" + (contrato | locacao)']
def qd_get(params, cache):
    k = os.path.join(cache, hashlib.sha1(json.dumps(params, sort_keys=True).encode()).hexdigest()[:16] + ".json")
    if os.path.exists(k):
        with open(k, encoding="utf-8") as f: return json.load(f)
    url = QD + "?" + urllib.parse.urlencode(params)
    if not robots_ok(url): return {"_erro": "robots.txt"}
    try: d = json.loads(baixar(url).decode("utf-8"))
    except urllib.error.HTTPError as e: d = {"_erro": f"HTTP {e.code}"}
    except Exception as e: d = {"_erro": str(e)[:120]}
    if "_erro" not in d:
        os.makedirs(cache, exist_ok=True)
        with open(k, "w", encoding="utf-8") as f: json.dump(d, f, ensure_ascii=False)
    time.sleep(1.0); return d

def rodar_qd(a):
    alvos = list(csv.DictReader(open(ALVOS, encoding="utf-8-sig"), delimiter=";"))
    alvos = [x for x in alvos if x["precisa_norma"] or x["precisa_contrato"]]
    if a.municipio: alvos = [x for x in alvos if sa(x["municipio"]) == sa(a.municipio)]
    cache = os.path.join(TRIAR, "qd-abertos-cache"); linhas, resumo = [], []
    print(f"\n=== Querido Diário: {len(alvos)} casos com norma ou contrato em aberto ===")
    t0 = time.time()
    for i, x in enumerate(alvos, 1):
        ib = str(x["cod_ibge"]).split(".")[0]
        ai = str(x["ano_inicio"])[:4]   # o campo pode trazer a data inteira (ex.: 2025-04-09)
        desde = f"{min(2019, int(ai) - 1) if ai.isdigit() else 2019}-01-01"
        cob = qd_get({"territory_ids": ib, "size": 1, "published_since": desde}, cache)
        tot = cob.get("total_gazettes", 0) if "_erro" not in cob else -1
        if tot <= 0:
            resumo.append(dict(municipio=x["municipio"], uf=x["uf"], cobertura_qd="sem diário no Querido Diário" if tot == 0 else cob.get("_erro"), achados=0))
            print(f"[{i}/{len(alvos)}] {x['municipio']}/{x['uf']}: sem cobertura ({'0 diários' if tot == 0 else cob.get('_erro')})"); continue
        termos = (T_NORMA if x["precisa_norma"] else []) + (T_CONTR if x["precisa_contrato"] else [])
        if x["operador_nome"]: termos.append(f'"{x["operador_nome"]}"')
        n = 0
        for q in termos:
            d = qd_get({"territory_ids": ib, "querystring": q, "published_since": desde, "size": 10, "excerpt_size": 400,
                        "number_of_excerpts": 2, "sort_by": "descending_date"}, cache)
            for g in (d.get("gazettes") or []):
                n += 1
                linhas.append(dict(municipio=x["municipio"], uf=x["uf"], cod_ibge=ib, falta="norma" if q in T_NORMA else ("operador" if q.startswith('"' + x["operador_nome"]) and x["operador_nome"] else "contrato"),
                                   busca=q, data=g.get("date", ""), edicao=g.get("edition", ""), extra=g.get("is_extra_edition", ""), url=g.get("url", ""), txt_url=g.get("txt_url", ""),
                                   excerto=" || ".join(mascara(e) for e in (g.get("excerpts") or []))[:900], total_na_busca=d.get("total_gazettes", "")))
        resumo.append(dict(municipio=x["municipio"], uf=x["uf"], cobertura_qd=f"{tot} diários desde {desde[:4]}", achados=n))
        print(f"[{i}/{len(alvos)}] {x['municipio']}/{x['uf']}: {tot} diários · {n} achados · {(time.time() - t0) / 60:.0f} min")
    vistos, uniq = {}, []
    for l in linhas:   # o mesmo diário achado por várias buscas vira uma linha, com as buscas e as faltas juntas
        k = (l["cod_ibge"], l["url"], l["excerto"][:120])
        if k in vistos:
            u = vistos[k]
            if l["busca"] not in u["busca"]: u["busca"] += " | " + l["busca"]
            if l["falta"] not in u["falta"]: u["falta"] += " + " + l["falta"]
        else: vistos[k] = l; uniq.append(l)
    p1 = os.path.join(PL, f"Querido Diário — normas e contratos abertos dos casos ({HOJE:%d-%m-%Y}).csv")
    p2 = os.path.join(PL, f"Querido Diário — cobertura dos casos abertos ({HOJE:%d-%m-%Y}).csv")
    for p, rows in ((p1, uniq), (p2, resumo)):
        if rows:
            with open(p, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter=";"); w.writeheader(); w.writerows(rows)
    print(f"\nQuerido Diário: {len(uniq)} achados em {sum(1 for r in resumo if r['achados'])} municípios; "
          f"{sum(1 for r in resumo if 'sem' in str(r['cobertura_qd']))} sem cobertura.\n  {p1}\n  {p2}")

# ---------------------------------------------------------------- 2. TCE-SP
TCE = "https://transparencia.tce.sp.gov.br/sites/default/files/conjunto-dados/despesas-{ano}.zip"
HIST = re.compile(r"transporte (publico |urbano |municipal )?coletivo|onibus circular|circular (urbano|gratuit|municipal)|tarifa zero|passe livre|transporte gratuito|"
                  r"linhas? (urbana|municipal)|onibus urbano|transporte de passageiros|locacao de onibus|fretamento|por (km|quilometro)|quilometro rodado|subsidio")
def achar(cols, *cands, evita=()):
    for c in cands:
        for i, n in enumerate(cols):
            if c in n and not any(e in n for e in evita): return i
    return None
def num(v):
    v = str(v or "").strip()
    if not v: return 0.0
    if "," in v: v = v.replace(".", "").replace(",", ".")
    try: return float(v)
    except ValueError: return 0.0

def rodar_tcesp(a):
    alvos = [x for x in csv.DictReader(open(ALVOS, encoding="utf-8-sig"), delimiter=";") if x["uf"] == "SP"]
    casos = {sa(x["municipio"]): x for x in alvos}
    op_cnpj = {c[:8]: x["municipio"] for x in alvos for c in x["operador_cnpjs"].split()}
    print(f"\n=== TCE-SP: {len(casos)} casos de SP · lendo o conjunto de CNPJ de transporte ...", flush=True)
    transp = set(open(CNPJS).read().split())
    cache = os.path.join(TRIAR, "tcesp-despesas-cache"); os.makedirs(cache, exist_ok=True)
    det_p = os.path.join(TRIAR, f"tcesp-despesas-transporte-casos ({HOJE:%d-%m-%Y}).csv")
    agg = {}; det_f = None; det_w = None
    for ano in range(a.anos[0], a.anos[1] + 1):
        url = TCE.format(ano=ano); zp = os.path.join(cache, f"despesas-{ano}.zip")
        if not os.path.exists(zp):
            if not robots_ok(url): print(f"  {ano}: robots.txt proíbe; baixar à mão: {url}"); continue
            print(f"  {ano}: baixando {url} ...", flush=True); t = time.time()
            try:
                tmp = zp + ".parcial"
                with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=120, context=CTX) as r, open(tmp, "wb") as f:
                    while True:
                        b = r.read(1 << 20)
                        if not b: break
                        f.write(b)
                os.replace(tmp, zp); print(f"     {os.path.getsize(zp) / 1e6:.0f} MB em {time.time() - t:.0f} s")
            except Exception as e:
                print(f"     falhou ({str(e)[:120]}); rode de novo depois"); continue
        with zipfile.ZipFile(zp) as z:
            membros = [m for m in z.namelist() if m.lower().endswith((".csv", ".txt"))]
            for m in membros:
                raw = z.open(m); amostra = raw.read(200000); raw.close()
                enc = "utf-8-sig"
                try: amostra.decode("utf-8")
                except UnicodeDecodeError: enc = "latin-1"
                txt = amostra.decode(enc, "ignore"); delim = ";" if txt.count(";") > txt.count(",") else ","
                fh = io.TextIOWrapper(z.open(m), encoding=enc, errors="replace", newline="")
                rd = csv.reader(fh, delimiter=delim); cab = next(rd); cols = [sa(c) for c in cab]
                M = dict(mun=achar(cols, "municipio"), forn_id=achar(cols, "nr_identificador", "cnpj", "cpf_cnpj", "documento", evita=("tp_",)), forn_tipo=achar(cols, "tp_identificador"),
                         forn_nome=achar(cols, "ds_despesa", "fornecedor", "credor", "favorecido", evita=("identificador", "cnpj")),
                         valor=achar(cols, "vl_despesa", "valor", "vl_"), evento=achar(cols, "tp_despesa", "evento", "tipo"),
                         funcao=achar(cols, "funcao", evita=("subfuncao",)), subfuncao=achar(cols, "subfuncao"), hist=achar(cols, "historico"),
                         data=achar(cols, "dt_emissao", "data"), elemento=achar(cols, "elemento"), empenho=achar(cols, "nr_empenho", "empenho"),
                         orgao=achar(cols, "ds_orgao", "orgao"), mes=achar(cols, "mes_referencia", "mes"))
                print(f"  {ano} · {m}: {enc}, '{delim}', {len(cab)} colunas\n     cabeçalho: {cab}\n     mapa: { {k: (cab[v] if v is not None else None) for k, v in M.items()} }", flush=True)
                if a.amostra:
                    for _ in range(3): print("     ", next(rd))
                    print("\nModo --amostra: mande este cabeçalho no chat se o mapa estiver errado."); return
                if M["mun"] is None or M["valor"] is None:
                    print("     não achei as colunas de município ou valor: mande o cabeçalho no chat; pulo este arquivo."); continue
                g = lambda r, k: (r[M[k]] if M[k] is not None and M[k] < len(r) else "")
                n = keep = 0; t = time.time()
                for r in rd:
                    n += 1
                    if n % 2000000 == 0: print(f"     {n / 1e6:.0f} mi linhas, {keep} de transporte, {time.time() - t:.0f} s", flush=True)
                    fid = g(r, "forn_id"); dig = re.sub(r"\D", "", fid); tipo = sa(g(r, "forn_tipo"))
                    pj = ("cnpj" in tipo or "juridica" in tipo) if tipo else len(dig) >= 14
                    if pj: dig = dig.zfill(14)
                    cb = dig[-14:][:8] if pj else ""
                    fun, sub, hist = sa(g(r, "funcao")), sa(g(r, "subfuncao")), sa(g(r, "hist"))
                    motivo = ("operador da base" if cb in op_cnpj else "") or ("subfunção transporte coletivo" if "transportes coletivos" in sub or "transporte coletivo" in sub else "") or \
                             ("função transporte" if "transporte" in fun else "") or ("CNPJ de transporte (6 CNAEs)" if cb in transp else "") or \
                             ("histórico" if HIST.search(hist) else "")
                    if not motivo: continue
                    keep += 1; mun = g(r, "mun"); smun = sa(mun); v = num(g(r, "valor"))
                    cred = (dig[-14:] if pj else "PF"); nome = g(r, "forn_nome") if pj else "pessoa física"
                    kk = (mun, ano, cred, nome[:80], g(r, "funcao")[:60], g(r, "subfuncao")[:60], g(r, "evento")[:30])
                    s = agg.setdefault(kk, [0.0, 0, motivo]); s[0] += v; s[1] += 1
                    if smun in casos:
                        if det_w is None:
                            det_f = open(det_p, "w", newline="", encoding="utf-8-sig"); det_w = csv.writer(det_f, delimiter=";")
                            det_w.writerow(["municipio", "ano", "mes", "orgao", "evento", "empenho", "data", "credor_cnpj", "credor_nome", "funcao", "subfuncao", "elemento", "valor", "motivo", "historico"])
                        det_w.writerow([mun, ano, g(r, "mes"), g(r, "orgao")[:80], g(r, "evento"), g(r, "empenho"), g(r, "data"), cred, nome[:120], g(r, "funcao"), g(r, "subfuncao"),
                                        g(r, "elemento")[:80], f"{v:.2f}", motivo, mascara(g(r, "hist"))[:500]])
                print(f"     {ano}: {n:,} linhas lidas, {keep:,} de transporte, {time.time() - t:.0f} s", flush=True)
    if det_f: det_f.close()
    ag_p = os.path.join(PL, f"TCE-SP — despesas de transporte por município, ano e credor ({HOJE:%d-%m-%Y}).csv")
    with open(ag_p, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";"); w.writerow(["municipio", "caso_tz", "ano", "credor_cnpj", "credor_nome", "operador_da_base", "funcao", "subfuncao", "evento", "valor_total", "n_lancamentos", "motivo"])
        for (mun, ano, cred, nome, fun, sub, ev), (v, k, mot) in sorted(agg.items()):
            w.writerow([mun, "sim" if sa(mun) in casos else "", ano, cred, nome, op_cnpj.get(cred[:8], ""), fun, sub, ev, f"{v:.2f}", k, mot])
    print(f"\nTCE-SP: {len(agg):,} linhas agregadas → {ag_p}\n  detalhe dos casos → {det_p if det_w else '(nenhum)'}")

# ---------------------------------------------------------------- 3. PNCP (21 abertos do Pacote + 83 lacunas de contrato, numa rodada só)
def rodar_pncp(a):
    l1 = os.path.join(RAIZ, "_meta", "scripts", "_scratch", "operadores-1014", "lista_pncp_abertos_1017.csv")
    l2 = os.path.join(SC, "lista_pncp_lacunas_1017.csv"); lista = os.path.join(SC, "lista_pncp_fundida_1017.csv")
    vistos, linhas, campos = set(), [], None
    for p in (l1, l2):
        with open(p, encoding="utf-8-sig") as f:
            rd = csv.DictReader(f, delimiter=";"); campos = campos or rd.fieldnames
            for r in rd:
                k = (sa(r["municipio"]), r["uf"])
                if k not in vistos: vistos.add(k); linhas.append(r)
    with open(lista, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=campos, delimiter=";", extrasaction="ignore"); w.writeheader(); w.writerows(linhas)
    padrao = os.path.join(PL, f"Operadoras — resultados do PNCP ({HOJE:%d-%m-%Y}).csv")
    alvo = os.path.join(PL, f"Operadoras — resultados do PNCP, abertos e lacunas ({HOJE:%d-%m-%Y}).csv")
    if os.path.exists(padrao):   # parcial de uma rodada interrompida: guardado, não apagado (o cache já tem o que veio)
        os.replace(padrao, padrao.replace(").csv", f", parcial guardado {time.strftime('%H%M%S')}).csv"))
    print(f"\n=== PNCP: {len(linhas)} municípios (21 abertos do Pacote + lacunas de contrato), desde {a.desde_pncp} ===", flush=True)
    r = subprocess.call([sys.executable, os.path.join(RAIZ, "_meta", "scripts", "buscar_operadores_pncp.py"), "--lista", lista,
                         "--desde", str(a.desde_pncp), "--validade", "0", "--paralelo", "4"] + (["--de", str(a.de)] if a.de > 1 else []), cwd=RAIZ)
    if os.path.exists(padrao): os.replace(padrao, alvo); print(f"  → {alvo}")
    if os.path.exists(alvo):
        sys.path.insert(0, os.path.join(RAIZ, "_meta", "scripts")); import buscar_abertos_pacote as bap
        bap.novidades(alvo, "abertos e lacunas")
    else:
        print("A busca parou antes de gravar; rode de novo o mesmo comando (o cache guarda o que veio; --de N retoma do N-ésimo).")

def main():
    ap = argparse.ArgumentParser(description="Normas e contratos abertos dos casos: Querido Diário e despesas do TCE-SP.")
    ap.add_argument("--so-qd", action="store_true"); ap.add_argument("--so-tcesp", action="store_true"); ap.add_argument("--so-pncp", action="store_true")
    ap.add_argument("--desde-pncp", type=int, default=2021); ap.add_argument("--de", type=int, default=1, help="PNCP: retoma do N-ésimo município")
    ap.add_argument("--anos", nargs=2, type=int, default=[2019, 2025], metavar=("DE", "ATE"))
    ap.add_argument("--amostra", action="store_true", help="TCE-SP: mostra o cabeçalho do primeiro arquivo e para")
    ap.add_argument("--municipio", help="QD: só este município (teste)")
    a = ap.parse_args()
    for p in (ALVOS, CNPJS): assert os.path.isfile(p), f"não achei {p}"
    print(f"Cofre: {RAIZ} · SSL: {SSL_FONTE} · Python {sys.version.split()[0]}")
    if a.so_pncp: rodar_pncp(a)
    else:
        if not a.so_tcesp: rodar_qd(a)
        if not a.so_qd: rodar_tcesp(a)
    print("\nPronto. Avise no chat: eu leio as saídas, confiro na fonte e registro o que mudar.")

if __name__ == "__main__":
    main()
