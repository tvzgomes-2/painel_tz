#!/usr/bin/env python3
"""reconciliar_tarifa_frota.py — resolve a pendência "reconciliar tarifa e
frota: SIMU x PEMOB/ANTP e DENATRAN" (Auditoria de dados, item 1). Resultado
da checagem (22/07/2026), separado por variável — são dois casos diferentes:

  FROTA (frota_onibus_simu_2021 / frota_total_simu_2021, já no wide, x
  serie_frota.csv/DENATRAN): **NÃO SÃO DUAS FONTES.** Comparados os 5.514
  municípios com valor nos dois lados em 2021 — correlação 1.0, diferença
  ZERO em TODOS (testado também frota_total, mesmo resultado), inclusive nas
  27 capitais. O SIMU/Ministério das Cidades republica o cadastro do
  DENATRAN, não faz coleta própria de frota. **Não há nada para reconciliar
  — é a mesma variável sob dois nomes.** Não integra nada novo aqui; só
  documenta (metadados.csv) que `frota_onibus_simu_2021`/
  `frota_total_simu_2021` E os dados de frota do DENATRAN são a MESMA fonte,
  para não serem citados como duas fontes independentes na tese.

  TARIFA (serie_tarifa_simu.csv x serie_tarifa.csv x ANTP): **SÃO três
  fontes independentes de fato**, não duas — correção de rótulo importante
  (a pedido do autor, 22/07/2026): a documentação anterior chamava
  `serie_tarifa.csv` de "PEMOB/ANTP" ou "PEMOB/SIMOB-ANTP", ERRADO — são
  instituições diferentes:
    - **PEMOB** = Pesquisa Nacional de Mobilidade Urbana (Ministério das
      Cidades, plataforma SIMU). `serie_tarifa.csv`/`tarifa_2024` vêm daqui
      — o autor tabulou manualmente os arquivos brutos por edição
      (2018-2024, `caderno PEMOB.R`). NÃO tem ANTP nisso. 102 municípios,
      2016-2024.
    - **SIMU** (`serie_tarifa_simu.csv`, `simu-tarifas-mun_T.csv`) — mesma
      casa institucional da PEMOB, mas indicador PRÉ-TABULADO pelo governo,
      não pelo autor; pipeline diferente, não confirmado se usa as mesmas
      respostas/edições. 105 municípios, 2010-2021 (esparso).
    - **ANTP/SIMOB** = sistema HISTÓRICO da Associação Nacional de
      Transportes Públicos — fonte GENUINAMENTE DIFERENTE, **extraída e
      integrada em 22/07/2026** do PDF já no acervo
      (`_data/SIMOB-ANTP/copia-de-tarifas_2005-a-atual-1.pdf`, extração com
      `pdfplumber`, tabela nativa do PDF — não é OCR de texto solto). 46
      grandes cidades (capitais + grandes RMs, inclui Santo André/SP e São
      Bernardo do Campo/SP, do Grande ABC), granularidade trimestral
      (jan/abr/jul/out) **2005-2017** — cobre sozinha quase toda a década
      2005-2015, período em que PEMOB e SIMU não têm NADA. Onde há
      sobreposição: contra PEMOB (30 município-ano em comum, 2016-2017),
      diferença mediana 0 mas até 14,9% de divergência; contra SIMU (361
      município-ano em comum, 2010-2017), diferença mediana 0 mas até 50%
      de divergência — mesmo padrão de "concordância parcial" já visto
      entre PEMOB e SIMU, reforçando que são de fato pesquisas
      independentes, não o mesmo dado retabulado.
  Rótulos corretos: **PEMOB ≠ SIMU ≠ ANTP/SIMOB** — três fontes.
  `tarifa_reconciliada_fonte` usa "PEMOB", "SIMU" ou "ANTP".

  DECISÃO (com o autor, 22/07/2026): **PEMOB > SIMU > ANTP**, nessa ordem de
  prioridade quando o mesmo município-ano aparece em mais de uma fonte
  (mantém a decisão original PEMOB-principal; ANTP entra como 3º nível,
  preenchendo sobretudo os anos 2005-2015 que as outras duas não cobrem).
  Nunca mistura sem marcar a proveniência por linha.

SAÍDA: `serie_tarifa_reconciliada.csv` (painel completo, PEMOB+SIMU+ANTP,
coluna `fonte`) + 3 colunas novas no wide (tarifa do ano mais recente
disponível por município, priorizando PEMOB>SIMU>ANTP): `tarifa_reconciliada`,
`tarifa_reconciliada_ano`, `tarifa_reconciliada_fonte`.

USO:  python reconciliar_tarifa_frota.py
Requer: pandas, pdfplumber (só para extrair o PDF da ANTP). Não acessa rede."""
import os, re, sys, unicodedata
import pandas as pd
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
V = os.path.join(os.path.abspath(os.path.join(HERE, "..", "..")), "03 - Dados", "_data")
OUT = os.path.join(V, "Base Municipal v3")
BASE_CSV = os.path.join(OUT, "base_municipal_v3.csv")
ANTP_PDF = os.path.join(V, "SIMOB-ANTP", "copia-de-tarifas_2005-a-atual-1.pdf")

MESES = {"jan": 1, "janeiro": 1, "fev": 2, "fevereiro": 2, "mar": 3, "março": 3, "abr": 4,
         "abril": 4, "mai": 5, "maio": 5, "jun": 6, "junho": 6, "jul": 7, "julho": 7,
         "ago": 8, "agosto": 8, "set": 9, "setembro": 9, "out": 10, "outubro": 10,
         "nov": 11, "novembro": 11, "dez": 12, "dezembro": 12}


def norm(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Z0-9]", "", s.upper())


def c7(x):
    try:
        return str(int(float(x))).zfill(7)
    except Exception:
        return None


def log(msg):
    print(msg, flush=True)


def salvar_atomico(df, path):
    tmp = path + ".tmp"
    df.to_csv(tmp, index=False)
    os.replace(tmp, path)


def parse_periodo(h):
    h = h.replace("\n", " ").strip().lower().replace("em ", "")
    m = re.search(r"([a-zç]+)[\s/]+(\d{2,4})", h)
    if not m:
        return None
    mes = MESES.get(m.group(1)[:3]) or MESES.get(m.group(1))
    if mes is None:
        return None
    ano = int(m.group(2))
    if ano < 100:
        ano += 2000
    return ano, mes


def parse_valor_rs(v):
    if not v:
        return None
    v = v.replace("R$", "").replace(" ", "").replace(",", ".").strip()
    try:
        return float(v)
    except Exception:
        return None


def extrai_antp(base_nomes):
    """Extrai a tabela de tarifas ANTP/SIMOB do PDF (pdfplumber lê a tabela
    nativa do PDF — não é OCR). base_nomes: DataFrame com cod_ibge/nome_mun/uf
    do base_municipal_v3.csv, usado como ponte cidade/UF -> cod_ibge."""
    import pdfplumber
    if not os.path.exists(ANTP_PDF):
        log(f"  ! {ANTP_PDF} não encontrado — pulando ANTP.")
        return None
    rows = []
    with pdfplumber.open(ANTP_PDF) as pdf:
        for page in pdf.pages:
            tabelas = page.extract_tables()
            if not tabelas:
                continue
            t = tabelas[0]
            header, dados = t[0], t[1:]
            periodos = [parse_periodo(h) for h in header[1:]]
            for r in dados:
                cidade_uf = r[0]
                for periodo, val in zip(periodos, r[1:]):
                    v = parse_valor_rs(val)
                    if v is not None and periodo is not None:
                        rows.append({"cidade_uf": cidade_uf, "ano": periodo[0], "mes": periodo[1], "valor": v})
    if not rows:
        log("  ! nenhuma linha extraída do PDF da ANTP.")
        return None
    d = pd.DataFrame(rows)
    d["cidade"], d["uf"] = zip(*d.cidade_uf.str.rsplit("/", n=1))
    d["chave"] = d["uf"].str.upper().str.strip() + "|" + d["cidade"].map(norm)

    bridge = base_nomes.assign(chave=base_nomes["uf"].str.upper().str.strip() + "|" + base_nomes["nome_mun"].map(norm))
    d = d.merge(bridge[["chave", "cod_ibge"]], on="chave", how="left")
    sem_match = d[d.cod_ibge.isna()]["cidade_uf"].unique()
    if len(sem_match):
        log(f"  ⚠️ cidades da ANTP sem cod_ibge (checar nome): {list(sem_match)}")
    d = d.dropna(subset=["cod_ibge"])

    # snapshot anual: última leitura (mês) disponível dentro de cada ano por município
    # — mesmo critério que a PEMOB já usa ("a pesquisa mais recente é o dado mais correto")
    d = d.sort_values(["cod_ibge", "ano", "mes"])
    anual = d.groupby(["cod_ibge", "ano"]).last().reset_index()[["cod_ibge", "ano", "valor"]]
    log(f"  ANTP extraído do PDF: {len(d)} leituras trimestrais -> {len(anual)} município-ano "
        f"| {anual.cod_ibge.nunique()} municípios | {anual.ano.min()}-{anual.ano.max()}")
    return anual


def reconcilia_tarifa():
    pemob = pd.read_csv(os.path.join(OUT, "serie_tarifa.csv"), dtype={"cod_ibge": str}).dropna(subset=["tarifa"])
    simu = pd.read_csv(os.path.join(OUT, "serie_tarifa_simu.csv"), dtype={"cod_ibge": str}).dropna(subset=["tarifa_simu"])
    pemob = pemob.assign(fonte="PEMOB").rename(columns={"tarifa": "valor"})
    simu = simu.assign(fonte="SIMU").rename(columns={"tarifa_simu": "valor"})

    base_nomes = pd.read_csv(BASE_CSV, usecols=["cod_ibge", "nome_mun", "uf"], dtype=str, low_memory=False)
    base_nomes["cod_ibge"] = base_nomes["cod_ibge"].map(c7)
    antp = extrai_antp(base_nomes)
    partes = [pemob[["cod_ibge", "ano", "valor", "fonte"]], simu[["cod_ibge", "ano", "valor", "fonte"]]]
    if antp is not None:
        partes.append(antp.assign(fonte="ANTP")[["cod_ibge", "ano", "valor", "fonte"]])

    # painel completo (as três fontes lado a lado, sem misturar linha nenhuma sem marcar)
    painel = pd.concat(partes, ignore_index=True)
    salvar_atomico(painel, os.path.join(OUT, "serie_tarifa_reconciliada.csv"))
    todos_cods = set(pemob.cod_ibge) | set(simu.cod_ibge) | (set(antp.cod_ibge) if antp is not None else set())
    log(f"serie_tarifa_reconciliada.csv: {len(painel)} linhas | {len(todos_cods)} municípios distintos "
        f"(PEMOB={pemob.cod_ibge.nunique()}, SIMU={simu.cod_ibge.nunique()}, "
        f"ANTP={antp.cod_ibge.nunique() if antp is not None else 0})")

    # snapshot: ANO mais recente por município; em caso de empate de ano, prioriza PEMOB > SIMU > ANTP
    PRIORIDADE = {"PEMOB": 0, "SIMU": 1, "ANTP": 2}
    painel["prioridade"] = painel["fonte"].map(PRIORIDADE)
    painel = painel.sort_values(["cod_ibge", "ano", "prioridade"])
    recente = painel.groupby("cod_ibge").tail(1)  # último ano; empate de ano já resolvido pelo sort (PEMOB antes)
    recente = recente.rename(columns={"valor": "tarifa_reconciliada", "ano": "tarifa_reconciliada_ano",
                                       "fonte": "tarifa_reconciliada_fonte"})
    return recente[["cod_ibge", "tarifa_reconciliada", "tarifa_reconciliada_ano", "tarifa_reconciliada_fonte"]]


def main():
    log("=== FROTA: SIMU e DENATRAN são a MESMA fonte (verificado 22/07/2026, ver docstring) ===")
    log("  nenhuma coluna nova — só documentação em metadados.csv (frota_onibus_simu_2021 = frota DENATRAN)")

    log("\n=== TARIFA: reconciliando PEMOB > SIMU > ANTP/SIMOB (nessa prioridade) ===")
    recente = reconcilia_tarifa()
    log(f"  {len(recente)} municípios no snapshot reconciliado "
        f"(fonte: {recente.tarifa_reconciliada_fonte.value_counts().to_dict()})")

    base = pd.read_csv(BASE_CSV, dtype={"cod_ibge": str}, low_memory=False)
    base["cod_ibge"] = base["cod_ibge"].map(c7)
    base = base.drop(columns=[c for c in recente.columns if c != "cod_ibge" and c in base.columns])
    base = base.merge(recente, on="cod_ibge", how="left")
    salvar_atomico(base, BASE_CSV)
    log(f"\nOK — base_municipal_v3.csv: {base.shape[0]} x {base.shape[1]} "
        f"(+3 colunas: tarifa_reconciliada, tarifa_reconciliada_ano, tarifa_reconciliada_fonte)")
    log("Lembrete: atualizar metadados.csv e a Auditoria de dados; rodar auditar_cofre.py.")


if __name__ == "__main__":
    main()
