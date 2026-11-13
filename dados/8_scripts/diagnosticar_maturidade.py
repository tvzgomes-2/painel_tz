# -*- coding: utf-8 -*-
"""Diagnóstico de maturidade da base-mestre (reprodutível).
Lê Municípios TZ - consolidado.xlsx e Tipologias TZ - consolidado.xlsx e imprime o funil por dimensão e o
cruzamento com porte (População (2022) = Censo 2022, base municipal v3, corrigida em 25/09/2026).
Uso: python diagnosticar_maturidade.py [--json saida.json]   (read-only)
Autor: Thiago Von Zeidler Gomes · Orientadora: Prof.ª Dra. Silvana Zioni"""
import os, re, sys, json, collections, openpyxl
R = os.environ.get("TZ_VAULT", os.path.expanduser("~/mnt/doutorado"))
M = os.path.join(R, "03 - Dados/_data/casos por fonte/Municípios TZ - consolidado.xlsx")
RG = os.path.join(R, "03 - Dados/_data/casos por fonte/Tipologias TZ - consolidado.xlsx")
wb = openpyxl.load_workbook(M, read_only=True); rows = list(wb["consolidado"].iter_rows(values_only=True)); H = rows[0]
g = lambda r, k: ("" if r[H.index(k)] is None else str(r[H.index(k)]).strip())
esc = [r for r in rows[1:] if g(r, "Situação") in ("Ativa", "Encerrada")]
def vazio(s): return s.lower() in ("", "none", "nan", "—", "-", "não mencionado", "não apurado", "não localizado")
D = {
 "fechado": lambda r: g(r, "Status no log").startswith("Resolvido"),
 "portao_det": lambda r: not vazio(g(r, "Régua — portão")) and not re.match(r"(a verificar|não determinável|candidato)", g(r, "Régua — portão").lower()),
 "portao_nenhum": lambda r: g(r, "Régua — portão").lower().startswith("nenhum"),
 "subtipo": lambda r: not vazio(g(r, "Régua — subtipo")),
 "vigente": lambda r: g(r, "Vigência — última evidência (leitura 23/09)").lower().split("||")[0].strip().startswith(("vigente", "confirmada", "operação contratada", "operação municipal")),
 "vig_duvida": lambda r: g(r, "Vigência — última evidência (leitura 23/09)").lower().split("||")[0].strip().startswith(("duvidosa", "não apurada", "provável")) or not g(r, "Vigência — última evidência (leitura 23/09)"),
 "operador": lambda r: not vazio(g(r, "Operador")),
 "cnpj": lambda r: bool(re.search(r"\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}", g(r, "Operador — CNPJ"))),
 "direta": lambda r: g(r, "Operador × GE — resultado (cruzamento)").startswith("sem operador privado"),
 "custeio": lambda r: not vazio(g(r, "Mecanismo de custeio")) and not g(r, "Mecanismo de custeio").lower().startswith("não verificado"),
 "tipologia": lambda r: not vazio(g(r, "Tipologia analítica")) and not g(r, "Tipologia analítica").lower().startswith("a classificar"),
 "linhas": lambda r: not vazio(g(r, "Nº linhas")) and not g(r, "Nº linhas").lower().startswith(("não", "a apurar")),
 "norma_lida": lambda r: g(r, "Instrumento — base da decisão").lower().startswith(("dispositivo lido", "contrato lido")) or bool(re.search(r"(?<!não )\b(lid[ao]s?|transcrit[ao])\b", g(r, "Status no log"))),
 "fonte_ext": lambda r: g(r, "Fontes — nº de levantamentos (recontagem)") not in ("", "0"),
}
N = len(esc); tot = {k: sum(1 for r in esc if f(r)) for k, f in D.items()}
def pop(r):
    try: return int(float(g(r, "População (2022)")))
    except ValueError: return None
faixas = [("< 10 mil", 0, 10000), ("10–20 mil", 10000, 20000), ("20–50 mil", 20000, 50000), ("50–100 mil", 50000, 100000), ("≥ 100 mil", 100000, 10**9)]
porte = []
for nome, a, b in faixas:
    rs = [r for r in esc if pop(r) is not None and a <= pop(r) < b]
    porte.append(dict(faixa=nome, n=len(rs), fechado=sum(D["fechado"](r) for r in rs), portao=sum(D["portao_det"](r) for r in rs),
                      subtipo=sum(D["subtipo"](r) for r in rs), cnpj_ou_direta=sum(D["cnpj"](r) or D["direta"](r) for r in rs)))
uf = collections.Counter(g(r, "UF") for r in esc); uf_f = collections.Counter(g(r, "UF") for r in esc if D["fechado"](r))
su = collections.Counter(g(r, "Situação unificada (controle)") for r in esc)
w = openpyxl.load_workbook(RG, read_only=True)
abas = {n: collections.Counter(st for x in list(w[n].iter_rows(values_only=True))[1:] for st in ((__import__("re").findall(r"2[a-e]", str(x[2])) or [x[2]]) if n == "2 Parcial" else [x[2]])) for n in ("1 Universal", "2 Parcial", "3 Encerradas")}  # A.1.15
out = dict(registros=N, municipios=len({(g(r, "Município"), g(r, "UF")) for r in esc}),
           ativas=sum(g(r, "Situação") == "Ativa" for r in esc), encerradas=sum(g(r, "Situação") == "Encerrada" for r in esc),
           pistas=[g(r, "Município") + "/" + g(r, "UF") for r in rows[1:] if g(r, "Situação").startswith("Pista")],
           totais=tot, porte=porte, uf=uf.most_common(8), uf_fechados={k: uf_f[k] for k, _ in uf.most_common(8)},
           situacao_unificada=su.most_common(), abas={k: dict(v) for k, v in abas.items()})
print(json.dumps(out, ensure_ascii=False, indent=1, default=str))
if "--json" in sys.argv: json.dump(out, open(sys.argv[sys.argv.index("--json") + 1], "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
