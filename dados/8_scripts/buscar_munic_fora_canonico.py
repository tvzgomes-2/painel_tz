#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
buscar_munic_fora_canonico.py — busca ativa dos municípios que DECLARAM
Tarifa Zero à MUNIC 2020 e NÃO estão na base canônica, em três fontes:
PNCP (contratações), SAPL (leis da Câmara) e Querido Diário (diários oficiais).

Criado em 25/09/2026.
Autor: Thiago Von Zeidler Gomes
Orientadora: Prof.ª Dra. Silvana Zioni

POR QUE ESTA LISTA
  A MUNIC 2020 (IBGE, bloco 3.3, MTRA2010 = isenção para "toda a população")
  é AUTODECLARADA. Na comparação de 24/09/2026 ([[MUNIC x levantamento
  documental (24-09-2026)]]), 126 municípios declaram TZ e estão fora da base.
  Eles NÃO entram na base sem documento (Regras, A.2 e A.2c). Este script
  procura esse documento e faz uma triagem. Ele NÃO classifica: toda linha
  "forte" ainda precisa de leitura humana da norma ou do contrato.

ENTRADA (padrão)
  03 - Dados/_data/casos por fonte/MUNIC x levantamento documental (24-09-2026).xlsx
  aba "MUNIC declara TZ — fora". Ou --csv com colunas municipio, uf, cod_ibge.

FONTES E O QUE CADA UMA PROVA
  pncp        Busca pública do PNCP (/api/search) por "<município> <termo>",
              em editais, contratos e atas. Filtra município + UF e o OBJETO.
              Prova: contratação de transporte coletivo; "forte" quando o
              objeto diz gratuito / tarifa zero / passe livre. Só existe
              depois de 04/2021 (Lei 14.133).
  sapl        1) OFFLINE: o corpus já colhido em
              saida_sapl_uniao_20260920/sapl_corpus.csv (cobre poucos da lista).
              2) AO VIVO: /api/norma/normajuridica/?ementa=<termo> nos hosts
              conhecidos (saida_sapl/sapl_hosts.csv) que não estão no corpus.
              3) --descobrir: tenta achar host SAPL para quem não tem.
              Prova: norma da Câmara (lei). Decreto do Executivo NÃO está no SAPL.
  qd          Querido Diário (/gazettes, territory_ids = IBGE 7 dígitos).
              ⚠️ A querystring do QD é frouxa (lição de 20/09/2026: só 3 de
              15.000 registros tinham a frase de fato). Por isso o script SÓ
              aceita excerto em que a frase aparece contígua. Cobertura do QD
              é parcial: município sem diário indexado volta vazio (NA ≠ 0).

SAÍDA  (_meta/scripts/saida_munic_fora_AAAA-MM-DD/)
  pncp_achados.csv · sapl_achados.csv · qd_achados.csv  (uma linha por achado)
  resumo.csv / resumo.xlsx  (um município por linha: contagem por fonte,
                             melhor evidência de cada, triagem)
  _feito_<fonte>.txt        (checkpoint: rodar de novo retoma)
  log.txt

TRIAGEM (não é classificação)
  forte   algum achado diz gratuito/tarifa zero/passe livre JUNTO de
          transporte coletivo/ônibus/circular/passageiros.
  medio   só contratação ou norma de transporte coletivo municipal, sem
          palavra de gratuidade (serviço existe; regra de acesso não lida).
  nada    nenhuma fonte devolveu achado — NÃO quer dizer "não tem TZ":
          pode ser falta de cobertura da fonte (NA ≠ 0). Coluna "cobertura"
          diz quais fontes tinham como responder.

USO (do seu terminal normal — pncp.gov.br é bloqueado no sandbox do Cowork)
  python buscar_munic_fora_canonico.py autoteste          # testa a lógica, offline
  python buscar_munic_fora_canonico.py rodar              # todas as fontes
  python buscar_munic_fora_canonico.py rodar --fontes pncp,qd
  python buscar_munic_fora_canonico.py rodar --fontes sapl --descobrir
  python buscar_munic_fora_canonico.py rodar --limite 5   # ensaio com 5 municípios
  python buscar_munic_fora_canonico.py resumo             # só refaz o resumo

  Opções: --delay 1.0 (segundos entre chamadas ao mesmo host) · --recomecar
  (ignora checkpoints) · --saida <pasta> · --csv <lista.csv> · --desde 2019-01-01 (QD)

Dependências: requests, openpyxl (pip install requests openpyxl).
"""

import argparse
import csv
import datetime as dt
import json
import os
import re
import socket
import sys
import time
import unicodedata
from pathlib import Path

AQUI = Path(__file__).resolve().parent
COFRE = AQUI.parent.parent
ENTRADA_PADRAO = COFRE / "03 - Dados" / "_data" / "casos por fonte" / "MUNIC x levantamento documental (24-09-2026).xlsx"
ABA_PADRAO = "MUNIC declara TZ — fora"
IBGE_CSV = AQUI / "municipios_ibge_5570.csv"
SAPL_HOSTS = AQUI / "saida_sapl" / "sapl_hosts.csv"
SAPL_CORPUS = AQUI / "saida_sapl_uniao_20260920" / "sapl_corpus.csv"
UA = "Pesquisa de doutorado UFABC - Tarifa Zero (contato: thiago@poloplanejamento.com)"

PNCP_SEARCH = "https://pncp.gov.br/api/search/"
QD_API = "https://api.queridodiario.org.br/gazettes"

# ------------------------------------------------------------------ termos
PNCP_TERMOS = ["transporte coletivo", "gratuito", "tarifa zero", "passe livre", "circular", "onibus urbano"]
SAPL_TERMOS = ["tarifa zero", "passe livre", "transporte coletivo", "transporte gratuito",
               "gratuidade", "circular", "onibus"]
QD_TERMOS = ["tarifa zero", "passe livre", "transporte coletivo gratuito", "transporte gratuito",
             "onibus gratuito", "circular gratuito", "transporte publico gratuito"]

RE_GRAT = re.compile(r"gratuit|tarifa zero|passe livre|custo zero|sem cobranca de tarifa|isencao (total )?da tarifa")
RE_COLET = re.compile(r"transporte (publico )?coletivo|coletivo urbano|coletivo municipal|onibus|micro ?onibus|"
                      r"(linha|onibus|transporte|servico) circular|circular (municipal|urbano|gratuito)|passageir|transporte (publico )?(urbano|municipal)")
# ruído observado na rodada de 25/09/2026 (130 municípios): abrigos/pontos, manutenção de frota,
# passagens para servidores, locação sem motorista, "ofício circular", "concreto circular"...
RE_EXCLUI = re.compile(r"escolar|alunos|estudante|residuo|lixo|coleta de|paciente|saude|tfd|hemodial|merenda|carga|frete|"
                       r"distribuicao gratuita|cessao (de uso )?gratuita|wi ?fi|curso de|cursos|condutores|vale.?transporte|fretamento|turismo|"
                       r"eleitor|eleicao|evento|festa|romaria|abrigo|ponto(s)? de onibus|passagens? de onibus|passagens? rodoviar|"
                       r"manutencao|borracharia|retifica|pneu|pecas|recapag|sem motorista|sem condutor|trabalhadores|"
                       r"oficio circular|concreto circular|dancas? circular|saas|software|leito|diaria")


def nfd(s):
    s = unicodedata.normalize("NFKD", str(s or ""))
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def limpa(s):
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", nfd(s))).strip()


def contem_frase(texto, frase):
    """frase contígua, sem acento, minúscula, pontuação normalizada."""
    t, f = " " + limpa(texto) + " ", " " + limpa(frase) + " "
    return f in t


def triagem_texto(texto):
    """'forte' | 'medio' | '' para um trecho (objeto, ementa ou excerto)."""
    t = limpa(texto)
    if not t:
        return ""
    col = bool(RE_COLET.search(t))
    gra = bool(RE_GRAT.search(t))
    exc = bool(RE_EXCLUI.search(t))
    if col and gra and not re.search(r"distribuicao gratuita|cessao (de uso )?gratuita|wi ?fi", t):
        return "forte"
    if col and not exc:
        return "medio"
    return ""


# ------------------------------------------------------------------ HTTP
class Http:
    def __init__(self, delay=1.0, timeout=30, tentativas=4, backoff_max=60):
        import requests
        self.rq = requests
        self.s = requests.Session()
        self.s.headers["User-Agent"] = UA
        self.delay, self.timeout, self.tentativas, self.backoff_max = delay, timeout, tentativas, backoff_max
        self._ultimo = {}

    def _nova_sessao(self):
        try:
            self.s.close()
        except Exception:
            pass
        self.s = self.rq.Session()
        self.s.headers["User-Agent"] = UA

    def _espera_rede(self, host, maximo=1800):
        import socket
        t0 = time.time(); avisou = False
        while True:
            try:
                socket.getaddrinfo(host, 443)
                if avisou:
                    print(f"  rede de volta após {int(time.time() - t0)} s")
                return True
            except OSError:
                if time.time() - t0 > maximo:
                    return False
                if not avisou:
                    print(f"  sem rede/DNS para {host} — aguardando voltar (até {maximo // 60} min)…"); avisou = True
                time.sleep(30)

    def get_json(self, url, params=None):
        from urllib.parse import urlparse
        host = urlparse(url).netloc
        erro = None
        for k in range(1, self.tentativas + 1):
            t = self._ultimo.get(host)
            if t is not None:
                espera = self.delay - (time.time() - t)
                if espera > 0:
                    time.sleep(espera)
            self._espera_rede(host)   # 26/09/2026: sem DNS/rede, espera voltar em vez de queimar tentativas
            try:
                r = self.s.get(url, params=params, timeout=self.timeout)
                self._ultimo[host] = time.time()
                if r.status_code == 429 or r.status_code >= 500:
                    raise self.rq.exceptions.HTTPError(f"HTTP {r.status_code}", response=r)
                if r.status_code >= 400:
                    return None, f"HTTP {r.status_code}"
                if r.status_code == 204 or not r.content.strip():
                    return None, ""   # 26/09/2026: 204/corpo vazio = sem dados (ex.: item sem resultado), não é falha
                return r.json(), ""
            except (self.rq.exceptions.Timeout, self.rq.exceptions.ConnectionError,
                    self.rq.exceptions.HTTPError, ValueError) as e:
                self._ultimo[host] = time.time()
                erro = f"{type(e).__name__}: {e}"
                if isinstance(e, self.rq.exceptions.ConnectionError):
                    # 26/09/2026: o PNCP derruba conexões keep-alive reaproveitadas (ConnectionResetError 10054);
                    # abrir uma sessão nova evita que a conexão morta contamine as consultas seguintes.
                    self._nova_sessao()
                if k < self.tentativas:
                    # 26/09/2026: queda de conexão pede espera mais longa (15, 30, 45 s) que erro HTTP
                    esp = 15 * k if isinstance(e, self.rq.exceptions.ConnectionError) else 3 * 2 ** (k - 1)
                    time.sleep(min(esp, max(self.backoff_max, 45)))
        return None, erro


# ------------------------------------------------------------------ entrada
def ler_ibge7():
    m = {}
    if IBGE_CSV.exists():
        with open(IBGE_CSV, encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                m[str(r["cod_ibge"])[:6]] = str(r["cod_ibge"])
    return m


def ler_lista(args):
    ibge7 = ler_ibge7()
    muns = []
    if args.csv:
        with open(args.csv, encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                muns.append(dict(municipio=r["municipio"], uf=r["uf"], cod6=str(r["cod_ibge"])[:6]))
    else:
        import openpyxl
        wb = openpyxl.load_workbook(ENTRADA_PADRAO, read_only=True, data_only=True)
        ws = wb[ABA_PADRAO]
        rows = list(ws.iter_rows(values_only=True))
        h = [str(x) for x in rows[0]]
        ix = {k: i for i, k in enumerate(h)}
        for r in rows[1:]:
            if not r or not r[ix["Município"]]:
                continue
            muns.append(dict(
                municipio=r[ix["Município"]], uf=r[ix["UF"]], cod6=str(r[ix["Código IBGE"]])[:6],
                munic_regulacao=r[ix.get("MUNIC 2020 — regulamentação", -1)] if "MUNIC 2020 — regulamentação" in ix else "",
                munic_onibus=r[ix.get("MUNIC 2020 — ônibus intramunicipal", -1)] if "MUNIC 2020 — ônibus intramunicipal" in ix else "",
            ))
    vistos, out = set(), []
    for m in muns:
        k = (m["cod6"], m["uf"])
        if k in vistos:
            continue
        vistos.add(k)
        m["cod7"] = ibge7.get(m["cod6"], "")
        out.append(m)
    if args.limite:
        out = out[: args.limite]
    return out


# ------------------------------------------------------------------ util saída
class Saida:
    def __init__(self, pasta, recomecar=False):
        self.p = Path(pasta)
        self.p.mkdir(parents=True, exist_ok=True)
        self.recomecar = recomecar
        if recomecar:
            for f in list(self.p.glob("*_achados.csv")) + list(self.p.glob("_feito_*.txt")):
                f.unlink()
        self.log_f = open(self.p / "log.txt", "a", encoding="utf-8")

    def log(self, msg):
        linha = f"{dt.datetime.now():%Y-%m-%d %H:%M:%S} {msg}"
        print(linha)
        self.log_f.write(linha + "\n")
        self.log_f.flush()

    def feitos(self, fonte):
        f = self.p / f"_feito_{fonte}.txt"
        if not f.exists():
            return set()
        return set(x.strip() for x in f.read_text(encoding="utf-8").splitlines() if x.strip())

    def marca(self, fonte, chave):
        with open(self.p / f"_feito_{fonte}.txt", "a", encoding="utf-8") as f:
            f.write(chave + "\n")

    def grava(self, nome, colunas, linhas):
        arq = self.p / nome
        novo = not arq.exists()
        with open(arq, "a", newline="", encoding="utf-8-sig" if novo else "utf-8") as f:
            w = csv.DictWriter(f, fieldnames=colunas, extrasaction="ignore")
            if novo:
                w.writeheader()
            for l in linhas:
                w.writerow(l)


def chave(m):
    return f"{m['cod6']}|{m['municipio']}|{m['uf']}"


# ------------------------------------------------------------------ PNCP
PNCP_COLS = ["cod_ibge", "municipio", "uf", "triagem", "tipo", "data", "orgao", "objeto", "link", "termo_busca"]


def pncp_link(item_url):
    p = (item_url or "").strip("/").split("/")
    if len(p) == 4 and p[0] in ("compras", "contratos", "atas"):
        base = {"compras": "editais", "contratos": "contratos", "atas": "atas"}[p[0]]
        return f"https://pncp.gov.br/app/{base}/{p[1]}/{p[2]}/{p[3]}"
    return "https://pncp.gov.br" + (item_url or "")


def rodar_pncp(muns, http, out):
    feitos = out.feitos("pncp")
    for i, m in enumerate(muns, 1):
        if chave(m) in feitos:
            continue
        achados, erros = {}, 0
        for termo in PNCP_TERMOS:
            for tipo in ("edital", "contrato", "ata"):
                j, err = http.get_json(PNCP_SEARCH, dict(q=f"{m['municipio']} {termo}", tipos_documento=tipo,
                                                         ordenacao="-data", pagina=1, tam_pagina=50, status="todos"))
                if err:
                    erros += 1
                    out.log(f"  PNCP {m['municipio']}/{m['uf']} '{termo}' {tipo}: {err}")
                    continue
                for it in (j or {}).get("items", []):
                    if limpa(it.get("municipio_nome")) != limpa(m["municipio"]) or (it.get("uf") or "") != m["uf"]:
                        continue
                    obj = it.get("description") or it.get("title") or ""
                    tri = triagem_texto(obj)
                    if not tri:
                        continue
                    url = it.get("item_url") or ""
                    if url in achados and achados[url]["triagem"] == "forte":
                        continue
                    achados[url] = dict(cod_ibge=m["cod6"], municipio=m["municipio"], uf=m["uf"], triagem=tri,
                                        tipo=tipo, data=(it.get("data_publicacao_pncp") or "")[:10],
                                        orgao=it.get("orgao_nome") or "", objeto=obj[:500],
                                        link=pncp_link(url), termo_busca=termo)
        if erros:   # NA ≠ 0: consulta que falhou não vira "zero achados"
            out.log(f"[PNCP {i}/{len(muns)}] {m['municipio']}/{m['uf']}: {erros} consultas falharam — NÃO marcado; rode de novo")
            continue
        out.grava("pncp_achados.csv", PNCP_COLS, sorted(achados.values(), key=lambda x: (x["triagem"] != "forte", x["data"])))
        out.marca("pncp", chave(m))
        nf = sum(1 for a in achados.values() if a["triagem"] == "forte")
        out.log(f"[PNCP {i}/{len(muns)}] {m['municipio']}/{m['uf']}: {len(achados)} achados ({nf} fortes)")


# ------------------------------------------------------------------ SAPL
SAPL_COLS = ["cod_ibge", "municipio", "uf", "triagem", "origem", "host", "tipo", "numero", "ano", "data", "ementa", "termo", "link_pdf"]


def ler_hosts():
    """Só hosts em que a descoberta de 09/09/2026 confirmou a API do SAPL
    (coluna api preenchida). Na rodada de 25/09, os demais devolveram 404 ou
    HTML — eram domínios da Câmara sem SAPL."""
    h = {}
    if SAPL_HOSTS.exists():
        with open(SAPL_HOSTS, encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                if r.get("host") and (r.get("api") or "").strip().lower() not in ("", "nao", "não", "0", "false"):
                    h[str(r["cod_ibge"])[:6]] = r
    return h


def sapl_casa(texto):
    for t in SAPL_TERMOS:
        if contem_frase(texto, t):
            return t
    return ""


def rodar_sapl(muns, http, out, descobrir=False):
    feitos = out.feitos("sapl")
    alvo = {m["cod6"]: m for m in muns if chave(m) not in feitos}
    if not alvo:
        return
    # 1) corpus offline
    no_corpus = set()
    if SAPL_CORPUS.exists():
        linhas = []
        with open(SAPL_CORPUS, encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                c6 = str(r.get("cod_ibge", ""))[:6]
                if c6 not in alvo:
                    continue
                no_corpus.add(c6)
                txt = (r.get("ementa") or "") + " " + (r.get("texto") or "")
                termo = sapl_casa(txt)
                if not termo:
                    continue
                m = alvo[c6]
                linhas.append(dict(cod_ibge=c6, municipio=m["municipio"], uf=m["uf"],
                                   triagem=triagem_texto(txt) or "citacao", origem="corpus 20/09/2026",
                                   host=r.get("host"), tipo=r.get("tipo"), numero=r.get("numero"), ano=r.get("ano"),
                                   data=r.get("data"), ementa=(r.get("ementa") or "")[:500], termo=termo,
                                   link_pdf=r.get("link_pdf")))
        out.grava("sapl_achados.csv", SAPL_COLS, linhas)
        out.log(f"[SAPL corpus] {len(no_corpus)} municípios da lista no corpus; {len(linhas)} normas casadas")
    # 2) ao vivo nos hosts conhecidos
    hosts = ler_hosts()
    for i, (c6, m) in enumerate(alvo.items(), 1):
        if c6 in no_corpus:
            out.marca("sapl", chave(m))
            continue
        host = (hosts.get(c6) or {}).get("host") or ""
        if not host and descobrir:
            host = descobrir_host(m, http, out)
        if not host:
            out.marca("sapl", chave(m))
            continue
        linhas, vistos, erros = [], set(), 0
        for termo in SAPL_TERMOS:
            url = f"https://{host}/api/norma/normajuridica/"
            for pag in range(1, 6):
                j, err = http.get_json(url, dict(ementa=termo, page=pag, page_size=100))
                if err or not isinstance(j, dict):
                    if err:
                        erros += 1
                        out.log(f"  SAPL {host} '{termo}': {err}")
                    break
            if erros and "Connection" in (err or "") and not linhas:
                erros = len(SAPL_TERMOS)   # host fora do ar: não insiste nos outros termos
                break
                res = j.get("results") or []
                for it in res:
                    txt = f"{it.get('ementa') or ''} {it.get('indexacao') or ''}"
                    if not contem_frase(txt, termo):
                        continue
                    k = (it.get("tipo"), it.get("numero"), it.get("ano"))
                    if k in vistos:
                        continue
                    vistos.add(k)
                    pdf = it.get("texto_integral") or ""
                    if pdf and pdf.startswith("/"):
                        pdf = f"https://{host}{pdf}"
                    linhas.append(dict(cod_ibge=c6, municipio=m["municipio"], uf=m["uf"],
                                       triagem=triagem_texto(txt) or "citacao", origem="api ao vivo", host=host,
                                       tipo=it.get("tipo"), numero=it.get("numero"), ano=it.get("ano"),
                                       data=it.get("data"), ementa=(it.get("ementa") or "")[:500], termo=termo, link_pdf=pdf))
                if not (j.get("pagination") or {}).get("links", {}).get("next") and not j.get("next"):
                    if len(res) < 100:
                        break
        if erros == len(SAPL_TERMOS):   # host inteiro falhou: não vira "zero normas"
            out.log(f"[SAPL {i}/{len(alvo)}] {m['municipio']}/{m['uf']} ({host}): todas as consultas falharam — NÃO marcado")
            continue
        out.grava("sapl_achados.csv", SAPL_COLS, linhas)
        out.marca("sapl", chave(m))
        out.log(f"[SAPL {i}/{len(alvo)}] {m['municipio']}/{m['uf']} ({host}): {len(linhas)} normas" + (f" ({erros} termos com erro)" if erros else ""))


def _slugs(municipio):
    p = limpa(municipio).replace("-", " ").split()
    prep = {"de", "do", "da", "dos", "das", "d"}
    v = ["".join(p), "-".join(p)]
    sem = [x for x in p if x not in prep]
    if sem != p:
        v += ["".join(sem), "-".join(sem)]
    return list(dict.fromkeys(x for x in v if x))


def descobrir_host(m, http, out):
    """Tenta sapl.<slug>.<uf>.leg.br e variantes. Não gera 'só a primeira
    palavra' (armadilha Vargem × Vargem Grande Paulista, 09/09/2026)."""
    uf = m["uf"].lower()
    for s in _slugs(m["municipio"]):
        for pref in ("sapl.", ""):
            for corpo in (s, "camara" + s, "cm" + s):
                host = f"{pref}{corpo}.{uf}.leg.br"
                try:
                    socket.setdefaulttimeout(3)
                    socket.getaddrinfo(host, 443)
                except Exception:
                    continue
                j, err = http.get_json(f"https://{host}/api/norma/normajuridica/", dict(page_size=1))
                if isinstance(j, dict) and ("results" in j or "pagination" in j):
                    out.log(f"  SAPL descoberto: {m['municipio']}/{m['uf']} → {host}")
                    return host
    return ""


# ------------------------------------------------------------------ Querido Diário
QD_COLS = ["cod_ibge", "municipio", "uf", "triagem", "data", "termo", "excerto", "link"]


def rodar_qd(muns, http, out, desde=None):
    feitos = out.feitos("qd")
    for i, m in enumerate(muns, 1):
        if chave(m) in feitos:
            continue
        if not m.get("cod7"):
            out.log(f"[QD] {m['municipio']}/{m['uf']}: sem código IBGE de 7 dígitos — pulado")
            out.marca("qd", chave(m))
            continue
        linhas, total_api, vistos, erros = [], 0, set(), 0
        for termo in QD_TERMOS:
            p = dict(territory_ids=m["cod7"], querystring=f'"{termo}"', excerpt_size=500,
                     number_of_excerpts=3, size=30, sort_by="descending_date")
            if desde:
                p["published_since"] = desde
            j, err = http.get_json(QD_API, p)
            if err:
                erros += 1
                out.log(f"  QD {m['municipio']}/{m['uf']} '{termo}': {err}")
                continue
            gz = (j or {}).get("gazettes") or []
            total_api += len(gz)
            for g in gz:
                for ex in g.get("excerpts") or []:
                    if not contem_frase(ex, termo):      # frase contígua obrigatória
                        continue
                    k = (g.get("date"), limpa(ex)[:80])
                    if k in vistos:
                        continue
                    vistos.add(k)
                    linhas.append(dict(cod_ibge=m["cod6"], municipio=m["municipio"], uf=m["uf"],
                                       triagem=triagem_texto(ex) or "citacao", data=g.get("date"), termo=termo,
                                       excerto=re.sub(r"\s+", " ", ex)[:600], link=g.get("url") or g.get("txt_url") or ""))
        if erros:
            out.log(f"[QD {i}/{len(muns)}] {m['municipio']}/{m['uf']}: {erros} consultas falharam — NÃO marcado; rode de novo")
            continue
        out.grava("qd_achados.csv", QD_COLS, linhas)
        out.marca("qd", chave(m))
        out.log(f"[QD {i}/{len(muns)}] {m['municipio']}/{m['uf']}: {total_api} diários devolvidos, {len(linhas)} excertos com a frase")


# ------------------------------------------------------------------ resumo
def ler_csv(p):
    if not p.exists():
        return []
    with open(p, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def resumo(muns, out):
    P = ler_csv(out.p / "pncp_achados.csv")
    S = ler_csv(out.p / "sapl_achados.csv")
    Q = ler_csv(out.p / "qd_achados.csv")
    # re-triagem com o filtro atual (a regra pode ter sido refinada depois da coleta)
    for L, campo in ((P, "objeto"), (S, "ementa"), (Q, "excerto")):
        for x in L:
            x["triagem"] = triagem_texto(x.get(campo, "")) or ("citacao" if L is not P else "")
    P = [x for x in P if x["triagem"]]
    hosts = ler_hosts()
    fp, fs, fq = (out.feitos(x) for x in ("pncp", "sapl", "qd"))
    rows = []
    ordem = {"forte": 0, "medio": 1, "citacao": 2}
    for m in muns:
        c6 = m["cod6"]
        p = sorted([x for x in P if x["cod_ibge"] == c6], key=lambda x: (ordem.get(x["triagem"], 9), x["data"][::-1]))
        s = sorted([x for x in S if x["cod_ibge"] == c6], key=lambda x: (ordem.get(x["triagem"], 9), -(int(x["ano"] or 0))))
        q = sorted([x for x in Q if x["cod_ibge"] == c6], key=lambda x: (ordem.get(x["triagem"], 9), x["data"][::-1]))
        tri = [x["triagem"] for x in p + s + q]
        cob = []
        if chave(m) in fp: cob.append("PNCP")
        if chave(m) in fs and (hosts.get(c6) or any(x["cod_ibge"] == c6 for x in S)): cob.append("SAPL")
        if chave(m) in fq and m.get("cod7"): cob.append("QD")
        t = "forte" if "forte" in tri else ("medio" if "medio" in tri else ("nada" if cob else "nao consultado"))  # citação sozinha não é indício
        best = lambda L, f: (f(L[0]) if L else "")
        rows.append({
            "Município": m["municipio"], "UF": m["uf"], "Código IBGE": m["cod7"] or c6,
            "MUNIC 2020 — regulamentação": m.get("munic_regulacao") or "",
            "Triagem (não é classificação)": t,
            "Fontes com cobertura": ", ".join(cob) or "nenhuma",
            "PNCP — achados (fortes)": f"{len(p)} ({sum(1 for x in p if x['triagem']=='forte')})",
            "PNCP — melhor": best(p, lambda x: f"[{x['triagem']}] {x['data']} {x['objeto'][:180]} {x['link']}"),
            "SAPL — normas (fortes)": f"{len(s)} ({sum(1 for x in s if x['triagem']=='forte')})",
            "SAPL — melhor": best(s, lambda x: f"[{x['triagem']}] tipo {x['tipo']} {x['numero']}/{x['ano']}: {x['ementa'][:180]} {x['link_pdf']}"),
            "QD — excertos (fortes)": f"{len(q)} ({sum(1 for x in q if x['triagem']=='forte')})",
            "QD — melhor": best(q, lambda x: f"[{x['triagem']}] {x['data']} “{x['excerto'][:220]}” {x['link']}"),
            "Próximo passo": {"forte": "ler o documento (norma/contrato) e a notícia de operação — A.2(c)",
                              "medio": "serviço existe; procurar regra de acesso (norma, TR, notícia)",
                              "nada": "sem achado nas fontes com cobertura — site da Prefeitura / e-SIC",
                              "nao consultado": "rodar as fontes (ou a consulta falhou)"}[t],
        })
    cols = list(rows[0].keys()) if rows else []
    with open(out.p / "resumo.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Resumo"
        ws.append(cols)
        for c in ws[1]:
            c.font = Font(bold=True)
        cor = {"forte": "C6EFCE", "medio": "FFEB9C", "nada": "EDEDED", "nao consultado": "FFFFFF"}
        for r in sorted(rows, key=lambda r: {"forte": 0, "medio": 1, "nada": 2, "nao consultado": 3}[r["Triagem (não é classificação)"]]):
            ws.append([r[c] for c in cols])
            ws.cell(ws.max_row, 5).fill = PatternFill("solid", fgColor=cor[r["Triagem (não é classificação)"]])
        leia = wb.create_sheet("Leia-me")
        for l in [
            "Busca ativa dos municípios que declaram TZ à MUNIC 2020 e estão fora da base canônica.",
            f"Gerado em {dt.datetime.now():%d/%m/%Y %H:%M} por _meta/scripts/buscar_munic_fora_canonico.py.",
            "Autor: Thiago Von Zeidler Gomes · Orientadora: Prof.ª Dra. Silvana Zioni",
            "Triagem NÃO é classificação: 'forte' pede leitura humana do documento (Regras, A.2 e A.2c).",
            "'nada' não significa ausência de TZ: ver a coluna de cobertura (NA ≠ 0).",
            "QD: só entram excertos com a frase contígua (a querystring do QD é frouxa).",
            "SAPL: só leis da Câmara; decretos do Executivo não estão lá.",
            "PNCP: só a partir de 04/2021; filtra município/UF e o objeto da contratação.",
        ]:
            leia.append([l])
        wb.save(out.p / "resumo.xlsx")
    except Exception as e:
        out.log(f"resumo.xlsx não gerado ({e}); resumo.csv gravado")
    n = {k: sum(1 for r in rows if r["Triagem (não é classificação)"] == k) for k in ("forte", "medio", "nada", "nao consultado")}
    out.log(f"RESUMO: {len(rows)} municípios · forte {n['forte']} · médio {n['medio']} · nada {n['nada']} · não consultado {n['nao consultado']}")


# ------------------------------------------------------------------ autoteste
def autoteste():
    ok = True
    def t(nome, got, exp):
        nonlocal ok
        r = "ok" if got == exp else "FALHOU"
        ok &= got == exp
        print(f"{r:6} {nome}: {got!r} (esperado {exp!r})")
    t("frase contígua", contem_frase("Institui o Passe-Livre no transporte", "passe livre"), True)
    t("palavras soltas não casam", contem_frase("passe de ônibus livre", "passe livre"), False)
    t("acento", contem_frase("TRANSPORTE COLETIVO GRATUÍTO", "transporte coletivo gratuito"), True)
    t("objeto forte", triagem_texto("Locação de ônibus para o transporte coletivo municipal urbano gratuito"), "forte")
    t("objeto médio", triagem_texto("Prestação de serviço de transporte coletivo urbano de passageiros"), "medio")
    t("escolar fora", triagem_texto("Transporte escolar de alunos da rede municipal"), "")
    t("distribuição gratuita fora", triagem_texto("Aquisição de cestas básicas para distribuição gratuita"), "")
    t("curso de condutor fora", triagem_texto("Curso de formação de condutores de transporte coletivo"), "")
    t("tarifa zero forte", triagem_texto("Concessão do sistema de transporte coletivo 'Tarifa Zero'"), "forte")
    t("link edital", pncp_link("/compras/16780795000138/2025/27"), "https://pncp.gov.br/app/editais/16780795000138/2025/27")
    t("link contrato", pncp_link("/contratos/76022490000199/2024/16"), "https://pncp.gov.br/app/contratos/76022490000199/2024/16")
    t("slugs sem 1ª palavra", "vargem" in _slugs("Vargem Grande Paulista"), False)
    t("abrigo fora", triagem_texto("Fornecimento de abrigos de passageiros do transporte coletivo urbano"), "")
    t("ofício circular fora", triagem_texto("Altera a Lei Orgânica em atendimento ao ofício circular do TCE"), "")
    t("passagens fora", triagem_texto("Aquisição de passagens de ônibus para vereadores"), "")
    t("popular tarifa zero forte", triagem_texto("serviço de transporte de passageiros nas linhas do transporte popular tarifa zero"), "forte")
    print("\nTODOS OK" if ok else "\nHÁ FALHAS")
    return ok


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("comando", choices=["rodar", "resumo", "autoteste"])
    ap.add_argument("--fontes", default="pncp,sapl,qd")
    ap.add_argument("--csv")
    ap.add_argument("--limite", type=int)
    ap.add_argument("--delay", type=float, default=1.0)
    ap.add_argument("--saida", default=str(AQUI / f"saida_munic_fora_{dt.date.today():%Y-%m-%d}"))
    ap.add_argument("--recomecar", action="store_true")
    ap.add_argument("--descobrir", action="store_true", help="SAPL: tentar achar host para quem não tem")
    ap.add_argument("--desde", help="QD: published_since (AAAA-MM-DD)")
    a = ap.parse_args()
    if a.comando == "autoteste":
        sys.exit(0 if autoteste() else 1)
    muns = ler_lista(a)
    out = Saida(a.saida, a.recomecar)
    out.log(f"== {a.comando} · {len(muns)} municípios · fontes {a.fontes} · saída {out.p}")
    if a.comando == "rodar":
        http = Http(delay=a.delay)
        fontes = [x.strip() for x in a.fontes.split(",")]
        if "pncp" in fontes:
            rodar_pncp(muns, http, out)
        if "sapl" in fontes:
            rodar_sapl(muns, http, out, descobrir=a.descobrir)
        if "qd" in fontes:
            rodar_qd(muns, http, out, desde=a.desde)
    resumo(muns, out)


if __name__ == "__main__":
    main()
