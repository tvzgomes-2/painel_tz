# -*- coding: utf-8 -*-
r"""buscar_fila_autor_1106.py — busca automática das pendências da Fila do autor e dos [A CONFIRMAR] de 06/11/2026.

Autor: Thiago Von Zeidler Gomes · Orientadora: Prof.ª Dra. Silvana Zioni · script escrito com Claude (06/11/2026).

O que faz, para cada alvo (Palma/MG, Carmo/RJ, Palmas/PR, Jales/SP, Brodowski/SP, Lauro Müller/SC, Pederneiras/SP, Guararema/SP):
  1. Querido Diário (API pública): busca no texto dos diários oficiais as expressões do alvo, desde a data do alvo; guarda trecho e link.
  2. PNCP (API pública, só leitura; reaproveita o cache, o intervalo e a espera em 429 de buscar_operadores_pncp.py):
     a) contratações e contratos de transporte do município (mesma rotina das rodadas de operadores);
     b) para os contratos e compras já conhecidos: termos aditivos, itens, resultados e lista de arquivos;
     c) baixa os arquivos (PDF) desses contratos e compras para conferência.
Saídas (nada entra na base; tudo é pista até a leitura do documento e a decisão do autor):
  - "04 - Análises/Pesquisa legal/Fila do autor — busca automática (DD-MM-AAAA).csv" (uma linha por achado)
  - arquivos em "03 - Dados/_data/Legislacao e contratos TZ/_a triar/fila-autor-AAAA-MM-DD/<Município-UF>/"
Regras: respeita robots.txt, intervalo entre pedidos e espera em 429; não contorna bloqueio, captcha nem login; não grava CPF.
Uso (na máquina do autor, ambiente conda "tz-download"):
  conda activate tz-download
  python _meta/scripts/buscar_fila_autor_1106.py                 # todos os alvos
  python _meta/scripts/buscar_fila_autor_1106.py --so Jales       # um alvo (parte do nome)
  python _meta/scripts/buscar_fila_autor_1106.py --sem-qd         # só PNCP
  python _meta/scripts/buscar_fila_autor_1106.py --sem-pncp       # só Querido Diário
  python _meta/scripts/buscar_fila_autor_1106.py --sem-baixar     # não baixa arquivos
"""
import argparse, csv, datetime, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request, urllib.robotparser
AQUI = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, AQUI)
import buscar_operadores_pncp as B          # get_json com cache, robots e 429; UA; CTX; API; API_PNCP
RAIZ = B.RAIZ; HOJE = datetime.date.today()
SAIDA = os.path.join(RAIZ, "04 - Análises", "Pesquisa legal", f"Fila do autor — busca automática ({HOJE:%d-%m-%Y}).csv")
PASTA = os.path.join(RAIZ, "03 - Dados", "_data", "Legislacao e contratos TZ", "_a triar", f"fila-autor-{HOJE:%Y-%m-%d}")
MES = os.path.join(RAIZ, "03 - Dados", "_data", "casos por fonte", "Municípios TZ - consolidado.xlsx")

# ── alvos: pendência, termos do Querido Diário, desde, contratos (cnpj, ano, seq) e compras (cnpj, ano, seq) já conhecidos ──
ALVOS = [
 dict(mun="Palma", uf="MG", pend="ato que suspendeu a Tarifa Zero; PL 30/2026; Lei 1.853/2025", desde="2025-01-01",
      qd=['"tarifa zero"', '"transporte gratuito"', 'suspensão transporte', '"projeto de lei" 30/2026', '"1.853"', '"transporte coletivo"'],
      contratos=[], compras=[]),
 dict(mun="Carmo", uf="RJ", pend="resultado da sessão de 03/11/2026 (PP 0008/2026, Edital 0041/2026); contrato de 2024 a 2026; Anexo I do Contrato 0048/2023; razão social do CNPJ 28.542.511",
      desde="2023-01-01", qd=['Angramar', '"LR de Simoes"', '"LR de Simões"', '"0008/2026"', '"0041/2026"', '"transporte coletivo municipal"', '"0048/2023"'],
      contratos=[], compras=[]),
 dict(mun="Palmas", uf="PR", pend="Decreto 4.037/2022 (base do programa citada no 1º aditivo ao Contrato 101/2024)", desde="2022-01-01",
      qd=['"4.037"', '"4037/2022"', '"transporte coletivo municipal urbano gratuito"', '"3.046"'],
      contratos=[("76161181000108", 2024, 50), ("76161181000108", 2025, 258)], compras=[]),
 dict(mun="Jales", uf="SP", pend="valor do Contrato 73/2025: PNCP R$ 9.850.791 em 12 meses × base R$ 5.088.481,20/ano (Aditivo 02/2026)", desde="2025-01-01",
      qd=['"73/2025"', '"transporte coletivo"', '"5.088.481"', '"5,7037"', 'aditivo transporte coletivo'],
      contratos=[("45131885000104", 2025, 117)], compras=[]),
 dict(mun="Brodowski", uf="SP", pend="período das quantidades do Contrato 041/2026 (R$ 1.509.172,80; 127.896 km)", desde="2026-01-01",
      qd=['Gatran', '"041/2026"', '"001/2026" transporte', 'circular'],
      contratos=[], compras=[("45301652000102", 2026, 86)]),
 dict(mun="Lauro Müller", uf="SC", pend="destino da Concorrência 218/PMLM/2025 (permissão); Decreto 209/2025 (revogado)", desde="2025-06-01",
      qd=['"218/PMLM"', 'permissão transporte urbano', '"Decreto 209"', '"Leva e Traz"', '"transporte urbano gratuito"'],
      contratos=[], compras=[("82558909000124", 2025, 238), ("82558909000124", 2025, 218)]),
 dict(mun="Pederneiras", uf="SP", pend="'fornecimento de passes de circular' (Contrato 179/2025) num serviço gratuito", desde="2025-01-01",
      qd=['"passes de circular"', '"passe" circular', '"179/2025"', '"Futura Transportes"', '"tarifa zero"'],
      contratos=[("46189718000179", 2025, 183), ("46189718000179", 2025, 161)], compras=[("46189718000179", 2026, 301)]),
 dict(mun="Guararema", uf="SP", pend="parte urbana × escolar do custo do Contrato 32/2024 (estimada em 70% pelas medições de 2025)", desde="2025-01-01",
      qd=['"Alto Tietê" escolar', '"32/2024" apostilamento', 'medição transporte escolar', '"Guararema Sem Pagar"'],
      contratos=[("46523262000131", 2024, 55), ("46523262000131", 2024, 62)], compras=[]),
]

QD_HOSTS = ["https://api.queridodiario.ok.org.br/gazettes", "https://api.queridodiario.org.br/gazettes"]
CPF = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
def mascara(t): return CPF.sub("[CPF omitido]", re.sub(r"\s+", " ", str(t or ""))).strip()
def limpa_nome(t): return re.sub(r'[\\/:*?"<>|]+', "-", str(t or "")).strip()[:120]
def ibge7(c):
    c = str(int(float(c))) if c not in (None, "") else ""
    if len(c) == 7: return c
    if len(c) != 6: return ""
    s = sum(sum(int(x) for x in str(int(d) * p)) for d, p in zip(c, (1, 2, 1, 2, 1, 2)))
    return c + str((10 - s % 10) % 10)

def ler_ibge():
    try:
        import openpyxl
    except ModuleNotFoundError:
        sys.exit("Falta o pacote openpyxl neste ambiente:  pip install openpyxl")
    ws = openpyxl.load_workbook(MES, read_only=True)["consolidado"]; it = ws.iter_rows(values_only=True); h = next(it); ix = {k: i for i, k in enumerate(h)}
    return {(r[ix["Município"]], r[ix["UF"]]): ibge7(r[ix["Código IBGE"]]) for r in it if r[ix["Município"]]}

# ── Querido Diário ──
_rp = {}
def qd_get(params):
    for host in QD_HOSTS:
        h = urllib.parse.urlparse(host).netloc
        if h not in _rp:
            rp = urllib.robotparser.RobotFileParser()
            try:
                req = urllib.request.Request(f"https://{h}/robots.txt", headers={"User-Agent": B.UA})
                with urllib.request.urlopen(req, timeout=20, context=B.CTX) as r: rp.parse(r.read().decode("utf-8", "ignore").splitlines())
            except Exception: rp.parse([])
            _rp[h] = rp
        url = host + "?" + urllib.parse.urlencode(params, doseq=True)
        if not _rp[h].can_fetch(B.UA, url): print(f"      robots.txt proíbe {h}"); continue
        for tent in range(1, 5):
            time.sleep(1.5)
            try:
                req = urllib.request.Request(url, headers={"User-Agent": B.UA, "Accept": "application/json"})
                with urllib.request.urlopen(req, timeout=60, context=B.CTX) as r: return json.loads(r.read().decode("utf-8"))
            except urllib.error.HTTPError as e:
                if e.code == 429: print("      Querido Diário: HTTP 429, esperando 60 s"); time.sleep(60); continue
                if e.code >= 500: time.sleep(10 * tent); continue
                print(f"      Querido Diário: HTTP {e.code} em {h}"); break
            except Exception as e:
                print(f"      Querido Diário: falha em {h} ({str(e)[:80]})"); time.sleep(5 * tent)
    return None

def buscar_qd(alvo, ibge):
    out = []
    for termo in alvo["qd"]:
        d = qd_get({"territory_ids": ibge, "querystring": termo, "published_since": alvo["desde"], "excerpt_size": 400,
                    "number_of_excerpts": 3, "size": 20, "sort_by": "descending_date"})
        if d is None: out.append(dict(fonte="Querido Diário", tipo="erro de consulta", termo=termo)); continue
        gz = d.get("gazettes") or []
        print(f"   QD '{termo}': {d.get('total_gazettes', len(gz))} diários")
        if not gz: out.append(dict(fonte="Querido Diário", tipo="sem resultado (ou município sem cobertura)", termo=termo))
        for g in gz:
            out.append(dict(fonte="Querido Diário", tipo="diário oficial", termo=termo, data=g.get("date"), titulo=g.get("edition") or "",
                            trecho=mascara(" … ".join(g.get("excerpts") or []))[:1500], url=g.get("url") or g.get("txt_url") or ""))
    return out

# ── PNCP ──
def dados(d): return (d.get("data") or []) if isinstance(d, dict) else (d or [])
def baixar(url, destino):
    if os.path.exists(destino): return destino
    if not B.robots_ok(url): return "robots.txt proíbe"
    B.R.vez()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": B.UA})
        with urllib.request.urlopen(req, timeout=120, context=B.CTX) as r:
            corpo = r.read(); cd = r.headers.get("Content-Disposition") or ""
        m = re.search(r'filename="?([^";]+)', cd); ext = os.path.splitext(m.group(1))[1] if m else ".pdf"
        destino = os.path.splitext(destino)[0] + (ext or ".pdf")
        os.makedirs(os.path.dirname(destino), exist_ok=True); open(destino, "wb").write(corpo); return destino
    except Exception as e:
        return f"falha: {str(e)[:80]}"

def arquivos(base, alvo, rotulo, sem_baixar):
    out = []
    for a in dados(B.get_json(f"{base}/arquivos")):
        url = a.get("url") or a.get("uri") or ""
        tit = a.get("titulo") or a.get("tipoDocumentoNome") or "documento"
        dest = ""
        if url and not sem_baixar:
            dest = baixar(url, os.path.join(PASTA, limpa_nome(f"{alvo['mun']}-{alvo['uf']}"), limpa_nome(f"{rotulo} - doc {a.get('sequencialDocumento', '')} - {tit}") + ".pdf"))
        out.append(dict(fonte="PNCP", tipo=f"arquivo ({a.get('tipoDocumentoNome', '')})", titulo=f"{rotulo}: {tit}", data=(a.get("dataPublicacaoPncp") or "")[:10],
                        url=url, arquivo=os.path.relpath(dest, RAIZ) if dest and os.path.exists(dest) else dest))
    return out

def contrato(cnpj, ano, seq, alvo, sem_baixar):
    base = f"{B.API_PNCP}/orgaos/{cnpj}/contratos/{ano}/{seq}"; rot = f"contrato PNCP {ano}-{seq}"; out = []
    c = B.get_json(base) or {}
    if c:
        out.append(dict(fonte="PNCP", tipo="contrato", titulo=f"{rot}: nº {c.get('numeroContratoEmpenho')} · {c.get('nomeRazaoSocialFornecedor')} ({c.get('niFornecedor')})",
                        data=c.get("dataAssinatura"), trecho=mascara(f"{c.get('objetoContrato')} | vigência {c.get('dataVigenciaInicio')} a {c.get('dataVigenciaFim')} | "
                                                                     f"valor inicial {c.get('valorInicial')} · global {c.get('valorGlobal')} · parcelas {c.get('numeroParcelas')} de {c.get('valorParcela')}"),
                        url=f"https://pncp.gov.br/app/contratos/{cnpj}/{ano}/{seq}"))
    for t in dados(B.get_json(f"{base}/termos")):
        out.append(dict(fonte="PNCP", tipo=f"termo ({t.get('tipoTermoContratoNome') or t.get('tipoTermoContrato', '')})", titulo=f"{rot}: termo {t.get('numeroTermoContrato')}",
                        data=t.get("dataAssinatura"), trecho=mascara(f"{t.get('objetoTermoContrato') or ''} | vigência até {t.get('dataVigenciaFim')} | valor global {t.get('valorGlobal')} | "
                                                                     f"acréscimo {t.get('valorAcrescido')} | prazo aditado {t.get('prazoAditadoDias')} dias")[:1500],
                        url=f"https://pncp.gov.br/app/contratos/{cnpj}/{ano}/{seq}"))
        sq = t.get("sequencialTermoContrato")
        if sq: out += arquivos(f"{base}/termos/{sq}", alvo, f"{rot} termo {sq}", sem_baixar)
    return out + arquivos(base, alvo, rot, sem_baixar)

def compra(cnpj, ano, seq, alvo, sem_baixar):
    base = f"{B.API_PNCP}/orgaos/{cnpj}/compras/{ano}/{seq}"; rot = f"compra PNCP {ano}-{seq}"; out = []
    c = B.get_json(f"{B.API}/orgaos/{cnpj}/compras/{ano}/{seq}") or B.get_json(base) or {}   # 06/11/2026: o detalhe da compra mudou para a API de consulta (HTTP 301)
    if c:
        out.append(dict(fonte="PNCP", tipo=f"compra ({c.get('modalidadeNome')}; {c.get('situacaoCompraNome')})", titulo=f"{rot}: nº {c.get('numeroCompra')}",
                        data=(c.get("dataPublicacaoPncp") or "")[:10], trecho=mascara(f"{c.get('objetoCompra')} | estimado {c.get('valorTotalEstimado')} · homologado {c.get('valorTotalHomologado')}"),
                        url=f"https://pncp.gov.br/app/editais/{cnpj}/{ano}/{seq}"))
    for it in dados(B.get_json(f"{base}/itens?pagina=1&tamanhoPagina=50"))[:20]:
        res = dados(B.get_json(f"{base}/itens/{it.get('numeroItem')}/resultados"))
        txt = f"item {it.get('numeroItem')} ({it.get('situacaoCompraItemNome')}): {(it.get('descricao') or '')[:150]} | {it.get('quantidade')} {it.get('unidadeMedida')} a R$ {it.get('valorUnitarioEstimado')}"
        if not res: out.append(dict(fonte="PNCP", tipo="item sem resultado", titulo=rot, trecho=mascara(txt), url=f"https://pncp.gov.br/app/editais/{cnpj}/{ano}/{seq}"))
        for r in res:
            out.append(dict(fonte="PNCP", tipo="resultado", titulo=f"{rot}: {r.get('nomeRazaoSocialFornecedor')} ({r.get('niFornecedor')})", data=(r.get("dataResultado") or "")[:10],
                            trecho=mascara(f"{txt} | homologado {r.get('valorTotalHomologado')} ({r.get('situacaoCompraItemResultadoNome', '')})"), url=f"https://pncp.gov.br/app/editais/{cnpj}/{ano}/{seq}"))
    return out + arquivos(base, alvo, rot, sem_baixar)

def municipio_pncp(alvo, ibge):
    class A: desde = int(alvo["desde"][:4]); sem_resultados = False; completo = False
    m = {"municipio": alvo["mun"], "uf": alvo["uf"], "ibge": ibge, "grupo": "fila do autor", "orgaos_conhecidos": " ".join({c for c, _, _ in alvo["contratos"] + alvo["compras"]})}
    out = []
    for l in B.um_municipio(m, A):
        out.append(dict(fonte="PNCP", tipo=l.get("fonte"), titulo=f"{l.get('numero')}/{l.get('ano')} · {l.get('fornecedor') or ''} ({l.get('cnpj_fornecedor') or ''})",
                        data=l.get("vigencia_inicio") or "", trecho=mascara(f"{l.get('objeto')} | valor {l.get('valor_global')} | {l.get('tipo') or ''} | vigência {l.get('vigencia_inicio')} a {l.get('vigencia_fim')}"),
                        url=l.get("url"), outro_servico=l.get("marca_outro_servico", "")))
    return out

def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--so", help="só os alvos cujo nome contém este texto"); ap.add_argument("--sem-qd", action="store_true")
    ap.add_argument("--sem-pncp", action="store_true"); ap.add_argument("--sem-baixar", action="store_true")
    a = ap.parse_args()
    B.R = B.Rede(paralelo=2, offline=False, validade=7, espera_rede=10)
    ib = ler_ibge(); linhas = []
    for alvo in ALVOS:
        if a.so and B.sa(a.so) not in B.sa(alvo["mun"]): continue
        ibge = ib.get((alvo["mun"], alvo["uf"]), "")
        print(f"\n== {alvo['mun']}/{alvo['uf']} (IBGE {ibge or '?'}) — {alvo['pend']}", flush=True)
        achados = []
        try:
            if not a.sem_qd and ibge: achados += buscar_qd(alvo, ibge)
            if not a.sem_pncp:
                for c in alvo["contratos"]: achados += contrato(*c, alvo, a.sem_baixar)
                for c in alvo["compras"]: achados += compra(*c, alvo, a.sem_baixar)
                if ibge: achados += municipio_pncp(alvo, ibge)
        except B.SemRede:
            print("   sem internet: parei este alvo (rode de novo; o cache do PNCP guarda o que já veio)")
        for x in achados:
            linhas.append(dict(alvo=f"{alvo['mun']}/{alvo['uf']}", pendencia=alvo["pend"], **{k: x.get(k, "") for k in
                               ("fonte", "tipo", "termo", "data", "titulo", "trecho", "url", "arquivo", "outro_servico")}))
        print(f"   achados: {len(achados)}")
    os.makedirs(os.path.dirname(SAIDA), exist_ok=True)
    campos = ["alvo", "pendencia", "fonte", "tipo", "termo", "data", "titulo", "trecho", "url", "arquivo", "outro_servico"]
    with open(SAIDA, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos, delimiter=";"); w.writeheader(); w.writerows(linhas)
    if B.R.log:
        with open(SAIDA.replace(".csv", " — log de erros.csv"), "w", encoding="utf-8-sig", newline="") as f:
            csv.writer(f, delimiter=";").writerows([["url", "erro", "detalhe"]] + B.R.log)
    print(f"\n{len(linhas)} linhas → {SAIDA}\narquivos → {PASTA}\nPNCP: {B.R.stat}")
    B.R.pool.shutdown(wait=False)

if __name__ == "__main__":
    main()
