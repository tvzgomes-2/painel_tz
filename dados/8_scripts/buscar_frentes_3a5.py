#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
buscar_frentes_3a5.py — frentes 3, 4 e 5 da busca automatizada (25/09/2026), para rodar no terminal do autor
(PNCP e Siconfi recusam conexão das máquinas do Claude; o terminal do autor alcança os dois).

  Frente 3 — PNCP: contratos e editais de transporte coletivo de cada município da base-mestre
             (escopo + pistas) → fornecedor, CNPJ, vigência, valor, gratuidade escrita no objeto.
  Frente 4 — Siconfi (DCA Anexo I-E): despesa municipal por função/subfunção, por ano →
             função 26 (Transporte), subfunção 26.453 (Transporte Coletivo Urbano) e total.
  Frente 5 — Querido Diário: excertos com "tarifa zero", "passe livre", "transporte gratuito"… nos casos
             ABERTOS (Situação unificada ≠ Fechado).

USO (na pasta _meta/scripts):
  python buscar_frentes_3a5.py autoteste                  # testa as regras, sem rede
  python buscar_frentes_3a5.py rodar --limite 3           # ensaio com 3 municípios, todas as frentes
  python buscar_frentes_3a5.py rodar                      # tudo (horas: deixe rodando; retoma de onde parou)
  python buscar_frentes_3a5.py rodar --frentes 3          # só PNCP  (ou 4, ou 5, ou 3,4)
  python buscar_frentes_3a5.py resumo                     # só refaz o resumo.xlsx
  python buscar_frentes_3a5.py status                     # 28/09/2026: o que falta em cada frente, sem rede
  Opções: --anos 2017-2025 (Siconfi) · --delay 1.0 · --saida <pasta> · --recomecar · --abertos (frente 3 só nos abertos)
          --siconfi-refazer (apaga e refaz o Siconfi inteiro; normalmente desnecessário)

v4 (30/09/2026) — universo ampliado (--universo, combinável por vírgula; padrão 'base', que é o comportamento de antes):
  base     escopo da base-mestre + pistas da mestre (como até a v3)
  pistas   pistas fora do canônico: 'Pista' e 'Regulamentada — não implantada' da mestre + os municípios que declaram TZ
           à MUNIC 2020 e estão fora da base (aba 'MUNIC declara TZ — fora'), menos os que já entraram no escopo
  camada2  aba '2 Parcial' da régua; por padrão só os municípios com 2a, 2b ou 2c (37 em 30/09/2026) —
           --com-2d inclui também os que só têm 2d eleitoral/evento (mais ~300, rodada de muitas horas)
  camada3  aba '3 Encerradas' da régua
  No universo ampliado todos os municípios entram na frente 5 (Querido Diário), e a saída vai para
  saida_frentes_3a5_ampliado/ (pasta própria, que também retoma de onde parou), para não misturar com a base.
  Exemplos:  python buscar_frentes_3a5.py rodar --universo pistas,camada2,camada3
             python buscar_frentes_3a5.py status --universo pistas,camada2,camada3
             python buscar_frentes_3a5.py rodar --universo camada2 --com-2d

v3 (28/09/2026):
  - Siconfi não roda de novo o que já está no checkpoint: só municípios/anos novos e, a cada 30 dias, os anos recentes
    que estavam 'sem DCA publicado' (o ente pode entregar ou retificar depois — NA não é definitivo). Sem pendência, uma linha só.
  - Querido Diário: checkpoint por termo (uma queda não refaz os 7 termos) e disjuntor — com 12 falhas seguidas pausa 5 min;
    se continuar fora do ar, interrompe a frente 5 em vez de passar horas colecionando HTTP 503.
  - PNCP: disjuntor (depois de 2 pausas de 3 min sem nenhum município completo, interrompe a frente 3) e repescagem automática
    dos municípios com consulta pendente ao fim da passada, com sessão nova.
  - Ao fim de 'rodar', imprime o 'status' (o que ficou pendente e o comando para retomar).

Saída: _meta/scripts/saida_frentes_3a5_AAAA-MM-DD/ — pncp_contratos.csv, siconfi_despesa.csv, qd_achados.csv,
resumo.xlsx, log.txt e checkpoints _feito_*.txt. NA ≠ 0: consulta que falha NÃO é marcada como feita; rode de novo.
Dependências: requests, openpyxl (pip install requests openpyxl). Read-only sobre o cofre.
Autor: Thiago Von Zeidler Gomes · Orientadora: Prof.ª Dra. Silvana Zioni
"""
import argparse, csv, datetime as dt, re, sys
import openpyxl
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
import buscar_munic_fora_canonico as bm   # reaproveita Http, Saida, filtros e o Querido Diário

COFRE = AQUI.parent.parent
MESTRE = COFRE / "03 - Dados" / "_data" / "casos por fonte" / "Municípios TZ - consolidado.xlsx"
PNCP_API = "https://pncp.gov.br/pncp-api/v1/orgaos"
SICONFI = "https://apidatalake.tesouro.gov.br/ords/cdwhprd/siconfi/tt/dca"  # 28/09/2026: base mudou para /ords/cdwhprd/siconfi/tt/ (docs/siconfi); o endereço antigo /ossiconfi/tt/ devolve 404 em todos os entes
TERMOS3 = ["transporte coletivo", "tarifa zero", "onibus", "transporte publico"]
TIPOS3 = ["contrato", "edital"]
HOJE = dt.date.today()

# ------------------------------------------------------------------ entrada: base-mestre
def ler_base(args):
    import openpyxl
    ibge7 = bm.ler_ibge7()
    ws = openpyxl.load_workbook(MESTRE, read_only=True, data_only=True)["consolidado"]
    it = ws.iter_rows(values_only=True); h = [str(x) for x in next(it)]
    ix = {k: i for i, k in enumerate(h)}
    out, vistos = [], set()
    for r in it:
        sit = str(r[ix["Situação"]] or "") if r and r[0] else ""
        cod = re.sub(r"\D", "", str(r[ix["Código IBGE"]] or ""))[:7]
        cod6 = cod[:6]
        if sit in ("Ativa", "Encerrada"): ESCOPO6.add((cod6, r[ix["UF"]]))
        if sit.startswith("Regulamentada") and "pistas" in str(getattr(args, "universo", "")):
            out.append(dict(municipio=r[0], uf=r[ix["UF"]], cod6=cod6, cod7=cod if len(cod) == 7 else ibge7.get(cod6, ""), aberto=True, situacao="Pista"))
            continue
        if sit not in ("Ativa", "Encerrada", "Pista (a verificar)"): continue
        k = (cod6, r[ix["UF"]])
        if k in vistos: continue
        vistos.add(k)
        out.append(dict(municipio=r[0], uf=r[ix["UF"]], cod6=cod6, cod7=cod if len(cod) == 7 else ibge7.get(cod6, ""),
                        aberto=str(r[ix["Situação unificada (controle)"]] or "") != "Fechado",
                        situacao="Pista" if sit.startswith("Pista") else sit))
    uni = set((getattr(args, "universo", "base") or "base").split(","))
    if uni != {"base"}:
        out = ([m for m in out if m["situacao"] == "Pista"] if "pistas" in uni else [])
        vistos = {(m["cod6"], m["uf"]) for m in out}
        escopo6 = {k for k in ESCOPO6}
        def junta(lst, rotulo):
            for m in lst:
                k = (m["cod6"], m["uf"])
                if not m["cod6"] or k in vistos: continue
                vistos.add(k); m["aberto"] = True; m["universo"] = rotulo; out.append(m)
        if "pistas" in uni:
            class _A: csv = None; limite = None
            try:
                munic = bm.ler_lista(_A())
                junta([dict(municipio=m["municipio"], uf=m["uf"], cod6=m["cod6"], cod7=m.get("cod7", "")) for m in munic
                       if (m["cod6"], m["uf"]) not in escopo6], "pista — MUNIC fora da base")
            except Exception as e:
                print(f"aviso: lista MUNIC fora da base não lida ({e})")
        if "camada2" in uni or "camada3" in uni:
            wr = openpyxl.load_workbook(REGUA, read_only=True, data_only=True)
            nome7 = ler_nome_ibge()
            def da_aba(aba, filtro=None):
                rows = list(wr[aba].iter_rows(values_only=True)); sub = {}
                for r in rows[1:]:
                    if r and r[0]: sub.setdefault((str(r[0]).strip(), str(r[1]).strip()), set()).add(str(r[2] or "").strip())
                lst, falta = [], []
                for (mu, uf), ss in sub.items():
                    if filtro and not filtro(ss): continue
                    c7 = nome7.get((chave_nome(mu), uf), "")
                    if not c7: falta.append(f"{mu}/{uf}"); continue
                    lst.append(dict(municipio=mu, uf=uf, cod6=c7[:6], cod7=c7))
                if falta: print(f"aviso: {len(falta)} municípios da aba '{aba}' sem código IBGE pelo nome: {', '.join(falta[:15])}")
                return lst
            if "camada2" in uni:
                com2d = getattr(args, "com_2d", False)
                junta(da_aba("2 Parcial", None if com2d else (lambda ss: bool(ss - {"2d", ""}))), "camada 2")
            if "camada3" in uni: junta(da_aba("3 Encerradas"), "camada 3")
        for m in out: m.setdefault("universo", "pista (base-mestre)"); m["aberto"] = True
    if args.limite: out = out[: args.limite]
    return out

UNIV = "base"
REGUA = COFRE / "03 - Dados" / "_data" / "casos por fonte" / "Tipologias TZ - consolidado.xlsx"
ESCOPO6 = set()

def chave_nome(s):
    return re.sub(r"[^a-z0-9]", "", bm.nfd(str(s)).lower())

def ler_nome_ibge():
    m = {}
    if bm.IBGE_CSV.exists():
        with open(bm.IBGE_CSV, encoding="utf-8-sig") as f:
            for r in csv.DictReader(f): m[(chave_nome(r["municipio"]), r["uf"])] = str(r["cod_ibge"])
    for (nome, uf), alvo in ALIAS_IBGE.items():   # grafias da régua que diferem da tabela do IBGE usada aqui
        if (chave_nome(alvo), uf) in m: m[(chave_nome(nome), uf)] = m[(chave_nome(alvo), uf)]
    return m

ALIAS_IBGE = {("Embu das Artes", "SP"): "Embu", ("São Luiz do Paraitinga", "SP"): "São Luís Do Paraitinga"}

# ------------------------------------------------------------------ frente 3: PNCP
C3 = ["cod_ibge", "municipio", "uf", "fonte", "orgao_cnpj", "ano", "seq", "numero", "data_publicacao", "objeto",
      "fornecedor", "cnpj_fornecedor", "vigencia_inicio", "vigencia_fim", "valor", "situacao",
      "gratuidade_escrita", "vigente_hoje", "link"]

def partes_url(item_url):
    p = (item_url or "").strip("/").split("/")
    return (p[0], p[1], p[2], p[3]) if len(p) == 4 and p[0] in ("compras", "contratos", "atas") else None

def vigente(fim):
    try: return "sim" if dt.date.fromisoformat(str(fim)[:10]) >= HOJE else "não"
    except ValueError: return ""

RE_OBRA = re.compile(r"construcao|obra(s)? de|engenharia|reforma|estacao de onibus|terminal rodoviario|pavimenta|asfalt|cobertura metalica")

def eh_transporte(obj):
    t = bm.limpa(obj)   # ensaio de 25/09: "construção da estação de ônibus" entrava como contrato de transporte
    return bool(bm.RE_COLET.search(t)) and not bm.RE_EXCLUI.search(t) and not RE_OBRA.search(t)

def fmt_cnpj(s):
    d = re.sub(r"\D", "", str(s or ""))
    return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}" if len(d) == 14 else (s or "")

MAX_FALHAS = 3      # por município: com 3 falhas, desiste dele nesta rodada (fica para a próxima) — evita 50 min presos num só
PAUSA_FALHA = 20    # segundos de espera depois de uma queda de conexão, para o PNCP se recuperar
PNCP_MAX_PAUSAS = 2  # 28/09/2026: depois de 2 pausas seguidas sem nenhum município completo, a frente 3 para (PNCP instável)
QD_FALHAS_SEGUIDAS = 12   # 28/09/2026: consultas seguidas com erro que disparam a pausa longa do Querido Diário
QD_PAUSA = 300            # segundos
SEMDCA_RETENTAR_DIAS = 30  # 28/09/2026: 'sem DCA publicado' em ano recente é reconsultado a cada 30 dias
SEMDCA_ANOS_RECENTES = 2   # ... só para os 2 últimos exercícios (os antigos não mudam mais)

def rodar_pncp(muns, http, out, repescar=True):
    import time
    feitos = out.feitos("pncp3")
    feitos_q = out.feitos("pncp3q")   # 26/09/2026: checkpoint por consulta (município|termo|tipo) — uma queda não joga fora as consultas que deram certo
    ja = set()                        # documentos já gravados em rodadas anteriores (evita duplicar ao refazer consultas)
    arq = out.p / "pncp_contratos.csv"
    if arq.exists():
        with open(arq, encoding="utf-8-sig") as fh:
            for r in csv.DictReader(fh):
                ja.add((f"{r.get('fonte', '')}s", r.get("orgao_cnpj", ""), r.get("ano", ""), r.get("seq", "")))
    seguidos = 0   # 26/09/2026: municípios seguidos com falha; a partir de 3, pausa longa para o PNCP esfriar
    pausas = 0     # 28/09/2026: pausas seguidas sem nenhum município completo no meio
    for i, m in enumerate(muns, 1):
        if bm.chave(m) in feitos: continue
        if seguidos >= 3:
            if pausas >= PNCP_MAX_PAUSAS:
                out.log(f"  PNCP instável: {seguidos} municípios seguidos com falha depois de {pausas} pausas — frente 3 interrompida. "
                        "O que ficou pendente está no checkpoint; retome com: python buscar_frentes_3a5.py rodar --frentes 3"); return
            pausas += 1
            out.log(f"  {seguidos} municípios seguidos com falha — pausa de 3 min ({pausas}/{PNCP_MAX_PAUSAS})"); time.sleep(180); seguidos = 0
        vistos, erros, n_docs, n_contr, pendentes = set(), 0, 0, 0, 0
        for termo in TERMOS3:
            for tipo in TIPOS3:
                qk = f"{bm.chave(m)}|{termo}|{tipo}"
                if qk in feitos_q: continue
                if erros >= MAX_FALHAS: pendentes += 1; continue
                erros_q, linhas_q = 0, []
                j, err = http.get_json(bm.PNCP_SEARCH, dict(q=f"{m['municipio']} {termo}", tipos_documento=tipo, ordenacao="-data",
                                                            pagina=1, tam_pagina=50, status="todos"))
                if err:
                    erros += 1; pendentes += 1; out.log(f"  PNCP {m['municipio']}/{m['uf']} '{termo}' {tipo}: {err}"); time.sleep(PAUSA_FALHA); continue
                for it in (j or {}).get("items", []):
                    if bm.limpa(it.get("municipio_nome")) != bm.limpa(m["municipio"]) or (it.get("uf") or "") != m["uf"]: continue
                    obj = it.get("description") or it.get("title") or ""
                    if not eh_transporte(obj): continue
                    pu = partes_url(it.get("item_url"))
                    if not pu or pu in vistos or pu in ja: continue
                    vistos.add(pu)
                    fonte, cnpj, ano, seq = pu
                    base = dict(cod_ibge=m["cod6"], municipio=m["municipio"], uf=m["uf"], fonte=fonte[:-1], orgao_cnpj=cnpj, ano=ano, seq=seq,
                                data_publicacao=(it.get("data_publicacao_pncp") or "")[:10], objeto=obj[:600], link=bm.pncp_link(it.get("item_url")))
                    if fonte == "contratos":
                        d, e2 = http.get_json(f"{PNCP_API}/{cnpj}/contratos/{ano}/{seq}")
                        if e2: erros += 1; erros_q += 1; out.log(f"  contrato {cnpj}/{ano}/{seq}: {e2}"); continue
                        d = d or {}
                        txt = " ".join(str(d.get(k) or "") for k in ("objetoContrato", "informacaoComplementar")) or obj
                        base.update(numero=d.get("numeroContratoEmpenho") or "", fornecedor=d.get("nomeRazaoSocialFornecedor") or "",
                                    cnpj_fornecedor=fmt_cnpj(d.get("niFornecedor")), vigencia_inicio=d.get("dataVigenciaInicio") or "",
                                    vigencia_fim=d.get("dataVigenciaFim") or "", valor=d.get("valorGlobal") or "",
                                    gratuidade_escrita="sim" if bm.RE_GRAT.search(bm.limpa(txt)) else "",
                                    vigente_hoje=vigente(d.get("dataVigenciaFim")))
                        linhas_q.append(base)
                    else:
                        its, e2 = http.get_json(f"{PNCP_API}/{cnpj}/{fonte}/{ano}/{seq}/itens")
                        if e2: erros += 1; erros_q += 1; out.log(f"  itens {cnpj}/{ano}/{seq}: {e2}"); continue
                        forn = []
                        for item in (its or [])[:3]:
                            rs, e3 = http.get_json(f"{PNCP_API}/{cnpj}/{fonte}/{ano}/{seq}/itens/{item.get('numeroItem')}/resultados")
                            if e3 and "404" not in e3: erros += 1; erros_q += 1; out.log(f"  resultados {cnpj}/{ano}/{seq} item {item.get('numeroItem')}: {e3}"); continue
                            for r in rs or []:
                                forn.append((r.get("nomeRazaoSocialFornecedor") or "", fmt_cnpj(r.get("niFornecedor")), r.get("valorTotalHomologado") or ""))
                        sit = "; ".join(sorted({str(x.get("situacaoCompraItemNome") or "") for x in (its or [])}))
                        base.update(numero=it.get("numero_controle_pncp") or "", situacao=sit,
                                    fornecedor=" | ".join(sorted({f[0] for f in forn if f[0]})), cnpj_fornecedor=" | ".join(sorted({f[1] for f in forn if f[1]})),
                                    valor=sum(float(f[2]) for f in forn if f[2]) if forn else "",
                                    gratuidade_escrita="sim" if bm.RE_GRAT.search(bm.limpa(obj)) else "")
                        linhas_q.append(base)
                if erros_q:
                    pendentes += 1; continue   # consulta incompleta: não grava nem marca; refaz na próxima rodada
                out.grava("pncp_contratos.csv", C3, linhas_q); out.marca("pncp3q", qk)
                for l in linhas_q:
                    ja.add((l["fonte"] + "s", l["orgao_cnpj"], l["ano"], l["seq"]))
                n_docs += len(linhas_q); n_contr += sum(1 for l in linhas_q if l["fonte"] == "contrato")
        if pendentes:
            seguidos += 1
            out.log(f"[PNCP {i}/{len(muns)}] {m['municipio']}/{m['uf']}: {pendentes} de {len(TERMOS3) * len(TIPOS3)} consultas pendentes ({n_docs} documentos gravados) — NÃO marcado; rode de novo"); continue
        out.marca("pncp3", bm.chave(m))
        seguidos = 0; pausas = 0
        out.log(f"[PNCP {i}/{len(muns)}] {m['municipio']}/{m['uf']}: completo nesta rodada ({n_docs} documentos novos, {n_contr} contratos)")
    if repescar:   # 28/09/2026: as quedas do PNCP são intermitentes; uma segunda passada curta fecha a maioria das consultas pendentes
        f = out.feitos("pncp3"); resto = [m for m in muns if bm.chave(m) not in f]
        if resto:
            out.log(f"[PNCP] repescagem: {len(resto)} municípios com consulta pendente — nova passada em 2 min, com sessão nova")
            time.sleep(120); http._nova_sessao(); rodar_pncp(resto, http, out, repescar=False)

# ------------------------------------------------------------------ frente 4: Siconfi
C4 = ["cod_ibge", "municipio", "uf", "ano", "cod_conta", "conta", "coluna", "valor"]
RE_CONTA = re.compile(r"^(26(\.\d+)?|\d{2}\.453|Despesas Exceto Intra|Total Geral da Despesa|Despesas Intra)", re.I)  # 28/09/2026: a subfunção 453 aparece sob a função lançada pela prefeitura (ex.: 15.453 em Luziânia/GO), não só 26.453

def conta_relevante(conta):
    return bool(RE_CONTA.search(str(conta or "").strip()))

def rodar_siconfi(muns, http, out, anos):
    """28/09/2026 (v3): consulta só o que falta. O DCA de um exercício fechado não muda, então município/ano já no checkpoint
    não é consultado de novo; a exceção é 'sem DCA publicado' nos 2 últimos exercícios, reconsultado a cada 30 dias."""
    feitos = out.feitos("siconfi")
    reais, semdca = set(), set()
    arq = out.p / "siconfi_despesa.csv"
    if arq.exists():
        for r in bm.ler_csv(arq):
            (semdca if r.get("conta") == "(sem DCA publicado)" else reais).add((r.get("cod_ibge"), r.get("ano")))
    ft = out.p / "_siconfi_semdca_tentativas.txt"
    tent = {}
    if ft.exists():
        for l in ft.read_text(encoding="utf-8").splitlines():
            if "|" in l: k, d = l.rsplit("|", 1); tent[k] = d
    def vencido(k):
        try: return (HOJE - dt.date.fromisoformat(tent[k])).days >= SEMDCA_RETENTAR_DIAS
        except (KeyError, ValueError): return True
    fila, sem7 = [], 0
    for m in muns:
        if not m["cod7"]: sem7 += 1; continue
        for ano in anos:
            k = f"{bm.chave(m)}|{ano}"
            if k not in feitos: fila.append((m, ano, k, False))
            elif ((m["cod7"], ano) in semdca and (m["cod7"], ano) not in reais and int(ano) >= HOJE.year - SEMDCA_ANOS_RECENTES and vencido(k)):
                fila.append((m, ano, k, True))
    if sem7: out.log(f"[Siconfi] {sem7} municípios sem IBGE de 7 dígitos — pulados")
    if not fila:
        out.log(f"[Siconfi] nada a consultar: {len(muns) - sem7} municípios × {len(anos)} anos já no checkpoint "
                f"('sem DCA' dos {SEMDCA_ANOS_RECENTES} últimos exercícios volta a ser consultado a cada {SEMDCA_RETENTAR_DIAS} dias)"); return
    n_re = sum(1 for x in fila if x[3])
    out.log(f"[Siconfi] {len(fila)} consultas a fazer ({len(fila) - n_re} novas, {n_re} reconsultas de 'sem DCA' recente)")
    por_mun = {}
    for m, ano, k, re_ in fila: por_mun.setdefault(bm.chave(m), (m, []))[1].append((ano, k, re_))
    for i, (ch, (m, itens)) in enumerate(por_mun.items(), 1):
        falhas, chegou = 0, 0
        for ano, k, re_ in itens:
            linhas, offset, erro, n = [], 0, "", 0
            while True:
                j, err = http.get_json(SICONFI, dict(an_exercicio=ano, no_anexo="DCA-Anexo I-E", id_ente=m["cod7"], offset=offset))
                if err: erro = err; break
                itens_api = (j or {}).get("items", [])
                n += len(itens_api)
                for x in itens_api:
                    if conta_relevante(x.get("conta")):
                        linhas.append(dict(cod_ibge=m["cod7"], municipio=m["municipio"], uf=m["uf"], ano=ano, cod_conta=x.get("cod_conta"),
                                           conta=x.get("conta"), coluna=x.get("coluna"), valor=x.get("valor")))
                if not (j or {}).get("hasMore"): break
                offset += len(itens_api) or 5000
            if erro:
                falhas += 1; out.log(f"  Siconfi {m['municipio']}/{m['uf']} {ano}: {erro} — NÃO marcado"); continue
            if re_:   # reconsulta: grava só se o DCA apareceu; em qualquer caso registra a data da tentativa
                with open(ft, "a", encoding="utf-8") as fh: fh.write(f"{k}|{HOJE.isoformat()}\n")
                if n: out.grava("siconfi_despesa.csv", C4, linhas); chegou += 1
                continue
            if n == 0:   # DCA não entregue ou não publicado: registra como NA, não como zero
                linhas = [dict(cod_ibge=m["cod7"], municipio=m["municipio"], uf=m["uf"], ano=ano, conta="(sem DCA publicado)", coluna="", valor="")]
            out.grava("siconfi_despesa.csv", C4, linhas); out.marca("siconfi", k)
        anos_txt = ", ".join(a for a, _, _ in itens)
        out.log(f"[Siconfi {i}/{len(por_mun)}] {m['municipio']}/{m['uf']}: {anos_txt}" + (f" · {falhas} falhas (fica para a próxima)" if falhas else "")
                + (f" · DCA novo em {chegou} ano(s) antes 'sem DCA'" if chegou else ""))

# ------------------------------------------------------------------ frente 5: Querido Diário (v3, 28/09/2026)
def rodar_qd(muns, http, out, desde=None):
    """Como bm.rodar_qd, mais: checkpoint por termo (_feito_qdq.txt) e disjuntor para quedas longas da API (HTTP 503 em série)."""
    import time
    feitos, feitos_q = out.feitos("qd"), out.feitos("qdq")
    ja = set()
    arq = out.p / "qd_achados.csv"
    if arq.exists():
        for r in bm.ler_csv(arq): ja.add((r.get("cod_ibge"), r.get("data"), bm.limpa(r.get("excerto", ""))[:80]))
    seguidas, pausou = 0, False
    for i, m in enumerate(muns, 1):
        if bm.chave(m) in feitos: continue
        if not m.get("cod7"):
            out.log(f"[QD] {m['municipio']}/{m['uf']}: sem código IBGE de 7 dígitos — pulado"); out.marca("qd", bm.chave(m)); continue
        total, erros, n_lin = 0, 0, 0
        for termo in bm.QD_TERMOS:
            qk = f"{bm.chave(m)}|{termo}"
            if qk in feitos_q: continue
            if seguidas >= QD_FALHAS_SEGUIDAS:
                if pausou:
                    resto = sum(1 for x in muns if bm.chave(x) not in out.feitos("qd"))
                    out.log(f"  Querido Diário fora do ar ({seguidas} falhas seguidas, também depois da pausa) — frente 5 interrompida; "
                            f"{resto} municípios ficam para depois: python buscar_frentes_3a5.py rodar --frentes 5"); return
                out.log(f"  Querido Diário: {seguidas} falhas seguidas — pausa de {QD_PAUSA // 60} min antes de testar de novo")
                time.sleep(QD_PAUSA); http._nova_sessao(); pausou = True; seguidas = QD_FALHAS_SEGUIDAS - 1
            p = dict(territory_ids=m["cod7"], querystring=f'"{termo}"', excerpt_size=500, number_of_excerpts=3, size=30, sort_by="descending_date")
            if desde: p["published_since"] = desde
            j, err = http.get_json(bm.QD_API, p)
            if err:
                erros += 1; seguidas += 1; out.log(f"  QD {m['municipio']}/{m['uf']} '{termo}': {err}"); continue
            seguidas, pausou = 0, False
            gz = (j or {}).get("gazettes") or []
            total += len(gz); linhas = []
            for g in gz:
                for ex in g.get("excerpts") or []:
                    if not bm.contem_frase(ex, termo): continue   # frase contígua obrigatória
                    k = (m["cod6"], g.get("date"), bm.limpa(ex)[:80])
                    if k in ja: continue
                    ja.add(k)
                    linhas.append(dict(cod_ibge=m["cod6"], municipio=m["municipio"], uf=m["uf"], triagem=bm.triagem_texto(ex) or "citacao",
                                       data=g.get("date"), termo=termo, excerto=re.sub(r"\s+", " ", ex)[:600], link=g.get("url") or g.get("txt_url") or ""))
            out.grava("qd_achados.csv", bm.QD_COLS, linhas); out.marca("qdq", qk); n_lin += len(linhas)
        if erros:
            out.log(f"[QD {i}/{len(muns)}] {m['municipio']}/{m['uf']}: {erros} termos falharam (os demais ficaram gravados) — NÃO marcado; rode de novo"); continue
        out.marca("qd", bm.chave(m))
        out.log(f"[QD {i}/{len(muns)}] {m['municipio']}/{m['uf']}: {total} diários devolvidos nesta rodada, {n_lin} excertos novos com a frase")

# ------------------------------------------------------------------ status (28/09/2026)
def status(muns, out, anos):
    f3, q3, f4, f5, q5 = out.feitos("pncp3"), out.feitos("pncp3q"), out.feitos("siconfi"), out.feitos("qd"), out.feitos("qdq")
    p3 = [m for m in muns if bm.chave(m) not in f3]
    pq3 = sum(1 for m in p3 for t in TERMOS3 for tp in TIPOS3 if f"{bm.chave(m)}|{t}|{tp}" not in q3)
    p4 = sum(1 for m in muns if m["cod7"] for a in anos if f"{bm.chave(m)}|{a}" not in f4)
    ab = [m for m in muns if m["aberto"]]; p5 = [m for m in ab if bm.chave(m) not in f5]
    pq5 = sum(1 for m in p5 for t in bm.QD_TERMOS if f"{bm.chave(m)}|{t}" not in q5)
    out.log(f"== status · pasta {out.p.name}")
    out.log(f"  Frente 3 PNCP: {len(muns) - len(p3)}/{len(muns)} municípios completos; {len(p3)} pendentes ({pq3} consultas)")
    out.log(f"  Frente 4 Siconfi: {p4} município-anos sem consulta (fora as reconsultas de 'sem DCA' recente)")
    out.log(f"  Frente 5 Querido Diário: {len(ab) - len(p5)}/{len(ab)} casos abertos completos; {len(p5)} pendentes ({pq5} consultas)")
    fr = ",".join(x for x, n in (("3", len(p3)), ("4", p4), ("5", len(p5))) if n)
    uarg = f" --universo {UNIV}" if UNIV != "base" else ""
    out.log(f"  Para retomar: python buscar_frentes_3a5.py rodar --frentes {fr}{uarg}" if fr else "  Nada pendente.")

# ------------------------------------------------------------------ resumo
def resumo(muns, out):
    import openpyxl
    from openpyxl.styles import Font
    P = bm.ler_csv(out.p / "pncp_contratos.csv"); S = bm.ler_csv(out.p / "siconfi_despesa.csv"); Q = bm.ler_csv(out.p / "qd_achados.csv")
    for x in Q: x["triagem"] = bm.triagem_texto(x.get("excerto", "")) or "citacao"
    f3, f4, f5 = out.feitos("pncp3"), out.feitos("siconfi"), out.feitos("qd")
    anos = sorted({x["ano"] for x in S})
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = "Resumo"
    cab = ["Município", "UF", "Caso aberto", "PNCP consultado", "Contratos", "Editais", "Último contrato — fornecedor", "CNPJ",
           "Vigência até", "Vigente hoje", "Gratuidade escrita (algum documento)", "Todos os CNPJs de fornecedor"] + \
          [f"x.453 liquidada {a}" for a in anos] + [f"% do total {a}" for a in anos] + ["QD consultado", "QD — excertos fortes", "QD — excertos médios", "QD — melhor excerto"]
    ws.append(cab)
    for m in muns:
        c6 = m["cod6"]; p = [x for x in P if x["cod_ibge"] == c6]
        cts = sorted([x for x in p if x["fonte"] == "contrato"], key=lambda x: x.get("vigencia_fim") or "", reverse=True)
        ult = cts[0] if cts else {}
        cn = sorted({c for x in p for c in (x.get("cnpj_fornecedor") or "").split(" | ") if c})
        s = [x for x in S if x["cod_ibge"] == m["cod7"]]
        def val(a, pred):
            v = [float(x["valor"]) for x in s if x["ano"] == a and x["valor"] not in ("", None) and "Liquidad" in (x["coluna"] or "") and pred(x)]
            return sum(v) if v else None
        l453 = {a: val(a, lambda x: bool(re.match(r"\d{2}\.453\b", str(x["conta"])))) for a in anos}  # 28/09/2026: qualquer função + subfunção 453
        tot = {a: val(a, lambda x: str(x["conta"]).lower().startswith("despesas exceto intra")) or val(a, lambda x: str(x["conta"]).lower().startswith("total geral")) for a in anos}
        semdca = {a for a in anos if any(x["ano"] == a and x["conta"] == "(sem DCA publicado)" for x in s)
                  and not any(x["ano"] == a and x["conta"] != "(sem DCA publicado)" for x in s)}   # 28/09/2026: o DCA pode chegar numa reconsulta
        q = [x for x in Q if x["cod_ibge"] == c6]
        melhor = sorted(q, key=lambda x: {"forte": 0, "medio": 1}.get(x["triagem"], 2))
        ws.append([m["municipio"], m["uf"], "sim" if m["aberto"] else "não", "sim" if bm.chave(m) in f3 else "não",
                   len(cts), len(p) - len(cts), ult.get("fornecedor", ""), ult.get("cnpj_fornecedor", ""), (ult.get("vigencia_fim") or "")[:10],
                   ult.get("vigente_hoje", ""), "sim" if any(x.get("gratuidade_escrita") == "sim" for x in p) else "", "; ".join(cn)] +
                  [("sem DCA" if a in semdca else l453[a]) for a in anos] +
                  [(round(100 * l453[a] / tot[a], 2) if l453[a] and tot[a] else "") for a in anos] +
                  ["sim" if bm.chave(m) in f5 else ("não aplicável (fechado)" if not m["aberto"] else "não"),
                   sum(1 for x in q if x["triagem"] == "forte"), sum(1 for x in q if x["triagem"] == "medio"),
                   (f"[{melhor[0]['triagem']}] {melhor[0]['data']} {melhor[0]['excerto'][:250]} {melhor[0]['link']}" if melhor else "")])
    for c in ws[1]: c.font = Font(bold=True)
    for nome, L in (("Contratos PNCP", P), ("Siconfi", S), ("Querido Diário", Q)):
        w = wb.create_sheet(nome)
        if L:
            w.append(list(L[0].keys()))
            for x in L: w.append(list(x.values()))
    lm = wb.create_sheet("Leia-me")
    for t in [f"Frentes 3–5 — gerado em {dt.datetime.now():%d/%m/%Y %H:%M} por _meta/scripts/buscar_frentes_3a5.py.",
              "Autor: Thiago Von Zeidler Gomes · Orientadora: Prof.ª Dra. Silvana Zioni",
              "PNCP: só contratações publicadas a partir de 04/2021 (Lei 14.133). Ausência de contrato no PNCP não é ausência de contrato.",
              "Siconfi: DCA Anexo I-E, coluna 'Despesas Liquidadas'. x.453 = Transporte Coletivo Urbano, somado sob qualquer função (26.453, 15.453…); 'sem DCA' = o município não publicou (NA, não zero).",
              "  A classificação funcional depende do lançamento contábil de cada prefeitura: TZ pode estar em outra subfunção (ex.: 26.122, 15.452). Ler como indício.",
              "Querido Diário: só municípios indexados; 0 diários devolvidos = não indexado, não 'sem TZ'.",
              "Próximo passo: Claude lê este resumo e propaga para a base-mestre (operador, CNPJ, vigência, custeio) com leitura dos documentos que decidem."]:
        lm.append([t])
    wb.save(out.p / "resumo.xlsx"); out.log(f"resumo -> {out.p / 'resumo.xlsx'}")

# ------------------------------------------------------------------ autoteste
def autoteste():
    ok = True
    def t(nome, got, exp):
        nonlocal ok
        print(("ok    " if got == exp else "FALHA ") + f"{nome}: {got!r} (esperado {exp!r})"); ok &= got == exp
    t("url contrato", partes_url("/contratos/46373445000118/2025/117"), ("contratos", "46373445000118", "2025", "117"))
    t("url compra", partes_url("/compras/46373445000118/2025/370"), ("compras", "46373445000118", "2025", "370"))
    t("url inválida", partes_url("/x/1"), None)
    t("vigente futuro", vigente("2099-01-01"), "sim"); t("vigente passado", vigente("2020-01-01"), "não"); t("vigente vazio", vigente(""), "")
    t("transporte ok", eh_transporte("Locação de ônibus com motorista para o transporte coletivo urbano gratuito"), True)
    t("transporte escolar fora", eh_transporte("Transporte escolar de alunos da rede municipal"), False)
    t("pneus fora", eh_transporte("Aquisição de pneus para ônibus"), False)
    t("obra fora", eh_transporte("Contratação de empresa de engenharia para a construção da estação de ônibus intermunicipal"), False)
    t("cnpj", fmt_cnpj("00413338000175"), "00.413.338/0001-75")
    t("conta 26.453", conta_relevante("26.453 - Transporte Coletivo Urbano"), True)
    t("conta 15.453", conta_relevante("15.453 - Transportes Coletivos Urbanos"), True)
    t("conta 15.452 fora", conta_relevante("15.452 - Serviços Urbanos"), False)
    t("conta total", conta_relevante("Despesas Exceto Intraorçamentárias"), True)
    t("conta saúde fora", conta_relevante("10.301 - Atenção Básica"), False)
    t("constantes v3", (PNCP_MAX_PAUSAS, QD_FALHAS_SEGUIDAS, SEMDCA_RETENTAR_DIAS) > (0, 0, 0), True)
    print("\nTODOS OK" if ok else "\nHÁ FALHAS"); return ok

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("comando", choices=["rodar", "resumo", "autoteste", "status"])
    ap.add_argument("--frentes", default="3,4,5"); ap.add_argument("--anos", default="2017-2025")
    ap.add_argument("--limite", type=int); ap.add_argument("--delay", type=float, default=2.5)  # PNCP derruba conexões com 1 s (ensaio de 25/09)
    ap.add_argument("--saida"); ap.add_argument("--recomecar", action="store_true"); ap.add_argument("--abertos", action="store_true")
    ap.add_argument("--tentativas", type=int, default=3)
    ap.add_argument("--siconfi-refazer", action="store_true", help="apaga siconfi_despesa.csv e o checkpoint e refaz a frente 4 inteira")
    ap.add_argument("--universo", default="base", help="base (padrão) ou combinação de pistas,camada2,camada3 — ver v4 no cabeçalho")
    ap.add_argument("--com-2d", dest="com_2d", action="store_true", help="com --universo camada2: inclui os municípios só com 2d (eleitoral/evento)")
    ap.add_argument("--nova", action="store_true", help="abre pasta de saída nova datada (padrão: continua na mais recente)")  # 25/09: 6 tentativas com espera crescente prendiam 50 min por município
    a = ap.parse_args()
    global UNIV; UNIV = a.universo + (" --com-2d" if a.com_2d else "")
    if a.comando == "autoteste": sys.exit(0 if autoteste() else 1)
    # 26/09/2026: a pasta de saída era datada pelo dia de execução, então rodar no dia seguinte recomeçava do zero.
    # Agora continua na pasta mais recente, salvo --nova (ou --saida explícita).
    if a.saida: pasta = Path(a.saida)
    elif a.universo != "base": pasta = AQUI / "saida_frentes_3a5_ampliado"
    else:
        existentes = sorted(AQUI.glob("saida_frentes_3a5_20*"))
        pasta = existentes[-1] if (existentes and not a.nova) else AQUI / f"saida_frentes_3a5_{HOJE.isoformat()}"
    out = bm.Saida(pasta, a.recomecar)
    if a.recomecar:   # a Saida só limpa *_achados.csv e _feito_*; limpa também as tabelas desta rodada
        for nome in ("pncp_contratos.csv", "siconfi_despesa.csv"):
            if (out.p / nome).exists(): (out.p / nome).unlink()
    muns = ler_base(a)
    a0, a1 = (int(x) for x in a.anos.split("-")); anos = [str(y) for y in range(a0, a1 + 1)]
    if a.comando == "status": status(muns, out, anos); return
    if a.siconfi_refazer:
        for nome in ("siconfi_despesa.csv", "_feito_siconfi.txt", "_siconfi_semdca_tentativas.txt"):
            if (out.p / nome).exists(): (out.p / nome).unlink()
    if a.comando == "rodar":
        http = bm.Http(delay=a.delay, tentativas=a.tentativas, timeout=20, backoff_max=8)
        fr = set(a.frentes.split(","))
        out.log(f"== rodar · universo {a.universo} · {len(muns)} municípios · frentes {a.frentes} · saída {out.p}")
        if "3" in fr: rodar_pncp([m for m in muns if m["aberto"]] if a.abertos else muns, http, out)
        if "4" in fr: rodar_siconfi(muns, http, out, anos)
        if "5" in fr: rodar_qd([m for m in muns if m["aberto"]], http, out)
    resumo(muns, out)
    if a.comando == "rodar": status(muns, out, anos)

if __name__ == "__main__":
    main()
