#!/usr/bin/env python3
"""
baixar_sidra.py — puxa do Censo 2022 (SIDRA/IBGE), em nível MUNICIPAL, as
variáveis de DESLOCAMENTO (trabalho e estudo) e de ENTORNO urbanístico, para
CSV largo (uma linha por município). Só biblioteca padrão.

RODAR NA SUA MÁQUINA: a apisidra responde direto e sem limite de tamanho.
(No sandbox do Cowork o web_fetch alcança a API, mas estoura o limite por chamada.)

Tabelas confirmadas (Censo 2022, nível N6 = 5.570 municípios):
  - 10329  Deslocamento p/ TRABALHO — "local de exercício do trabalho principal"
           var 13373 · classif. C469
  - 10321  Deslocamento p/ ESTUDO — "local da escola/creche que frequentavam"
           var 13631 · classif. C468
  - 6591   ENTORNO urbanístico — "características do entorno"
           var 9598 · classif. C14

Estratégia: 1 chamada por categoria (n6/all) para não estourar a resposta;
monta CSV largo por município. Formato apisidra: /f/u/h/n (compacto, sem cabeçalho).

USO:
  python3 baixar_sidra.py                      # baixa as 3 tabelas
  python3 baixar_sidra.py trabalho             # só uma (trabalho|estudo|entorno)
Saída: pasta ./sidra_censo2022/*.csv
"""
import urllib.request, json, csv, time, os, sys

BASE = "https://apisidra.ibge.gov.br/values"
OUT  = "./sidra_censo2022"

def get(url):
    for t in range(6):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "pesquisa-doutorado-PGT-UFABC"})
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.load(r)
        except Exception as e:
            if t == 5: raise
            time.sleep(3 * (t + 1))

def baixa(tab, var, fixos, alvo, out_name):
    """fixos: dict {classif: codigo_total}; alvo: (classif, {cod: rotulo_col})."""
    os.makedirs(OUT, exist_ok=True)
    alvo_c, cats = alvo
    fixstr = "".join(f"/{c}/{cod}" for c, cod in fixos.items())
    linhas = {}
    for cod, rotulo in cats.items():
        url = f"{BASE}/t/{tab}/n6/all/v/{var}/p/2022{fixstr}/{alvo_c}/{cod}/f/u/h/n"
        for it in get(url):
            m = it.get("D1C")
            if not m: continue
            linhas.setdefault(m, {"cod_mun": m})[rotulo] = it.get("V")
        time.sleep(0.3)
        print(f"  {tab} {rotulo}: {len(linhas)} municípios", flush=True)
    campos = ["cod_mun"] + list(cats.values())
    p = os.path.join(OUT, out_name)
    with open(p, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=campos, extrasaction="ignore"); w.writeheader()
        for m in sorted(linhas): w.writerow(linhas[m])
    print(f"OK -> {p} ({len(linhas)} municípios)\n", flush=True)

# ---- definições das 3 tabelas ----
TRABALHO = dict(tab="10329", var="13373",
    fixos={"c2":"6794","c386":"9680","c2087":"79177"},   # sexo/renda/retorno = Total
    alvo=("c469", {"12167":"trab_mesmo_municipio","12168":"trab_no_domicilio",
                    "12169":"trab_fora_domicilio","12188":"trab_outro_municipio",
                    "12189":"trab_pais_estrangeiro","12190":"trab_multiplos","79176":"trab_total"}),
    out_name="deslocamento_trabalho_2022.csv")

ESTUDO = dict(tab="10321", var="13631",
    fixos={"c2":"6794","c86":"95251","c386":"9680"},      # sexo/cor/renda = Total
    alvo=("c468", {"12163":"estudo_mesmo_municipio","12164":"estudo_outro_municipio",
                    "12165":"estudo_pais_estrangeiro","79174":"estudo_total"}),
    out_name="deslocamento_estudo_2022.csv")

ENTORNO = dict(tab="6591", var="9598",
    fixos={"c2":"6794","c58":"95253"},                    # sexo/idade = Total
    alvo=("c14", {"200":"entorno_total",
                   "72246":"via_pavimentada_existe","72254":"iluminacao_publica_existe",
                   "72258":"ponto_onibus_existe","72262":"via_bicicleta_existe",
                   "72266":"calcada_existe","72274":"rampa_cadeirante_existe",
                   "72278":"arboriz_sem_arvores","72281":"arboriz_5_ou_mais"}),
    out_name="entorno_urbanistico_2022.csv")

if __name__ == "__main__":
    alvo = sys.argv[1] if len(sys.argv) > 1 else "todos"
    if alvo in ("todos","trabalho"): baixa(**TRABALHO)
    if alvo in ("todos","estudo"):   baixa(**ESTUDO)
    if alvo in ("todos","entorno"):  baixa(**ENTORNO)
    print("CONCLUÍDO. CSVs em ./sidra_censo2022/")
