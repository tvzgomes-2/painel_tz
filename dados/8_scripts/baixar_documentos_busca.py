#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
Baixa os documentos da fila de busca de contratos (frente CNPJ, rodadas 1 a 3) para triagem.

Autor: Thiago Von Zeidler Gomes
Orientadora: Prof.ª Dra. Silvana Zioni
Script criado em 12/10/2026 (Claude, a pedido do autor).

O QUE FAZ
- Lê a fila: 04 - Análises/Pesquisa legal/Busca de contratos — fila de download (12-10-2026).csv
- Modo "pncp": usa a API pública do PNCP para listar e baixar os arquivos do contrato ou da compra,
  incluindo os termos aditivos dos contratos, e salva os metadados em JSON.
- Modo "direto": baixa a URL; se vier uma página HTML, salva o HTML. Com --seguir-links, segue também até
  5 links de PDF/download do mesmo site (desligado por padrão: em páginas de listagem pega anexos sem relação).
- Modo "manual": não baixa. Lista no log e, com --abrir-manuais, abre no navegador para baixar à mão.
- Tudo vai para 03 - Dados/_data/Legislacao e contratos TZ/_a triar/download-AAAA-MM-DD/<UF>/ e é
  registrado em _log_download.csv na mesma pasta. A triagem para normas/, contratos/ ou capturas/ é
  feita depois, com o nome no padrão do cofre.

REGRAS (do projeto, obrigatórias)
- Não contorna bloqueio: respeita o robots.txt, e HTTP 401/403/406/451 ou captcha viram "baixar à mão".
- Identifica-se com um User-Agent honesto, baixa um arquivo por vez e espera entre pedidos
  (2 s; 4 s no PNCP; 60 s depois de um HTTP 429, com uma única nova tentativa).
- Não apaga nada. Se o arquivo baixado for idêntico (SHA-256) a outro já existente em
  Legislacao e contratos TZ, ele não é salvo de novo e o log aponta o arquivo que já existe.
- Para não forçar o download de arquivos que estão só na nuvem do OneDrive, compara primeiro pelo
  tamanho e só calcula o hash de quem tem o mesmo tamanho.
- PDFs podem ter CPF de signatários: o script não lê o conteúdo. Não copie CPF para notas.

CONDA (Windows, Anaconda Prompt) — uma vez só:
    conda env create -f "_meta/scripts/baixar_documentos_busca.environment.yml"
  (cria o ambiente "tz-download" com Python 3.11, certifi e truststore; truststore faz o Python
  usar os certificados do Windows, o que evita erro de SSL em sites .gov.br com cadeia incompleta)
  Depois, a cada uso:
    conda activate tz-download
    cd "%USERPROFILE%\OneDrive\doutorado"
    python "_meta/scripts/baixar_documentos_busca.py" --simular
  Ou, sem ativar nada, dar dois cliques / rodar: _meta\scripts\baixar_documentos_busca.bat [opções]
  Qualquer ambiente conda com Python 3.9+ serve; certifi e truststore são opcionais, mas recomendados.

USO (da raiz do cofre)
    python "_meta/scripts/baixar_documentos_busca.py" --simular          # mostra o que faria
    python "_meta/scripts/baixar_documentos_busca.py"                    # baixa tudo o que não é manual
    python "_meta/scripts/baixar_documentos_busca.py" --rodada 3         # só a rodada 3
    python "_meta/scripts/baixar_documentos_busca.py" --prioridade P1 --limite 20
    python "_meta/scripts/baixar_documentos_busca.py" --linhas 150-173
    python "_meta/scripts/baixar_documentos_busca.py" --abrir-manuais    # abre no navegador os manuais
Rodar de novo é seguro: as linhas que já deram "ok" ou "já no cofre" num log anterior são puladas
(use --refazer para baixar de novo).
Só biblioteca padrão do Python 3.9+. Opcionais (o script usa se existirem): truststore ou certifi, para os certificados SSL.
"""
import argparse, csv, datetime, hashlib, json, os, re, sys, time, unicodedata, webbrowser
import ssl, urllib.error, urllib.parse, urllib.request, urllib.robotparser

# Console do Windows (Anaconda Prompt usa cp1252): não quebrar com acentos
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Certificados: 1) truststore (certificados do Windows/macOS); 2) certifi; 3) padrão do Python
SSL_FONTE, CTX = "padrão do Python", None
try:
    import truststore
    truststore.inject_into_ssl(); SSL_FONTE = "truststore (certificados do sistema)"
except Exception:
    try:
        import certifi
        CTX = ssl.create_default_context(cafile=certifi.where()); SSL_FONTE = "certifi"
    except Exception:
        pass
from html.parser import HTMLParser

UA = "PesquisaTarifaZero-UFABC/1.0 (download assistido de documentos publicos para pesquisa academica)"
PAUSA, PAUSA_PNCP, PAUSA_429, TIMEOUT = 2.0, 4.0, 60, 90
MAX_LINKS_HTML = 5

# ---------- caminhos ----------
def achar_raiz():
    d = os.path.dirname(os.path.abspath(__file__))
    for _ in range(6):
        if os.path.isdir(os.path.join(d, "03 - Dados")) and os.path.isdir(os.path.join(d, "04 - Análises")):
            return d
        d = os.path.dirname(d)
    sys.exit("Não achei a raiz do cofre (pastas '03 - Dados' e '04 - Análises'). Rode o script de dentro do cofre.")

RAIZ = achar_raiz()
LEG = os.path.join(RAIZ, "03 - Dados", "_data", "Legislacao e contratos TZ")
TRIAR = os.path.join(LEG, "_a triar")
FILA_PADRAO = os.path.join(RAIZ, "04 - Análises", "Pesquisa legal", "Busca de contratos — fila de download (12-10-2026).csv")
CAMPOS_LOG = ["quando", "n", "rodada", "prioridade", "id", "municipio", "uf", "modo", "url", "status", "http",
              "arquivo", "sha256", "bytes", "ja_existente", "detalhe"]

# ---------- utilitários ----------
def limpar_nome(s, maxlen=110):
    s = unicodedata.normalize("NFKC", str(s or ""))
    s = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", s)
    s = re.sub(r"\s+", " ", s).strip(" .-")
    return s[:maxlen].rstrip(" .-") or "documento"

def longo(p):
    """No Windows, caminhos com mais de 260 caracteres precisam de prefixo especial (OneDrive + nomes longos)."""
    if os.name == "nt":
        p = os.path.abspath(p)
        if len(p) > 240 and not p.startswith("\\\\?\\"):
            return "\\\\?\\" + p
    return p

def sem_acento(s):
    return unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode()

def sha256_arquivo(p, bloco=1 << 20):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(bloco), b""):
            h.update(b)
    return h.hexdigest()

class IndiceExistentes:
    """Arquivos já na pasta de legislação e contratos, por tamanho (stat não força download do OneDrive)."""
    def __init__(self, raiz):
        self.por_tamanho, self.hash_cache = {}, {}
        for d, _, fs in os.walk(raiz):
            for f in fs:
                if f.startswith("_log_download"):
                    continue
                p = os.path.join(d, f)
                try:
                    self.por_tamanho.setdefault(os.stat(p).st_size, []).append(p)
                except OSError:
                    pass
    def procurar(self, dados):
        h = hashlib.sha256(dados).hexdigest()
        for p in self.por_tamanho.get(len(dados), []):
            if p not in self.hash_cache:
                try:
                    self.hash_cache[p] = sha256_arquivo(p)
                except OSError:
                    continue
            if self.hash_cache[p] == h:
                return h, p
        return h, None
    def registrar(self, p, h, n):
        self.por_tamanho.setdefault(n, []).append(p); self.hash_cache[p] = h

class Bloqueio(Exception):
    pass

_robots = {}
def robots_permite(url):
    p = urllib.parse.urlparse(url)
    base = f"{p.scheme}://{p.netloc}"
    if base not in _robots:
        rp = urllib.robotparser.RobotFileParser()
        try:
            req = urllib.request.Request(base + "/robots.txt", headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=20, context=CTX) as r:
                rp.parse(r.read().decode("utf-8", "ignore").splitlines())
        except urllib.error.HTTPError as e:
            rp.parse([] if e.code >= 400 and e.code not in (401, 403) else ["User-agent: *", "Disallow: /"])
        except Exception:
            rp.parse([])  # robots.txt inacessível: tratado como permitido (convenção)
        _robots[base] = rp
    return _robots[base].can_fetch(UA, url)

_ultimo = {}
def baixar(url, pausa=PAUSA, aceitar="*/*"):
    """Devolve (bytes, content-type, nome sugerido, http). Levanta Bloqueio quando não se deve insistir."""
    host = urllib.parse.urlparse(url).netloc
    if not robots_permite(url):
        raise Bloqueio("robots.txt proíbe acesso automático: baixar à mão no navegador")
    espera = pausa - (time.time() - _ultimo.get(host, 0))
    if espera > 0:
        time.sleep(espera)
    for tentativa in (1, 2, 3):
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": aceitar})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT, context=CTX) as r:
                dados = r.read(); ct = r.headers.get("Content-Type", ""); cd = r.headers.get("Content-Disposition", "")
                _ultimo[host] = time.time()
                m = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)', cd or "")
                nome = urllib.parse.unquote(m.group(1)) if m else ""
                return dados, ct, nome, r.status
        except urllib.error.HTTPError as e:
            _ultimo[host] = time.time()
            if e.code == 429 and tentativa == 1:
                print(f"    HTTP 429: esperando {PAUSA_429} s e tentando uma vez"); time.sleep(PAUSA_429); continue
            if e.code in (500, 502, 503, 504) and tentativa < 3:
                espera_5xx = 20 * tentativa
                print(f"    HTTP {e.code} (servidor instável): esperando {espera_5xx} s e tentando de novo"); time.sleep(espera_5xx); continue
            if e.code in (401, 403, 406, 451, 429):
                raise Bloqueio(f"HTTP {e.code}: o site recusou o acesso automático; baixar à mão")
            raise
    raise Bloqueio("HTTP 429 repetido: tentar mais tarde")

def extensao(dados, ct, nome, url):
    if dados[:5] == b"%PDF-": return ".pdf"
    if dados[:2] == b"PK":
        n = (nome or url).lower()
        for e in (".docx", ".xlsx", ".odt", ".ods", ".zip"):
            if n.endswith(e) or e in n: return e
        return ".zip"
    if dados[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        return ".xls" if ".xls" in (nome or url).lower() else ".doc"
    c = ct.lower()
    if "json" in c: return ".json"
    if "html" in c or dados.lstrip()[:15].lower().startswith((b"<!doctype", b"<html")): return ".html"
    m = re.search(r"\.([a-z0-9]{2,5})$", (nome or urllib.parse.urlparse(url).path).lower())
    return "." + m.group(1) if m else ".bin"

def tem_captcha(dados):
    t = dados[:400000].lower()
    return any(k in t for k in (b"g-recaptcha", b"hcaptcha", b"captcha", b"cf-challenge", b"challenge-platform"))

class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.links = []
    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = dict(attrs).get("href")
            if href: self.links.append(href)

def links_de_documento(html_bytes, base_url):
    p = Links()
    try:
        p.feed(html_bytes.decode("utf-8", "ignore"))
    except Exception:
        return []
    host = urllib.parse.urlparse(base_url).netloc.lower().removeprefix("www.")
    out = []
    for h in p.links:
        u = urllib.parse.urljoin(base_url, h)
        if urllib.parse.urlparse(u).netloc.lower().removeprefix("www.") != host:
            continue
        if re.search(r"\.pdf($|\?)|download|baixar|getDownload|arquivo", u, re.I) and u not in out and u != base_url:
            out.append(u)
    return out[:MAX_LINKS_HTML]

# ---------- PNCP ----------
def pncp_alvos(url):
    m = re.search(r"/app/(contratos|editais|atas)/(\d{14})/(\d{4})/(\d+)(?:/(\d+))?", url)
    if not m: return None
    tipo, cnpj, ano, seq, seq2 = m.groups()
    b = "https://pncp.gov.br"
    if tipo == "contratos":
        meta = [f"{b}/api/pncp/v1/orgaos/{cnpj}/contratos/{ano}/{seq}", f"{b}/api/consulta/v1/orgaos/{cnpj}/contratos/{ano}/{seq}"]
        arq = f"{b}/api/pncp/v1/orgaos/{cnpj}/contratos/{ano}/{seq}/arquivos"
        termos = f"{b}/api/pncp/v1/orgaos/{cnpj}/contratos/{ano}/{seq}/termos"
    elif tipo == "editais":
        meta = [f"{b}/api/consulta/v1/orgaos/{cnpj}/compras/{ano}/{seq}", f"{b}/api/pncp/v1/orgaos/{cnpj}/compras/{ano}/{seq}"]
        arq = f"{b}/api/pncp/v1/orgaos/{cnpj}/compras/{ano}/{seq}/arquivos"; termos = None
    else:  # atas: /app/atas/<cnpj>/<ano>/<seq compra>/<seq ata>
        if not seq2: return None
        meta = [f"{b}/api/pncp/v1/orgaos/{cnpj}/compras/{ano}/{seq}/atas/{seq2}"]
        arq = f"{b}/api/pncp/v1/orgaos/{cnpj}/compras/{ano}/{seq}/atas/{seq2}/arquivos"; termos = None
    return dict(tipo=tipo, cnpj=cnpj, ano=ano, seq=seq, meta=meta, arquivos=arq, termos=termos)

def pncp_json(url):
    dados, ct, _, st = baixar(url, pausa=PAUSA_PNCP, aceitar="application/json")
    return json.loads(dados.decode("utf-8")) if dados.strip() else None

def lista_arquivos_pncp(j):
    if isinstance(j, dict):
        j = j.get("data") or j.get("arquivos") or []
    out = []
    for a in j or []:
        u = a.get("url") or a.get("uri") or a.get("urlArquivo")
        if u:
            out.append((u, a.get("titulo") or a.get("tipoDocumentoNome") or a.get("tipoDocumentoDescricao") or "arquivo"))
    return out

# ---------- execução ----------
def logs_anteriores():
    """Linhas já resolvidas: têm 'ok' ou 'já no cofre' mais recente que qualquer 'erro' ou 'sem arquivos'."""
    ult_ok, ult_erro = {}, {}
    if not os.path.isdir(TRIAR): return set()
    for d in os.listdir(TRIAR):
        p = os.path.join(TRIAR, d, "_log_download.csv")
        if os.path.isfile(p):
            with open(p, encoding="utf-8-sig") as f:
                for r in csv.DictReader(f, delimiter=";"):
                    n, q, st = r.get("n"), r.get("quando", ""), r.get("status")
                    if st in ("ok", "já no cofre"): ult_ok[n] = max(ult_ok.get(n, ""), q)
                    elif st in ("erro", "sem arquivos"): ult_erro[n] = max(ult_erro.get(n, ""), q)
    return {n for n, q in ult_ok.items() if q > ult_erro.get(n, "")}

def intervalo(s):
    out = set()
    for parte in s.split(","):
        a, _, b = parte.partition("-")
        out |= set(range(int(a), int(b or a) + 1))
    return out

def main():
    ap = argparse.ArgumentParser(description="Baixa os documentos da fila de busca de contratos para _a triar/.")
    ap.add_argument("--fila", default=FILA_PADRAO)
    ap.add_argument("--rodada", help="1-2 ou 3")
    ap.add_argument("--prioridade", help="P1, P2, P3, P4 ou R3")
    ap.add_argument("--linhas", help="ex.: 1-20,150-173 (coluna n da fila)")
    ap.add_argument("--limite", type=int, default=0, help="no máximo N linhas nesta execução")
    ap.add_argument("--simular", action="store_true", help="não baixa; só mostra o plano")
    ap.add_argument("--abrir-manuais", action="store_true", help="abre no navegador as linhas manuais (até 15)")
    ap.add_argument("--refazer", action="store_true", help="não pula as linhas já baixadas em execuções anteriores")
    ap.add_argument("--seguir-links", action="store_true", help="em páginas HTML, baixa também até 5 PDFs linkados do mesmo site")
    a = ap.parse_args()

    with open(a.fila, encoding="utf-8-sig") as f:
        fila = list(csv.DictReader(f, delimiter=";"))
    if a.rodada: fila = [r for r in fila if r["rodada"] == a.rodada]
    if a.prioridade: fila = [r for r in fila if r["prioridade"] == a.prioridade]
    if a.linhas:
        alvo = intervalo(a.linhas); fila = [r for r in fila if int(r["n"]) in alvo]
    feitos = set() if a.refazer else logs_anteriores()
    pular = [r for r in fila if r["n"] in feitos]; fila = [r for r in fila if r["n"] not in feitos]
    manuais = [r for r in fila if r["modo"] == "manual"]; auto = [r for r in fila if r["modo"] != "manual"]
    if a.limite: auto = auto[:a.limite]
    print(f"Python {sys.version.split()[0]} · ambiente: {os.environ.get('CONDA_DEFAULT_ENV') or sys.prefix} · SSL: {SSL_FONTE}")
    print(f"Cofre: {RAIZ}")
    print(f"Fila: {len(auto)} para baixar · {len(manuais)} manuais · {len(pular)} já feitas antes")

    if a.abrir_manuais:
        for r in manuais[:15]:
            print(f"  abrindo n{r['n']} {r['municipio']}-{r['uf']}: {r['motivo_manual']}"); webbrowser.open(r["url"]); time.sleep(1)
        if len(manuais) > 15: print(f"  (+{len(manuais)-15} manuais; rode de novo com --linhas)")
    if a.simular:
        for r in auto: print(f"  n{r['n']:>3} {r['modo']:6} {r['municipio']}-{r['uf']}  {r['url'][:100]}")
        for r in manuais: print(f"  n{r['n']:>3} manual {r['municipio']}-{r['uf']}  {r['motivo_manual'][:90]}")
        return

    hoje = datetime.date.today().isoformat()
    lote = os.path.join(TRIAR, f"download-{hoje}"); os.makedirs(lote, exist_ok=True)
    log_path = os.path.join(lote, "_log_download.csv"); novo = not os.path.isfile(log_path)
    flog = open(log_path, "a", newline="", encoding="utf-8-sig"); w = csv.DictWriter(flog, fieldnames=CAMPOS_LOG, delimiter=";")
    if novo: w.writeheader()
    print("Indexando arquivos existentes (por tamanho)…"); idx = IndiceExistentes(LEG)
    cont = {}

    def registrar(r, status, **k):
        cont[status] = cont.get(status, 0) + 1
        w.writerow({**{c: "" for c in CAMPOS_LOG}, "quando": datetime.datetime.now().isoformat(timespec="seconds"),
                    "n": r["n"], "rodada": r["rodada"], "prioridade": r["prioridade"], "id": r["id"],
                    "municipio": r["municipio"], "uf": r["uf"], "modo": r["modo"], "status": status, **k}); flog.flush()

    def salvar(r, dados, ct, nome, url, rotulo, http=""):
        ext = extensao(dados, ct, nome, url)
        h, existe = idx.procurar(dados)
        if existe:
            registrar(r, "já no cofre", url=url, http=http, sha256=h, bytes=len(dados), ja_existente=os.path.relpath(existe, RAIZ))
            print(f"    = já existe: {os.path.relpath(existe, LEG)}"); return ext
        pasta = os.path.join(lote, limpar_nome(r["uf"] or "_UF")); os.makedirs(longo(pasta), exist_ok=True)
        base = limpar_nome(f"{sem_acento(r['municipio'])}-{r['uf']} - r{r['rodada']} n{int(r['n']):03d} - {rotulo}")
        p = os.path.join(pasta, base + ext); k = 2
        while os.path.exists(longo(p)):
            p = os.path.join(pasta, f"{base} ({k}){ext}"); k += 1
        with open(longo(p), "wb") as f: f.write(dados)
        idx.registrar(p, h, len(dados))
        registrar(r, "ok", url=url, http=http, arquivo=os.path.relpath(p, RAIZ), sha256=h, bytes=len(dados))
        print(f"    + {os.path.relpath(p, lote)} ({len(dados)//1024} KB)"); return ext

    for r in manuais:
        registrar(r, "manual", url=r["url"], detalhe=r["motivo_manual"])

    for i, r in enumerate(auto, 1):
        rot = " ".join(x for x in (r["tipo"], r["numero"]) if x) or "documento"
        print(f"[{i}/{len(auto)}] n{r['n']} {r['municipio']}-{r['uf']} ({r['modo']})")
        try:
            if r["modo"] == "pncp":
                alvo = pncp_alvos(r["url"])
                if not alvo:
                    registrar(r, "manual", url=r["url"], detalhe="URL do PNCP não reconhecida"); continue
                rot = f"PNCP {alvo['tipo']} {alvo['ano']}-{alvo['seq']}"
                meta = None
                for mu in alvo["meta"]:
                    try:
                        meta = pncp_json(mu); break
                    except (urllib.error.HTTPError, urllib.error.URLError, ValueError):
                        continue
                if meta:
                    salvar(r, json.dumps(meta, ensure_ascii=False, indent=1).encode("utf-8"), "application/json", "", alvo["meta"][0], rot + " - metadados")
                try:
                    arqs = lista_arquivos_pncp(pncp_json(alvo["arquivos"]))
                except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
                    registrar(r, "erro", url=alvo["arquivos"], detalhe=f"lista de arquivos do PNCP indisponível ({e}); rode de novo mais tarde")
                    print(f"    ! lista de arquivos do PNCP indisponível: {e}"); continue
                if alvo["termos"]:
                    try:
                        for t in pncp_json(alvo["termos"]) or []:
                            st = t.get("sequencialTermoContrato") or t.get("sequencial")
                            if st:
                                for u, tit in lista_arquivos_pncp(pncp_json(f"{alvo['termos']}/{st}/arquivos")):
                                    arqs.append((u, f"termo {st} - {tit}"))
                    except (urllib.error.HTTPError, urllib.error.URLError, ValueError) as e:
                        print(f"    termos: {e}")
                if not arqs:
                    registrar(r, "sem arquivos", url=alvo["arquivos"], detalhe="o PNCP não lista arquivos" + ("" if meta else "; metadados indisponíveis")); continue
                for u, tit in arqs:
                    try:
                        d, ct, nome, st = baixar(u, pausa=PAUSA_PNCP)
                        salvar(r, d, ct, nome, u, f"{rot} - {tit}", http=st)
                    except Bloqueio as e:
                        registrar(r, "manual", url=u, detalhe=str(e))
                    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as e:
                        registrar(r, "erro", url=u, detalhe=str(e)[:200])
            else:
                d, ct, nome, st = baixar(r["url"])
                ext = extensao(d, ct, nome, r["url"])
                if ext == ".html" and tem_captcha(d):
                    registrar(r, "manual", url=r["url"], http=st, detalhe="página com captcha ou desafio anti-robô: baixar à mão")
                    print("    ! captcha ou desafio anti-robô: fica para baixar à mão"); continue
                salvar(r, d, ct, nome, r["url"], rot, http=st)
                if ext == ".html" and a.seguir_links:
                    for u in links_de_documento(d, r["url"]):
                        try:
                            d2, ct2, nome2, st2 = baixar(u)
                            if extensao(d2, ct2, nome2, u) != ".html":
                                salvar(r, d2, ct2, nome2, u, rot + " - anexo", http=st2)
                        except Bloqueio as e:
                            registrar(r, "manual", url=u, detalhe=str(e))
                        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as e:
                            registrar(r, "erro", url=u, detalhe=str(e)[:200])
        except Bloqueio as e:
            registrar(r, "manual", url=r["url"], detalhe=str(e)); print(f"    ! {e}")
        except urllib.error.HTTPError as e:
            registrar(r, "não encontrado" if e.code == 404 else "erro", url=r["url"], http=e.code, detalhe=str(e)[:200]); print(f"    ! HTTP {e.code}")
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
            msg = str(e)
            if "CERTIFICATE_VERIFY_FAILED" in msg:
                msg = "certificado SSL não verificado (instale truststore no ambiente: conda install -c conda-forge truststore); " + msg
            registrar(r, "erro", url=r["url"], detalhe=msg[:240]); print(f"    ! {msg[:160]}")

    flog.close()
    print("\nResumo:", ", ".join(f"{k} {v}" for k, v in sorted(cont.items())))
    print("Log:", os.path.relpath(log_path, RAIZ))
    print("Os arquivos ficam em _a triar/; a triagem para normas/, contratos/ ou capturas/ vem depois.")

if __name__ == "__main__":
    main()
