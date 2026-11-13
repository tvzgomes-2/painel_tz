#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ingerir_cadunico.py — incorpora agregados municipais do CadÚnico à Base Municipal v3.

Contexto: ver "03 - Dados/DB - CadÚnico (vulnerabilidade e demanda cativa).md".

MODOS
  --listar-campos       consulta a API do SAGI e imprime os campos disponíveis
                        (chamada exploratória fl=*&rows=1). Rode PRIMEIRO.
  --baixar              baixa o CSV municipal de uma competência via API do SAGI.
  --explorar ARQ        mostra as colunas do arquivo e tenta adivinhar o mapeamento.
  --ingerir ARQ         faz o merge na base, gerando um novo CSV (não sobrescreve).

⚠️ A API só responde onde houver saída de rede para aplicacoes.mds.gov.br. No sandbox
   e no shell da máquina do autor o egresso está bloqueado (connect_rejected). Se
   --baixar falhar, baixe manualmente (ver §2 da nota) e use --explorar/--ingerir.

USO TÍPICO
  python3 ingerir_cadunico.py --listar-campos
  python3 ingerir_cadunico.py --baixar --competencia 202209
  python3 ingerir_cadunico.py --explorar cadunico_202209.csv
  python3 ingerir_cadunico.py --ingerir cadunico_202209.csv \
      --competencia 202209 --faixa1-valor 105.00 \
      --col-ibge ibge --col-pessoas cadunico_pessoas \
      --col-familias cadunico_familias --col-faixa1 pessoas_ate_105

GARANTIAS
  - read-only sobre a base: escreve em base_municipal_v3_cadunico_<comp>.csv
  - nunca apaga arquivo (regra do cofre)
  - registra a competência e o valor nominal da faixa 1 em coluna própria,
    para impedir o encadeamento indevido de séries (ver §3 da nota)
"""
import argparse, csv, os, sys, unicodedata, urllib.request, urllib.error, urllib.parse

API = "https://aplicacoes.mds.gov.br/sagi/servicos/misocial"
UA  = "doutorado-tarifazero/1.0 (pesquisa academica; PGT-UFABC)"
CAMPOS_PADRAO = "ibge,ibge7,codigo_ibge,municipio,anomes,ano_mes"  # + os de CadÚnico, descobertos em --listar-campos

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BASE = os.path.join(RAIZ, "03 - Dados", "_data", "Base Municipal v3", "base_municipal_v3.csv")

PISTAS = {
    "ibge":     ["ibge", "cod_ibge", "codigo_ibge", "ibge7", "id_municipio", "co_municipio"],
    "pessoas":  ["pessoa", "pes_", "qtd_pessoas", "total_pessoas"],
    "familias": ["familia", "fam_", "qtd_familias", "total_familias"],
    "faixa1":   ["extrema", "faixa1", "ate_105", "ate105", "pobreza_extrema", "renda_ate"],
    "faixa2":   ["faixa2", "pobreza", "105_a", "de_105"],
}

def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return s.strip().lower().replace(" ", "_").replace("-", "_")

def sniff(path):
    with open(path, encoding="utf-8", errors="replace", newline="") as f:
        amostra = f.read(64 * 1024); f.seek(0)
        try:
            d = csv.Sniffer().sniff(amostra, delimiters=";,\t|")
        except csv.Error:
            d = csv.excel; d.delimiter = ";" if amostra.count(";") > amostra.count(",") else ","
        return d.delimiter

def ler(path):
    delim = sniff(path)
    with open(path, encoding="utf-8", errors="replace", newline="") as f:
        r = csv.DictReader(f, delimiter=delim)
        return [dict(x) for x in r], (r.fieldnames or []), delim

def num(v):
    if v is None: return None
    s = str(v).strip().replace("R$", "").replace(" ", "").replace("%", "")
    if not s or s.lower() in ("na", "nan", "none", "-", "..", "..."): return None
    # pt-BR: 1.234,56 -> 1234.56 ; en: 1,234.56 -> 1234.56
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    try: return float(s)
    except ValueError: return None

def ibge7(v):
    """CadÚnico costuma vir com IBGE de 7 dígitos; a base usa cod_ibge. Normaliza para str de 7."""
    n = num(v)
    if n is None: return None
    s = str(int(n))
    return s if len(s) == 7 else (s.zfill(7) if len(s) < 7 else s[:7])

def _get(url, timeout=120):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        sys.exit(f"ERRO HTTP {e.code} ao consultar a API.\n  URL: {url}\n  {e.reason}")
    except Exception as e:
        sys.exit("ERRO de rede ao consultar a API do SAGI.\n"
                 f"  URL: {url}\n  {type(e).__name__}: {e}\n\n"
                 "Se a mensagem indicar recusa de conexão ou proxy, a saída de rede está\n"
                 "bloqueada neste ambiente. Baixe o arquivo manualmente (ver §2 da nota\n"
                 "'DB - CadÚnico') e use --explorar / --ingerir.")

def listar_campos():
    url = f"{API}?" + urllib.parse.urlencode({"q": "*:*", "rows": "1", "wt": "csv", "fl": "*"})
    txt = _get(url, timeout=90)
    linhas = [l for l in txt.splitlines() if l.strip()]
    if not linhas:
        sys.exit("A API respondeu vazio. Confira o endpoint no §2 da nota.")
    cols = next(csv.reader([linhas[0]]))
    print(f"campos disponíveis na API ({len(cols)}):\n")
    ncols = {norm(c): c for c in cols}
    cand = {}
    for papel, pistas in PISTAS.items():
        cand[papel] = [o for n, o in ncols.items() if any(pp in n for pp in pistas)]
    for c in sorted(cols): print("  ", c)
    print("\n-- candidatos por papel (CONFERIR antes de baixar) --")
    for papel, achados in cand.items():
        print(f"  {papel:9s}: {achados if achados else 'NENHUM'}")
    print("\nMonte a lista de campos e rode:")
    print("  python3 ingerir_cadunico.py --baixar --competencia AAAAMM --campos 'ibge,campo1,campo2,...'")

def baixar(comp, campos, saida, filtro_comp):
    if not comp: sys.exit("ERRO: --competencia é obrigatória (AAAAMM).")
    q = {"q": "*:*", "rows": "6000", "wt": "csv"}
    if campos: q["fl"] = campos
    if filtro_comp: q["fq"] = f"{filtro_comp}:{comp}"
    url = f"{API}?" + urllib.parse.urlencode(q)
    print(f"GET {url}\n")
    txt = _get(url)
    linhas = [l for l in txt.splitlines() if l.strip()]
    if len(linhas) < 2:
        sys.exit("A API devolveu menos de duas linhas. Confira --competencia, --campos e "
                 "o nome do campo de competência (--campo-competencia).")
    saida = saida or os.path.join(os.getcwd(), f"cadunico_{comp}.csv")
    if os.path.exists(saida):
        sys.exit(f"ERRO: {saida} já existe. Renomeie ou use --saida (o script nunca sobrescreve).")
    with open(saida, "w", encoding="utf-8", newline="") as f:
        f.write("\n".join(linhas) + "\n")
    print(f"OK  {saida}\n    linhas de dados: {len(linhas)-1}")
    if len(linhas) - 1 < 5000:
        print("    ⚠️  menos de 5.000 municípios — verifique se o filtro de competência está correto")
    print("\nAgora: python3 ingerir_cadunico.py --explorar", os.path.basename(saida))

def explorar(path):
    linhas, cols, delim = ler(path)
    print(f"arquivo: {path}\ndelimitador: {delim!r}\nlinhas: {len(linhas)}\ncolunas: {len(cols)}\n")
    print("-- colunas --")
    for c in cols: print("  ", c)
    print("\n-- palpite de mapeamento (CONFERIR) --")
    ncols = {norm(c): c for c in cols}
    for papel, pistas in PISTAS.items():
        achados = [orig for n, orig in ncols.items() if any(p in n for p in pistas)]
        print(f"  --col-{papel:9s} candidatos: {achados if achados else 'NENHUM'}")
    if linhas:
        print("\n-- primeira linha --")
        for c in cols[:25]: print(f"   {c} = {linhas[0].get(c)!r}")
    print("\nConfira os candidatos e rode de novo com --ingerir e as flags --col-*.")

def ingerir(a):
    if not os.path.exists(BASE):
        sys.exit(f"ERRO: base não encontrada em {BASE}")
    dados, _, _ = ler(a.arquivo)

    idx = {}
    for row in dados:
        k = ibge7(row.get(a.col_ibge))
        if k: idx[k] = row
    if not idx:
        sys.exit(f"ERRO: nenhum código IBGE lido da coluna {a.col_ibge!r}. Rode --explorar.")

    comp = a.competencia
    novas = [f"cadunico_pessoas_{comp}", f"cadunico_familias_{comp}",
             f"cadunico_pessoas_faixa1_{comp}", f"cadunico_pessoas_faixa2_{comp}",
             "cadunico_faixa1_valor_ref", "cadunico_competencia",
             "cadunico_cobertura_pct", "cadunico_extrema_pct"]

    with open(BASE, encoding="utf-8", errors="replace", newline="") as f:
        rb = csv.DictReader(f); campos = list(rb.fieldnames or []); base = [dict(x) for x in rb]

    col_ibge_base = "cod_ibge" if "cod_ibge" in campos else None
    if not col_ibge_base:
        sys.exit("ERRO: a base não tem coluna 'cod_ibge'.")

    for c in novas:
        if c in campos:
            sys.exit(f"ERRO: a base já tem a coluna {c!r}. Renomeie a competência ou revise.")
    campos += novas

    casados = 0
    for row in base:
        k = ibge7(row.get(col_ibge_base))
        src = idx.get(k)
        for c in novas: row[c] = ""
        if not src: continue
        casados += 1
        pes = num(src.get(a.col_pessoas)) if a.col_pessoas else None
        fam = num(src.get(a.col_familias)) if a.col_familias else None
        f1  = num(src.get(a.col_faixa1))   if a.col_faixa1   else None
        f2  = num(src.get(a.col_faixa2))   if a.col_faixa2   else None
        pop = num(row.get("pop_2022"))
        row[f"cadunico_pessoas_{comp}"]        = "" if pes is None else int(pes)
        row[f"cadunico_familias_{comp}"]       = "" if fam is None else int(fam)
        row[f"cadunico_pessoas_faixa1_{comp}"] = "" if f1  is None else int(f1)
        row[f"cadunico_pessoas_faixa2_{comp}"] = "" if f2  is None else int(f2)
        row["cadunico_faixa1_valor_ref"] = a.faixa1_valor or ""
        row["cadunico_competencia"] = comp
        if pes is not None and pop:
            row["cadunico_cobertura_pct"] = round(pes / pop * 100, 2)
        if f1 is not None and pop:
            row["cadunico_extrema_pct"] = round(f1 / pop * 100, 2)

    saida = os.path.join(os.path.dirname(BASE), f"base_municipal_v3_cadunico_{comp}.csv")
    with open(saida, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos); w.writeheader(); w.writerows(base)

    cob = [num(r.get("cadunico_cobertura_pct")) for r in base]
    cob = sorted(x for x in cob if x is not None)
    print(f"OK  {saida}")
    print(f"    municípios na base: {len(base)} · casados com o CadÚnico: {casados} "
          f"({casados/len(base)*100:.1f}%)")
    if len(base) - casados:
        print(f"    ⚠️  {len(base)-casados} sem correspondência — conferir antes de usar")
    if cob:
        med = cob[len(cob)//2]
        print(f"    cobertura (%): min {cob[0]:.1f} · mediana {med:.1f} · max {cob[-1]:.1f}")
        if cob[-1] > 100:
            print("    ⚠️  cobertura acima de 100% em algum município — checar população-base e o campo de pessoas")
    print(f"    competência {comp} · valor de referência da faixa 1: {a.faixa1_valor or 'NÃO INFORMADO ⚠️'}")
    print("\nA base original NÃO foi alterada. Confira a saída e, se estiver correta,")
    print("promova-a a canônica registrando a decisão em 'Mapa de Dados'.")

def main():
    p = argparse.ArgumentParser(description="Incorpora o CadÚnico municipal à Base Municipal v3.")
    p.add_argument("--listar-campos", action="store_true", dest="listar",
                   help="consulta a API e imprime os campos disponíveis")
    p.add_argument("--baixar", action="store_true", help="baixa o CSV da competência via API do SAGI")
    p.add_argument("--campos", help="lista de campos para a API (fl=...); ver --listar-campos")
    p.add_argument("--campo-competencia", dest="campo_comp", default="ano_mes",
                   help="nome do campo de competência no filtro fq (padrão: ano_mes)")
    p.add_argument("--saida", help="caminho do CSV a gravar em --baixar")
    p.add_argument("--explorar", metavar="ARQ")
    p.add_argument("--ingerir", metavar="ARQ", dest="arquivo")
    p.add_argument("--competencia", help="AAAAMM, ex. 202209")
    p.add_argument("--faixa1-valor", dest="faixa1_valor", help="valor nominal da faixa 1 na competência, ex. 105.00")
    p.add_argument("--col-ibge", default="ibge")
    p.add_argument("--col-pessoas"); p.add_argument("--col-familias")
    p.add_argument("--col-faixa1");  p.add_argument("--col-faixa2")
    a = p.parse_args()
    if a.listar: return listar_campos()
    if a.baixar: return baixar(a.competencia, a.campos, a.saida, a.campo_comp)
    if a.explorar: return explorar(a.explorar)
    if a.arquivo:
        if not a.competencia: sys.exit("ERRO: --competencia é obrigatória (AAAAMM).")
        if not a.faixa1_valor:
            print("⚠️  sem --faixa1-valor: a série não poderá ser encadeada com segurança (ver §3 da nota).")
        return ingerir(a)
    p.print_help()

if __name__ == "__main__":
    main()
