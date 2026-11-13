# -*- coding: utf-8 -*-
r"""buscar_operadores_pncp.py — contratadas do transporte coletivo no PNCP, por município (frente das operadoras).

Autor: Thiago Von Zeidler Gomes · Orientadora: Prof.ª Dra. Silvana Zioni · script escrito com Claude (v1 14/10/2026; v2 15/10/2026; revisão 05/11/2026: --saida, retomada com --de preserva as linhas anteriores, mensagem de retomada com --lista).

Para quê: achar, no Portal Nacional de Contratações Públicas, o CNPJ das empresas que operam (ou locam veículos para)
o transporte coletivo gratuito dos municípios da lista, para fechar a coluna "Operador — CNPJ" da base-mestre.
O ambiente do Claude não alcança o PNCP; por isso o script roda na sua máquina (ambiente conda "tz-download").

Como funciona (API pública de consulta do PNCP, só leitura):
  1. Contratações publicadas com o código IBGE do município (7 modalidades, janelas de 1 ano desde --desde);
     as de transporte (pelo objeto) entram no CSV, com o vencedor de cada item quando houver resultado publicado.
  2. Contratos publicados pelos órgãos municipais achados no passo 1 (e pelos já conhecidos na lista).
  3. Grava um CSV para conferência e o JSON bruto de cada consulta (cache: rodar de novo não repete o que já veio).

O que mudou na v2 (15/10/2026):
  - Cache numa pasta fixa (_a triar/pncp-operadores-cache) e leitura do cache antigo (_a triar/pncp-operadores-*/cache):
    na v1 a pasta tinha a data do dia, e rodar no dia seguinte começava do zero.
  - A janela do ano corrente termina hoje; o cache dela vale por --validade dias (padrão 7) em vez de expirar todo dia.
  - Pedidos em paralelo (--paralelo, padrão 4), com intervalo mínimo entre pedidos e espera global em HTTP 429.
  - Sem internet: o script para e espera a rede voltar (até --espera-rede minutos) em vez de gravar centenas de erros
    e pular municípios; se não voltar, grava o que tem e diz de onde retomar (--de N).
  - Menos pedidos: só busca o vencedor de itens com resultado publicado (temResultado; no objeto de transporte coletivo
    ou de passageiros busca sempre, porque o campo erra em ~2% dos itens) e não busca vencedor de
    contratações de outro serviço (escolar, saúde, eventos...); na etapa 2 ignora fundos de saúde, educação,
    assistência e previdência. --completo desliga esses cortes.
  - "HTTP 204" (consulta sem resultado) deixa de ir para o log de erros: é só contagem.
  - --offline monta o CSV só com o cache, sem rede (útil com internet limitada).

Uso (da raiz do cofre, ou pelo .bat):
  python _meta/scripts/buscar_operadores_pncp.py                  # todos os municípios da lista
  python _meta/scripts/buscar_operadores_pncp.py --de 28          # retoma do 28º município da lista
  python _meta/scripts/buscar_operadores_pncp.py --so Conchas SP  # um município
  python _meta/scripts/buscar_operadores_pncp.py --offline        # só o cache, sem rede
  opções: --sem-resultados · --desde 2019 · --paralelo 2 · --validade 0 (rebaixa a janela atual) · --completo

Regras: respeita o robots.txt, intervalo mínimo entre pedidos, espera em 429 e 5xx; não contorna bloqueio.
O resultado é pista até conferência; nada entra na base sem passar pelo Registro de alterações pós-congelamento.
"""
import argparse, csv, datetime, glob, hashlib, json, os, re, socket, ssl, sys, threading, time, unicodedata
import urllib.error, urllib.parse, urllib.request, urllib.robotparser
from concurrent.futures import ThreadPoolExecutor

CTX = None; SSL_FONTE = "padrão do Python"
try:
    import truststore
    truststore.inject_into_ssl(); SSL_FONTE = "truststore (certificados do sistema)"
except Exception:
    try:
        import certifi
        CTX = ssl.create_default_context(cafile=certifi.where()); SSL_FONTE = "certifi"
    except Exception:
        pass

UA = "PesquisaTarifaZero-UFABC/1.0 (consulta a dados publicos do PNCP para pesquisa academica)"
INTERVALO, PAUSA_429, TIMEOUT = 0.4, 60, 40     # s entre inícios de pedido (todas as threads), espera em 429, timeout
API = "https://pncp.gov.br/api/consulta/v1"
API_PNCP = "https://pncp.gov.br/api/pncp/v1"
HOST = "pncp.gov.br"
MODALIDADES = (6, 8, 4, 7, 5, 9, 12)  # pregão eletr., dispensa, concorrência eletr., pregão pres., concorrência pres., inexigibilidade, credenciamento

def achar_raiz():
    d = os.path.dirname(os.path.abspath(__file__))
    for _ in range(6):
        if os.path.isdir(os.path.join(d, "03 - Dados")) and os.path.isdir(os.path.join(d, "04 - Análises")):
            return d
        d = os.path.dirname(d)
    sys.exit("Não achei a raiz do cofre. Rode o script de dentro do cofre.")
RAIZ = achar_raiz()
LISTA = os.path.join(RAIZ, "_meta", "scripts", "_scratch", "operadores-1014", "lista_pncp_operadores_1014.csv")
HOJE = datetime.date.today(); HOJE_S = HOJE.strftime("%Y%m%d")
TRIAR = os.path.join(RAIZ, "03 - Dados", "_data", "Legislacao e contratos TZ", "_a triar")
CACHE = os.path.join(TRIAR, "pncp-operadores-cache")
CACHES_ANTIGOS = sorted(glob.glob(os.path.join(TRIAR, "pncp-operadores-20*", "cache")), reverse=True)
LOG_CSV = os.path.join(CACHE, f"_log_pncp_operadores ({HOJE:%Y-%m-%d}).csv")
SAIDA_CSV = os.path.join(RAIZ, "04 - Análises", "Pesquisa legal", f"Operadoras — resultados do PNCP ({HOJE:%d-%m-%Y}).csv")

def sa(s): return unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().lower()
POS = re.compile(r"coletivo|passageiro|transporte (public|urbano|municipal|gratuit|circular|de pessoas)|onibus|circular|tarifa zero|passe livre|"
                 r"linhas? (urbana|municipa|rura)|concessao (do|de) servico|permissao (do|de) servico|fretamento|locacao de (veiculo|onibus|van|micro)|"
                 r"mobilidade urbana")
NEG = re.compile(r"escolar|aluno|estudant|universit|paciente|saude|tfd|hemodial|ambulanc|evento|merenda|combustiv|pneu|pecas|"
                 r"manutencao (de|da|dos) (veiculo|frota)|seguro|abrigo|ponto de onibus|sinaliz|lavagem|rastreamento|cartao|bilhetagem|"
                 r"assistencia social|cras|creas|idoso|atleta|esporte|cultura|turismo rural")
NUCLEO = re.compile(r"transporte (publico )?coletivo|transporte (publico )?de passageiros|circular|tarifa zero|passe livre|concessao|permissao|linhas? (urbana|municipa|rura)")
ORG_FORA = re.compile(r"fundo municipal de (saude|educacao|assistencia|previdencia|cultura|esporte|habitacao|meio ambiente)|"
                      r"instituto (municipal )?de previdencia|regime proprio|secretaria municipal de (saude|educacao)")

class SemRede(Exception): pass

class Rede:
    """Estado compartilhado entre as threads: intervalo mínimo, espera em 429, contagens, log e modo offline."""
    def __init__(self, paralelo, offline, validade, espera_rede):
        self.lock = threading.Lock(); self.prox = 0.0; self.pausa_ate = 0.0
        self.offline, self.validade, self.espera_rede = offline, validade, espera_rede
        self.stat = {"cache": 0, "rede": 0, "vazio": 0, "faltou_no_cache": 0}
        self.log = []; self.robots = None; self.sem_rede = False
        self.pool = ThreadPoolExecutor(max_workers=max(1, paralelo))
    def conta(self, k):
        with self.lock: self.stat[k] += 1
    def anota(self, *linha):
        with self.lock: self.log.append(list(linha))
    def vez(self):
        with self.lock:
            t = max(time.time(), self.prox, self.pausa_ate); self.prox = t + INTERVALO
        espera = t - time.time()
        if espera > 0: time.sleep(espera)
    def esperar_rede(self):
        """Bloqueia até o DNS do PNCP responder; levanta SemRede depois de espera_rede minutos."""
        with self.lock:
            if self.sem_rede: raise SemRede()
            limite = time.time() + 60 * self.espera_rede; avisou = False
            while True:
                try:
                    socket.getaddrinfo(HOST, 443); return
                except OSError:
                    if not avisou:
                        print(f"      sem internet (DNS de {HOST} não responde): esperando até {self.espera_rede} min…"); avisou = True
                    if time.time() > limite:
                        self.sem_rede = True; raise SemRede()
                    time.sleep(30)
R = None

def robots_ok(url):
    if R.robots is None:
        rp = urllib.robotparser.RobotFileParser()
        try:
            req = urllib.request.Request(f"https://{HOST}/robots.txt", headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=20, context=CTX) as r:
                rp.parse(r.read().decode("utf-8", "ignore").splitlines())
        except Exception:
            rp.parse([])
        R.robots = rp
    return R.robots.can_fetch(UA, url)

def chave(url): return hashlib.sha1(url.encode()).hexdigest()[:16] + ".json"

def ler_cache(url):
    """Procura a URL no cache novo e nos antigos; para a janela que termina hoje, aceita a mesma janela
    terminada até `validade` dias atrás. Devolve (achou, dado)."""
    cands = [(url, None)]
    if "dataFinal=" + HOJE_S in url:
        for d in range(1, R.validade + 1):
            cands.append((url.replace("dataFinal=" + HOJE_S, "dataFinal=" + (HOJE - datetime.timedelta(days=d)).strftime("%Y%m%d")), d))
    for u, _ in cands:
        for pasta in [CACHE] + CACHES_ANTIGOS:
            p = os.path.join(pasta, chave(u))
            if os.path.exists(p):
                try:
                    with open(p, encoding="utf-8") as f: return True, json.load(f)
                except (ValueError, OSError):
                    pass
    return False, None

def get_json(url):
    """GET com cache. Devolve dict/list, ou None (sem conteúdo ou erro registrado no log). Levanta SemRede."""
    achou, dado = ler_cache(url)
    if achou:
        R.conta("cache"); return dado
    if R.offline:
        R.conta("faltou_no_cache"); return None
    if R.sem_rede: raise SemRede()
    if not robots_ok(url):
        R.anota(url, "robots.txt proíbe", ""); return None
    tentativa = 0
    while True:
        tentativa += 1; R.vez()
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT, context=CTX) as r:
                corpo = r.read()
                dado = json.loads(corpo.decode("utf-8")) if r.status == 200 and corpo.strip() else None
        except urllib.error.HTTPError as e:
            if e.code in (204, 404):
                dado = None
            elif e.code == 429 and tentativa < 6:
                with R.lock: R.pausa_ate = max(R.pausa_ate, time.time() + PAUSA_429)
                print(f"      HTTP 429: todas as consultas esperam {PAUSA_429} s"); continue
            elif e.code in (500, 502, 503, 504) and tentativa < 4:
                time.sleep(15 * tentativa); continue
            else:
                R.anota(url, f"HTTP {e.code}", e.read()[:300].decode("utf-8", "ignore")); return None
        except (urllib.error.URLError, TimeoutError, ConnectionError, socket.timeout) as e:
            motivo = str(getattr(e, "reason", e))
            if tentativa < 3:
                time.sleep(5 * tentativa); continue
            try:
                socket.getaddrinfo(HOST, 443)
            except OSError:
                R.esperar_rede(); tentativa = 0; continue       # a rede voltou: tenta de novo do zero
            R.anota(url, "falha de conexão", motivo[:200]); return None   # rede ok, o pedido é que falha: não grava cache
        R.conta("rede")
        if dado is None: R.conta("vazio")
        os.makedirs(CACHE, exist_ok=True)
        with open(os.path.join(CACHE, chave(url)), "w", encoding="utf-8") as f:
            json.dump(dado, f, ensure_ascii=False)
        return dado

def paginas(base_url, maximo=40):
    out, p = [], 1
    while p <= maximo:
        sep = "&" if "?" in base_url else "?"
        d = get_json(f"{base_url}{sep}pagina={p}&tamanhoPagina=50")
        if not d: break
        out += (d.get("data") if isinstance(d, dict) else d) or []
        tot = (d.get("totalPaginas") if isinstance(d, dict) else 1) or 1
        if p >= tot: break
        p += 1
    return out

def em_paralelo(fn, tarefas):
    """Roda fn(tarefa) no pool, preserva a ordem e propaga SemRede."""
    return list(R.pool.map(fn, tarefas))

def janelas(desde):
    ini = datetime.date(desde, 1, 1)
    while ini <= HOJE:
        fim = min(ini + datetime.timedelta(days=364), HOJE)
        yield ini.strftime("%Y%m%d"), fim.strftime("%Y%m%d")
        ini = fim + datetime.timedelta(days=1)

def municipal(razao, completo):
    r = sa(razao)
    if "camara" in r: return False
    if not completo and ORG_FORA.search(r): return False
    return any(k in r for k in ("municipio", "prefeitura", "fundo municipal", "autarquia", "servico autonomo", "empresa publica",
                                "companhia municipal", "superintendencia", "secretaria municipal", "instituto municipal", "fundacao municipal"))

def linha_base(m, **kw):
    d = {"municipio": m["municipio"], "uf": m["uf"], "grupo": m["grupo"], "operador_atual": m.get("operador_atual", ""), "cnpj_atual": m.get("cnpj_atual", "")}
    d.update(kw); return d

def resultados(x, m, a):
    o = x.get("orgaoEntidade") or {}; cnpj, ano, seq = o.get("cnpj"), x.get("anoCompra"), x.get("sequencialCompra")
    obj = sa(x.get("objetoCompra")); marca = "sim" if NEG.search(obj) else ""
    comum = dict(fonte="", orgao_cnpj=cnpj, orgao=o.get("razaoSocial"), numero=x.get("numeroCompra"), ano=ano, sequencial=seq,
                 objeto=(x.get("objetoCompra") or "")[:400].replace("\n", " "), fornecedor="", cnpj_fornecedor="", vigencia_inicio="",
                 vigencia_fim="", marca_outro_servico=marca, url=f"https://pncp.gov.br/app/editais/{cnpj}/{ano}/{seq}")
    sem = [linha_base(m, **dict(comum, fonte="contratação sem vencedor publicado",
                                valor_global=x.get("valorTotalHomologado") or x.get("valorTotalEstimado"), tipo=x.get("modalidadeNome")))]
    if a.sem_resultados or not (cnpj and ano and seq): return sem
    if marca and not a.completo:
        sem[0]["fonte"] = "contratação de outro serviço (vencedor não buscado)"; return sem
    d = get_json(f"{API_PNCP}/orgaos/{cnpj}/compras/{ano}/{seq}/itens?pagina=1&tamanhoPagina=50")
    itens = ((d.get("data") or []) if isinstance(d, dict) else (d or []))[:20]
    if not itens: return sem
    nucleo = bool(NUCLEO.search(obj))
    def um(it):
        out = []
        res = None
        if it.get("temResultado") is not False or a.completo or nucleo:   # temResultado=False erra em ~2%: no núcleo, busca sempre
            rd = get_json(f"{API_PNCP}/orgaos/{cnpj}/compras/{ano}/{seq}/itens/{it.get('numeroItem')}/resultados")
            res = (rd.get("data") or []) if isinstance(rd, dict) else (rd or [])
        if not res:
            out.append(linha_base(m, **dict(comum, fonte="item sem resultado publicado", valor_global=it.get("valorTotal"),
                tipo=f"item {it.get('numeroItem')} ({it.get('situacaoCompraItemNome')}): {(it.get('descricao') or '')[:120]} | {it.get('quantidade')} {it.get('unidadeMedida')} a R$ {it.get('valorUnitarioEstimado')} (estimado)")))
        for r in res or []:
            out.append(linha_base(m, **dict(comum, fonte="resultado da contratação", fornecedor=r.get("nomeRazaoSocialFornecedor"),
                cnpj_fornecedor=r.get("niFornecedor"), valor_global=r.get("valorTotalHomologado"),
                tipo=f"item {it.get('numeroItem')}: {(it.get('descricao') or '')[:80]}")))
        return out
    return [l for it in itens for l in um(it)]   # sequencial: esta função já roda dentro do pool (pool aninhado travaria)

def um_municipio(m, a):
    mun, uf, ibge = m["municipio"], m["uf"], m["ibge"]
    orgs = {c: "" for c in (m.get("orgaos_conhecidos") or "").split() if c}
    tarefas = [(di, df, mod) for di, df in janelas(a.desde) for mod in MODALIDADES]
    lotes = em_paralelo(lambda t: paginas(f"{API}/contratacoes/publicacao?dataInicial={t[0]}&dataFinal={t[1]}&codigoModalidadeContratacao={t[2]}&codigoMunicipioIbge={ibge}", maximo=20), tarefas)
    compras, vistas = [], set()
    for lote in lotes:
        for x in lote:
            o = x.get("orgaoEntidade") or {}
            if not (o.get("cnpj") and municipal(o.get("razaoSocial", ""), a.completo)): continue
            orgs.setdefault(o["cnpj"], o.get("razaoSocial", ""))
            k = (o["cnpj"], x.get("anoCompra"), x.get("sequencialCompra"))
            if k in vistas or not POS.search(sa(x.get("objetoCompra"))): continue
            vistas.add(k); compras.append(x)
    linhas = [l for bloco in em_paralelo(lambda x: resultados(x, m, a), compras) for l in bloco]
    print(f"   órgãos: {len(orgs)} · contratações de transporte: {len(compras)}")
    t2 = [(c, di, df) for c in orgs for di, df in janelas(a.desde)]
    for (cnpj, di, df), cs in zip(t2, em_paralelo(lambda t: paginas(f"{API}/contratos?dataInicial={t[1]}&dataFinal={t[2]}&cnpjOrgao={t[0]}"), t2)):
        for c in cs:
            obj = sa(c.get("objetoContrato"))
            if not POS.search(obj): continue
            oe = c.get("orgaoEntidade") or {}; ano, seq = c.get("anoContrato"), c.get("sequencialContrato")
            linhas.append(linha_base(m, fonte="contrato", orgao_cnpj=oe.get("cnpj", cnpj), orgao=oe.get("razaoSocial", orgs[cnpj]),
                numero=c.get("numeroContratoEmpenho"), ano=ano, sequencial=seq, objeto=(c.get("objetoContrato") or "")[:400].replace("\n", " "),
                fornecedor=c.get("nomeRazaoSocialFornecedor"), cnpj_fornecedor=c.get("niFornecedor"), vigencia_inicio=c.get("dataVigenciaInicio"),
                vigencia_fim=c.get("dataVigenciaFim"), valor_global=c.get("valorGlobal"), tipo=(c.get("tipoContrato") or {}).get("nome"),
                marca_outro_servico="sim" if NEG.search(obj) else "", url=f"https://pncp.gov.br/app/contratos/{oe.get('cnpj', cnpj)}/{ano}/{seq}"))
    return linhas

CAMPOS = ["municipio", "uf", "grupo", "fonte", "orgao_cnpj", "orgao", "numero", "ano", "sequencial", "objeto", "fornecedor", "cnpj_fornecedor",
          "vigencia_inicio", "vigencia_fim", "valor_global", "tipo", "marca_outro_servico", "url", "operador_atual", "cnpj_atual"]

def gravar(linhas):
    vistos, uniq = set(), []
    for l in linhas:
        k = (l["url"], l["cnpj_fornecedor"], l["tipo"])
        if k in vistos: continue
        vistos.add(k); uniq.append(l)
    with open(SAIDA_CSV, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS, delimiter=";"); w.writeheader(); w.writerows(uniq)
    os.makedirs(CACHE, exist_ok=True)
    with open(LOG_CSV, "w", newline="", encoding="utf-8") as f:
        csv.writer(f, delimiter=";").writerows([["onde", "o quê", "detalhe"]] + R.log)
    return len(uniq)

def main():
    global R, SAIDA_CSV
    ap = argparse.ArgumentParser(description="Contratadas do transporte coletivo no PNCP, por município.")
    ap.add_argument("--lista", default=LISTA); ap.add_argument("--so", nargs=2, metavar=("MUNICIPIO", "UF"))
    ap.add_argument("--de", type=int, default=1, help="começa no N-ésimo município da lista (1 = o primeiro)")
    ap.add_argument("--ate", type=int, default=0, help="para no N-ésimo município (0 = até o fim)")
    ap.add_argument("--desde", type=int, default=2021)
    ap.add_argument("--sem-resultados", action="store_true", help="não busca os vencedores das contratações (mais rápido)")
    ap.add_argument("--paralelo", type=int, default=4, help="pedidos simultâneos (padrão 4; use 1 ou 2 se a rede estiver fraca)")
    ap.add_argument("--validade", type=int, default=7, help="dias em que o cache da janela atual vale (padrão 7; 0 = baixa de novo)")
    ap.add_argument("--espera-rede", type=int, default=20, help="minutos de espera quando a internet cai (padrão 20)")
    ap.add_argument("--offline", action="store_true", help="não usa a rede: monta o CSV só com o cache")
    ap.add_argument("--completo", action="store_true", help="desliga os cortes da v2 (fundos de saúde/educação, vencedor de outros serviços, itens sem resultado)")
    ap.add_argument("--saida", help="caminho do CSV de saída (padrão: 'Operadoras — resultados do PNCP (DD-MM-AAAA).csv' em Pesquisa legal)")
    a = ap.parse_args()
    if a.saida: SAIDA_CSV = os.path.abspath(a.saida)  # 05/11/2026: rodadas com lista própria (ex.: pendências) não sobrescrevem a das operadoras
    R = Rede(1 if a.offline else a.paralelo, a.offline, a.validade, a.espera_rede)
    lista = list(csv.DictReader(open(a.lista, encoding="utf-8-sig"), delimiter=";"))
    if a.so:
        lista = [r for r in lista if sa(r["municipio"]) == sa(a.so[0]) and r["uf"].upper() == a.so[1].upper()]
        SAIDA_CSV = SAIDA_CSV.replace(").csv", f", {a.so[0]}-{a.so[1].upper()}).csv")
        if not lista: sys.exit("Município não está na lista.")
    total = len(lista); fim = a.ate or total
    if a.offline: SAIDA_CSV = SAIDA_CSV.replace(").csv", ", só cache).csv")
    print(f"SSL: {SSL_FONTE} · paralelo: {R.pool._max_workers} · {'OFFLINE (só cache)' if a.offline else 'rede'}\nLista: {a.lista} ({total} municípios; de {a.de} a {fim})")
    print(f"Cache: {CACHE}" + (f" (+ {len(CACHES_ANTIGOS)} pasta(s) antiga(s) só para leitura)" if CACHES_ANTIGOS else ""))
    linhas, t0, feitos = [], time.time(), 0
    if a.de > 1 and os.path.exists(SAIDA_CSV):  # 05/11/2026: ao retomar com --de N, preserva as linhas dos municípios anteriores já gravadas
        antes_de = {(sa(r["municipio"]), r["uf"].upper()) for r in lista[:a.de - 1]}
        linhas = [r for r in csv.DictReader(open(SAIDA_CSV, encoding="utf-8-sig"), delimiter=";") if (sa(r.get("municipio")), str(r.get("uf", "")).upper()) in antes_de]
        print(f"Retomada: {len(linhas)} linhas dos municípios 1–{a.de - 1} preservadas de {SAIDA_CSV}")
    try:
        for k, m in enumerate(lista, 1):
            if k < a.de or k > fim: continue
            t = time.time(); antes = dict(R.stat)
            print(f"[{k}/{total}] {m['municipio']}/{m['uf']} (IBGE {m['ibge']})")
            linhas += um_municipio(m, a); feitos += 1
            n = gravar(linhas); dt = time.time() - t
            resto = (fim - k) * (time.time() - t0) / feitos
            print(f"   {dt:.0f} s · da rede {R.stat['rede'] - antes['rede']} · do cache {R.stat['cache'] - antes['cache']}"
                  + (f" · faltaram no cache {R.stat['faltou_no_cache'] - antes['faltou_no_cache']}" if a.offline else "")
                  + f" · CSV com {n} linhas · faltam ~{resto / 60:.0f} min")
    except SemRede:
        n = gravar(linhas)
        print(f"\nA internet não voltou em {a.espera_rede} min. Gravei {n} linhas. Para retomar:\n"
              f'  python _meta/scripts/buscar_operadores_pncp.py --lista "{a.lista}" --saida "{SAIDA_CSV}" --de {k}\n(o que já veio está no cache)')
        R.pool.shutdown(wait=False); sys.exit(2)
    R.pool.shutdown()
    print(f"\nPronto em {(time.time() - t0) / 60:.1f} min. {gravar(linhas)} linhas em:\n  {SAIDA_CSV}\n"
          f"Consultas: rede {R.stat['rede']} (sem conteúdo {R.stat['vazio']}) · cache {R.stat['cache']}"
          + (f" · faltaram no cache {R.stat['faltou_no_cache']}" if a.offline else "") + f" · erros no log {len(R.log)}\nLog: {LOG_CSV}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrompido. O que já veio está no cache; rode de novo (com --de N) para continuar.")
        os._exit(1)
