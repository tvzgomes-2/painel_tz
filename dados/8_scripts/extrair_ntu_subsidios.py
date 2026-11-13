#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""extrair_ntu_subsidios.py — extrai o indicador "% do custo total do
transporte coletivo por ônibus subsidiado com recursos públicos", por
município, a partir de dois Anuários NTU (transcrição manual dos gráficos
de barra "Figura 2/3/4", com conferência visual da imagem renderizada da
página do PDF — os gráficos não são tabelas nativas, pdftotext embaralha os
rótulos do eixo % com as linhas). Ver Auditoria de dados (jul-2026), item
"Anuários ANTP/SIMOB e NTU".

FONTES:
  - vintage "2023" (67 cidades): Anuário NTU 2023-2024 (pág. 66-71, Encarte
    "Pesquisas Temáticas NTU: Subsídios") == mesmo conteúdo do relatório
    avulso "NTU (2024) - Subsídios para o Transporte Coletivo Urbano por
    Ônibus" (layout limpo, 2 colunas, extração via pdftotext -layout, SEM
    contaminação de eixo — alta confiança).
  - vintage "2025" (maio/2025, 80 cidades = 21 capitais/RM + 59 outras):
    Anuário NTU 2024-2025 (pág. 69-70, Figuras 3 e 4). Extração por
    pdftotext -layout + CONFERÊNCIA VISUAL (pdftoppm -> leitura da imagem)
    de ambas as figuras, pois o layout aqui mistura texto do gráfico com o
    eixo percentual.

CORREÇÃO DOCUMENTADA: a Figura 4 da edição 2024-2025 rotula a cidade #9 como
"Itatiba/MG" — conferido visualmente no PDF, o erro é da própria NTU (não é
falha de OCR nosso). Na vintage 2023 (mesma cidade, extração limpa) e por
geografia real (não existe "Itatiba" em MG; existe em SP, região de
Campinas), a UF correta é SP. Corrigido aqui para SP com esta nota.

Cidades com escopo "(RM)" puro (ex.: "Curitiba/PR (RM)") são de sistema
metropolitano, não do município isolado — mantidas no painel completo
(serie_subsidio_ntu.csv) mas EXCLUÍDAS do snapshot de município (não têm um
cod_ibge de sistema metropolitano). Escopo "(Mun. e RM)" é tratado como
valor do município-sede (ex.: Goiânia, Vitória, Recife).

SAÍDA: serie_subsidio_ntu.csv (painel, todas as linhas, com ano/escopo/fonte)
+ 2 colunas novas no wide: subsidio_pct_custo_ntu (ano mais recente
disponível por município), subsidio_pct_custo_ntu_ano.

USO: python extrair_ntu_subsidios.py"""
import os
import re
import unicodedata

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
V = os.path.join(os.path.abspath(os.path.join(HERE, "..", "..")), "03 - Dados", "_data")
OUT = os.path.join(V, "Base Municipal v3")
BASE_CSV = os.path.join(OUT, "base_municipal_v3.csv")


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


# ---------------------------------------------------------------------------
# VINTAGE 2023 — Anuário NTU 2023-2024 / NTU "Subsídios" (2024), 67 cidades,
# extração limpa (texto nativo, 2 colunas, sem gráfico embaralhando eixo).
# ---------------------------------------------------------------------------
TXT_2023 = """
Araucária/PR 75
Votuporanga/SP 72
Santa Luzia/MG 67
Bragança Paulista/SP 57
Itatiba/SP 55
Nova Odessa/SP 55
Pouso Alegre/MG 52
Brasília/DF 50
Itabira/MG 49
S. J. da Boa Vista/SP 48
São Paulo/SP 47
V. da Conquista/BA 46
Londrina/PR 43
Goiânia/GO 43
Rio Verde/GO 43
Manaus/AM 40
Ouro Preto/MG 40
Cachoeirinha/RS 39
Ponta Grossa/PR 39
Patos de Minas/MG 37
Cuiabá/MT 36
Cascavel/PR 35
Rio Claro/SP 34
Belo Horizonte/MG 33
Guarulhos/SP 32
Várzea Grande/MT 32
Guarapuava/PR 30
Cubatão/SP 30
Vitória/ES 30
Ribeirão Preto/SP 29
Maringá/PR 29
Araçatuba/SP 29
Uberlândia/MG 29
Jacareí/SP 28
Niterói/RJ 27
João Monlevade/MG 27
Praia Grande/SP 26
Curitiba/PR (RM) 25
Taubaté/SP 24
Içara/SC 24
Passo Fundo/RS 23
Santos/SP 22
Campo Grande/MS 22
Curitiba/PR 22
Florianópolis/SC 21
Paranavaí/PR 20
Santo Ângelo/RS 20
S. J. dos Pinhais/PR 20
S. J. do Rio Preto/SP 20
Mauá/SP 19
Macapá/AP 19
Jundiaí/SP 18
Fortaleza/CE 18
Palmas/TO 18
Lajeado/RS 17
Bento Gonçalves/RS 17
S. F. do Sul/SC 15
Nova Friburgo/RJ 14
Bauru/SP 13
Campina Grande/PB 13
Blumenau/SC 12
Natal/RN 9
Guaratinguetá/SP 8
Santa Maria/RS 6
Caxias do Sul/RS 3
Recife/PE 3
Linhares/ES 2
"""

# ---------------------------------------------------------------------------
# VINTAGE 2025 (maio/2025) — Anuário NTU 2024-2025, Figura 3 (capitais/RM,
# 21) + Figura 4 (outras, 59). Conferido visualmente contra a imagem
# renderizada das págs. 69 e 70.
# ---------------------------------------------------------------------------
TXT_2025_CAPITAIS = """
Brasília/DF (Distrital) 75
Goiânia/GO (Mun. e RM) 66
Manaus/AM (Mun.) 60
São Paulo/SP (Mun.) 58
Boa Vista/RR (Mun.) 38
Teresina/PI (Mun.) 37
Cuiabá/MT (Mun.) 36
Rio de Janeiro/RJ (Mun.) 35
Belo Horizonte/MG (Mun.) 33
Fortaleza/CE (Mun.) 31
Curitiba/PR (RM) 30
Curitiba/PR (Mun.) 25
Florianópolis/SC (Mun.) 24
Vitória/ES (Mun. e RM) 23
Macapá/AP (Mun.) 19
Palmas/TO (Mun.) 18
Campo Grande/MS (Mun.) 17
Porto Alegre/RS (Mun.) 16
Recife/PE (Mun. e RM) 15
Salvador/BA (Mun.) 10
Natal/RN (Mun.) 5
"""

TXT_2025_OUTRAS = """
Araucária/PR 75
Toledo/PR 74
Votuporanga/SP 72
Santa Luzia/MG 67
Salto/SP 60
Bragança Paulista/SP 57
Cachoeirinha/RS 55
Nova Odessa/SP 55
Itatiba/MG 53
Pouso Alegre/MG 49
Itabira/MG 49
S. J. da Boa Vista/SP 48
V. da Conquista/BA 46
Londrina/PR 44
Garanhuns/PE 42
Vinhedo/SP 41
Feira de Santana/BA 41
Ponta Grossa/PR 39
Patos de Minas/MG 37
Cascavel/PR 35
Apucarana/PR 34
Rio Claro/SP 34
Guarulhos/SP 33
Ouro Preto/MG 32
Várzea Grande/MT 32
Maringá/PR 32
Cubatão/SP 30
Guarapuava/PR 30
Praia Grande/SP 30
Caxias do Sul/RS 30
Ribeirão Preto/SP 30
Araçatuba/SP 29
Uberlândia/MG 29
Jacareí/SP 28
João Monlevade/MG 27
Santa Maria/RS 25
Blumenau/SC 24
Varginha/MG 24
Taubaté/SP 24
Içara/SC 24
Passo Fundo/RS 23
Santos/SP 22
Paranavaí/PR 20
S. J. dos Pinhais/PR 20
Santo Ângelo/RS 20
S. J. do Rio Preto/SP 20
Mauá/SP 19
Jundiaí/SP 18
Bento Gonçalves/RS 17
Lajeado/RS 17
S. F. do Sul/SC 15
Nova Friburgo/RJ 15
Colatina/ES 14
Niterói/RJ 14
Bauru/SP 13
Canoas/RS 13
Guaratinguetá/SP 8
Linhares/ES 2
Campina Grande/PB 1
"""

# apelidos/abreviações do NTU -> nome oficial IBGE, já em forma norm() (sem
# espaços/acentos/pontuação), para o bridge por nome dar match exato.
ALIAS = {
    "SJDABOAVISTA": "SAOJOAODABOAVISTA",  # "S.J." aqui = São João (não José) da Boa Vista-SP
    "VDACONQUISTA": "VITORIADACONQUISTA",
    "SJDOSPINHAIS": "SAOJOSEDOSPINHAIS",
    "SJDORIOPRETO": "SAOJOSEDORIOPRETO",
    "SFDOSUL": "SAOFRANCISCODOSUL",
}


def parse_bloco(txt, escopo_default="Mun."):
    linhas = [l.strip() for l in txt.strip().splitlines() if l.strip()]
    rows = []
    for l in linhas:
        m = re.match(r"^(.*?)/([A-Z]{2})(\s*\(([^)]+)\))?\s+(\d+)$", l.strip())
        if not m:
            log(f"  ⚠️ linha não reconhecida: {l!r}")
            continue
        cidade, uf, _, escopo, pct = m.groups()
        rows.append({
            "cidade_ntu": cidade.strip(),
            "uf": uf.strip(),
            "escopo": (escopo or escopo_default).strip(),
            "pct_subsidio": int(pct),
        })
    return pd.DataFrame(rows)


def corrige_uf_conhecida(df):
    # Itatiba/MG (vintage 2025 "outras") é erro da própria NTU — não existe
    # Itatiba em MG; é a mesma cidade de Itatiba/SP (vintage 2023 confirma
    # SP, e não há município "Itatiba" cadastrado no IBGE para MG).
    m = (df["cidade_ntu"] == "Itatiba") & (df["uf"] == "MG")
    if m.any():
        log(f"  correção aplicada: Itatiba/MG -> Itatiba/SP ({m.sum()} linha(s); "
            f"erro da própria NTU, ver docstring)")
        df.loc[m, "uf"] = "SP"
    return df


def bridge_cod_ibge(df, base_nomes):
    chave_ntu = df["uf"].str.upper().str.strip() + "|" + df["cidade_ntu"].map(norm)
    for k, v in ALIAS.items():
        chave_ntu = chave_ntu.str.replace(re.escape(k), v, regex=True)
    df = df.assign(chave=chave_ntu)
    bridge = base_nomes.assign(chave=base_nomes["uf"].str.upper().str.strip() + "|" + base_nomes["nome_mun"].map(norm))
    d = df.merge(bridge[["chave", "cod_ibge"]], on="chave", how="left")
    sem = d[d.cod_ibge.isna()][["cidade_ntu", "uf", "escopo"]].drop_duplicates()
    if len(sem):
        log(f"  ⚠️ sem cod_ibge (checar nome/alias):\n{sem.to_string(index=False)}")
    return d


def main():
    base_nomes = pd.read_csv(BASE_CSV, usecols=["cod_ibge", "nome_mun", "uf"], dtype=str, low_memory=False)
    base_nomes["cod_ibge"] = base_nomes["cod_ibge"].map(c7)

    d2023 = parse_bloco(TXT_2023, escopo_default="Mun.").assign(ano=2023, fonte_doc="Anuário NTU 2023-2024 / NTU Subsídios (2024)")
    d2025c = parse_bloco(TXT_2025_CAPITAIS).assign(ano=2025, fonte_doc="Anuário NTU 2024-2025 (Figura 3, maio/2025)")
    d2025o = parse_bloco(TXT_2025_OUTRAS).assign(ano=2025, fonte_doc="Anuário NTU 2024-2025 (Figura 4, maio/2025)")

    painel = pd.concat([d2023, d2025c, d2025o], ignore_index=True)
    painel = corrige_uf_conhecida(painel)
    painel = bridge_cod_ibge(painel, base_nomes)

    salvar_atomico(painel, os.path.join(OUT, "serie_subsidio_ntu.csv"))
    log(f"\nserie_subsidio_ntu.csv: {len(painel)} linhas | "
        f"{painel.cod_ibge.nunique()} municípios distintos com cod_ibge | "
        f"anos: {sorted(painel.ano.unique())}")

    # snapshot: ano mais recente por município, excluindo escopo "(RM)" puro
    # (sistema metropolitano, não atribuível a um único cod_ibge de município)
    snap_base = painel[(painel.escopo != "RM") & painel.cod_ibge.notna()].copy()
    snap_base = snap_base.sort_values(["cod_ibge", "ano"])
    recente = snap_base.groupby("cod_ibge").tail(1)
    recente = recente.rename(columns={"pct_subsidio": "subsidio_pct_custo_ntu", "ano": "subsidio_pct_custo_ntu_ano"})
    recente = recente[["cod_ibge", "subsidio_pct_custo_ntu", "subsidio_pct_custo_ntu_ano"]]
    log(f"snapshot (município, exclui RM pura): {len(recente)} municípios")

    base = pd.read_csv(BASE_CSV, dtype={"cod_ibge": str}, low_memory=False)
    base["cod_ibge"] = base["cod_ibge"].map(c7)
    base = base.drop(columns=[c for c in recente.columns if c != "cod_ibge" and c in base.columns])
    base = base.merge(recente, on="cod_ibge", how="left")
    salvar_atomico(base, BASE_CSV)
    log(f"\nOK — base_municipal_v3.csv: {base.shape[0]} x {base.shape[1]} "
        f"(+2 colunas: subsidio_pct_custo_ntu, subsidio_pct_custo_ntu_ano)")
    log("Lembrete: atualizar metadados.csv e a Auditoria de dados; rodar auditar_cofre.py.")


if __name__ == "__main__":
    main()
