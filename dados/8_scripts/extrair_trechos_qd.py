# -*- coding: utf-8 -*-
r"""extrair_trechos_qd.py — baixa o texto dos diários do Querido Diário com achado relevante e recorta os trechos (v1, 17/10/2026).

Autor: Thiago Von Zeidler Gomes · Orientadora: Prof.ª Dra. Silvana Zioni · script escrito com Claude.
O ambiente do Claude não lê os .txt do Querido Diário; este script roda na sua máquina, baixa só os diários com excerto de
transporte coletivo (205 achados, ~176 diários), guarda em cache e grava um CSV com um trecho de ~2.500 caracteres em volta de
cada achado (CPF mascarado). Uso:
  cd /d "%USERPROFILE%\OneDrive\doutorado"
  python _meta\scripts\extrair_trechos_qd.py
"""
import csv, glob, os, re, sys, time, unicodedata, urllib.request, urllib.error, ssl, socket, gzip, hashlib
csv.field_size_limit(10**8)
CTX = None
try:
    import truststore; truststore.inject_into_ssl()
except Exception:
    try:
        import certifi; CTX = ssl.create_default_context(cafile=certifi.where())
    except Exception: pass
UA = "PesquisaTarifaZero-UFABC/1.0 (consulta a dados publicos para pesquisa academica)"
RAIZ = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
PL = os.path.join(RAIZ, "04 - Análises", "Pesquisa legal")
CACHE = os.path.join(RAIZ, "03 - Dados", "_data", "Legislacao e contratos TZ", "_a triar", "qd-diarios-txt")
sa = lambda s: unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
CPF = re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b")
REL = re.compile(r"transporte (publico |urbano |municipal )?coletivo|onibus|circular|tarifa zero|passe livre|transporte (publico )?gratuito|passageiros|subsidio ao transporte|bora de graca")

def baixar(url):
    k = os.path.join(CACHE, hashlib.sha1(url.encode()).hexdigest()[:20] + ".txt")
    if os.path.exists(k): return open(k, encoding="utf-8", errors="replace").read()
    for t in range(1, 5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "gzip"}), timeout=60, context=CTX) as r:
                b = r.read()
                if r.headers.get("Content-Encoding") == "gzip" or b[:2] == b"\x1f\x8b": b = gzip.decompress(b)
            txt = b.decode("utf-8", errors="replace"); os.makedirs(CACHE, exist_ok=True)
            open(k, "w", encoding="utf-8").write(txt); time.sleep(0.8); return txt
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(60); continue
            if e.code in (500, 502, 503, 504): time.sleep(10 * t); continue
            print(f"   HTTP {e.code}: {url}"); return ""
        except (urllib.error.URLError, TimeoutError, socket.timeout, ConnectionError):
            time.sleep(15 * t)
    return ""

def main():
    fonte = sorted(glob.glob(os.path.join(PL, "Querido Diário — normas e contratos abertos dos casos (*).csv")))[-1]
    rows = [x for x in csv.DictReader(open(fonte, encoding="utf-8-sig"), delimiter=";") if REL.search(sa(x["excerto"]))]
    print(f"{len(rows)} achados relevantes em {len({x['txt_url'] for x in rows})} diários ({os.path.basename(fonte)})")
    out = []
    for i, x in enumerate(rows, 1):
        txt = baixar(x["txt_url"])
        if not txt: continue
        flat = re.sub(r"\s+", " ", txt); fl = sa(flat)
        pos = -1
        for frag in (x["excerto"] or "").split(" || "):
            f = sa(re.sub(r"\s+", " ", frag)).replace("[cpf omitido]", "")
            for ini in (40, 120, 200):
                chave = f[ini:ini + 50].strip()
                if len(chave) > 25 and (p := fl.find(chave)) >= 0: pos = p; break
            if pos >= 0: break
        if pos < 0:
            m = REL.search(fl); pos = m.start() if m else 0
        trecho = CPF.sub("[CPF omitido]", flat[max(0, pos - 1200): pos + 1800])
        out.append(dict(municipio=x["municipio"], uf=x["uf"], data=x["data"], falta=x["falta"], busca=x["busca"], pdf=x["url"], trecho=trecho))
        if i % 20 == 0: print(f"   {i}/{len(rows)}", flush=True)
    vistos, uniq = set(), []
    for o in out:
        k = (o["pdf"], o["trecho"][:200])
        if k not in vistos: vistos.add(k); uniq.append(o)
    saida = os.path.join(PL, f"Querido Diário — trechos lidos dos achados ({time.strftime('%d-%m-%Y')}).csv")
    with open(saida, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(uniq[0]), delimiter=";"); w.writeheader(); w.writerows(uniq)
    print(f"\n{len(uniq)} trechos → {saida}\nPronto. Avise no chat.")

if __name__ == "__main__":
    main()
