# -*- coding: utf-8 -*-
"""
Constrói o crosswalk "estudo/fonte -> município" a partir dos arquivos em
'03 - Dados/_data/casos por fonte' (cofre Obsidian da tese Tarifa Zero).

Saída: painel TZ/scripts/casos_por_fonte.json
Chave: "Município|UF"  Valor: lista de {fonte, tipo, descricao, ano, link}
"""
import json
import re
import unicodedata
from pathlib import Path

import pandas as pd

BASE = Path("/sessions/nice-stoic-hypatia/mnt/doutorado/03 - Dados/_data/casos por fonte")
OUT = Path("/sessions/nice-stoic-hypatia/mnt/painel TZ/scripts/casos_por_fonte.json")

crosswalk = {}
warnings = []


def add(municipio, uf, fonte, tipo, descricao, ano, link):
    municipio = titlecase_municipio(municipio)
    uf = (uf or "").strip().upper()
    if not uf or len(uf) != 2:
        warnings.append(f"UF ausente/invalida para '{municipio}' (fonte={fonte}) -> registro DESCARTADO")
        return
    key = f"{municipio}|{uf}"
    entry = {
        "fonte": fonte,
        "tipo": tipo,
        "descricao": descricao if descricao and str(descricao).strip().lower() != "nan" else None,
        "ano": ano,
        "link": link if link and str(link).strip().lower() != "nan" else None,
    }
    crosswalk.setdefault(key, []).append(entry)


# Correções de grafia conhecidas (mesmo município, nome grafado errado na fonte)
CORRECOES_GRAFIA = {
    "Itatiaiçu": "Itatiaiuçu",  # brinco 2017 / Munic_pios_com_FFPT grafam sem o "u"; nome oficial é Itatiaiuçu-MG
}


def titlecase_municipio(nome):
    nome = nome.strip()
    # normaliza espaços múltiplos
    nome = re.sub(r"\s+", " ", nome)
    nome = CORRECOES_GRAFIA.get(nome, nome)
    return nome


def extrai_ano(valor):
    """Extrai um ano de 4 dígitos de uma string, ou retorna int se já for numero."""
    if valor is None:
        return None
    if isinstance(valor, (int, float)):
        if pd.isna(valor):
            return None
        return int(valor)
    s = str(valor)
    m = re.search(r"(19|20)\d{2}", s)
    if m:
        return int(m.group(0))
    return None


# Cross-referencia nome de município -> UF, construída a partir dos arquivos
# que JA trazem UF explicita. Usada para resolver linhas sem UF (Pereira 2023
# nao tem UF em nenhuma linha; Angelo 2023 e Vermander 2021 tem 1 linha cada
# sem UF).
cidade_uf_index = {}


def registra_index(nome, uf):
    nome_norm = titlecase_municipio(nome)
    cidade_uf_index[nome_norm] = uf.strip().upper()


# ---------------------------------------------------------------------------
# 1. Santini 2019.csv
# ---------------------------------------------------------------------------
df = pd.read_csv(BASE / "Santini 2019.csv", sep=";", encoding="utf-8-sig")
for _, row in df.iterrows():
    m = re.match(r"^(.*)\(([A-Za-z]{2})\)\s*$", row["Cidade"].strip())
    if not m:
        warnings.append(f"Santini 2019: nao consegui separar UF de '{row['Cidade']}'")
        continue
    nome, uf = m.group(1).strip(), m.group(2)
    registra_index(nome, uf)
    ano = extrai_ano(row["Ano de Implementação"])
    add(nome, uf, "Santini 2019", "Estudo acadêmico", "estudo de caso (FFPT)", ano, None)

# ---------------------------------------------------------------------------
# 3. Angelo 2023.csv  (processado antes do Pereira p/ alimentar o indice)
# ---------------------------------------------------------------------------
df = pd.read_csv(BASE / "Angelo 2023.csv", sep=";", encoding="utf-8-sig")
angelo_sem_uf = []
for _, row in df.iterrows():
    raw = row["Município"].strip()
    m = re.match(r"^(.*?)\s*-\s*([A-Za-z]{2})\s*$", raw)
    if m:
        nome, uf = m.group(1).strip(), m.group(2).upper()
        registra_index(nome, uf)
        ano = extrai_ano(row["Ano de Implementação"])
        add(nome, uf, "Angelo 2023", "Estudo acadêmico", "estudo de caso (FFPT)", ano, None)
    else:
        # sem UF (ex.: "Itatiaiuçu") -> resolve depois via indice
        angelo_sem_uf.append((raw, extrai_ano(row["Ano de Implementação"])))

# ---------------------------------------------------------------------------
# 4. Vermander 2021.csv
# ---------------------------------------------------------------------------
df = pd.read_csv(BASE / "Vermander 2021.csv", sep=";", encoding="utf-8-sig")
df = df.dropna(subset=["Município"])
vermander_sem_uf = []
for _, row in df.iterrows():
    raw = str(row["Município"]).strip()
    m = re.match(r"^(.*)\(([A-Za-z]{2})\)\s*$", raw)
    if m:
        nome, uf = m.group(1).strip(), m.group(2).upper()
        registra_index(nome, uf)
        ano = extrai_ano(row["Ano de Implementação"])
        add(nome, uf, "Vermander 2021", "Estudo acadêmico", "estudo de caso (FFPT, pioneiros)", ano, None)
    else:
        vermander_sem_uf.append((raw, extrai_ano(row["Ano de Implementação"])))

# ---------------------------------------------------------------------------
# 5. brinco 2017.csv  (nomes com hifen "-" ou en-dash "–")
# ---------------------------------------------------------------------------
df = pd.read_csv(BASE / "brinco 2017.csv", sep=";", encoding="utf-8-sig")
for _, row in df.iterrows():
    raw = str(row["Município"]).strip()
    m = re.match(r"^(.*?)[\-–]\s*([A-Za-z]{2})\s*$", raw)
    if m:
        nome, uf = m.group(1).strip(), m.group(2).upper()
        registra_index(nome, uf)
        ano = extrai_ano(row["Ano de Implementação"])
        add(nome, uf, "brinco 2017", "Estudo acadêmico", "estudo de caso (FFPT)", ano, None)
    else:
        warnings.append(f"brinco 2017: nao consegui separar UF de '{raw}'")

# ---------------------------------------------------------------------------
# 11. Munic_pios_com_FFPT.csv (mesmo formato do brinco, mas sem autoria clara
#      -> tratado como dado operacional/coleta propria, fonte distinta)
# ---------------------------------------------------------------------------
df = pd.read_csv(BASE / "Munic_pios_com_FFPT.csv", sep=",", encoding="utf-8-sig")
for _, row in df.iterrows():
    raw = str(row["Município"]).strip()
    m = re.match(r"^(.*?)[\-–]\s*([A-Za-z]{2})\s*$", raw)
    if m:
        nome, uf = m.group(1).strip(), m.group(2).upper()
        registra_index(nome, uf)
        ano = extrai_ano(row["Ano de Implementação"])
        add(nome, uf, "Municípios com FFPT (planilha de coleta)", "Dado operacional/coleta própria",
            "levantamento de municípios com FFPT", ano, None)
    else:
        warnings.append(f"Munic_pios_com_FFPT: nao consegui separar UF de '{raw}'")

# ---------------------------------------------------------------------------
# 2. Pereira 2023.csv  -- SEM UF em nenhuma linha; resolvida via indice
#    cruzado (NAO assumimos "todas MG" -- essa premissa do enunciado esta
#    ERRADA, ver relatorio final)
# ---------------------------------------------------------------------------
# Conhecimento geografico adicional para nomes que nao aparecem em nenhum
# outro arquivo do lote (municipios brasileiros unicos, sem homonimo):
CONHECIMENTO_GEOGRAFICO = {
    "Abaeté": "MG",              # unico municipio "Abaeté" no Brasil, em MG
    "Caeté": "MG",                # unico municipio "Caeté" no Brasil, em MG
    "Rio Branco do Sul": "PR",    # municipio da regiao metropolitana de Curitiba
    "Campo Belo": "MG",           # confirmado por NTU 2023 (Campo Belo-MG); unico municipio com esse nome
}
cidade_uf_index.update(CONHECIMENTO_GEOGRAFICO)

df = pd.read_csv(BASE / "Pereira 2023.csv", sep=";", encoding="utf-8-sig")
col_municipio = df.columns[0]  # header truncado por BOM -> "icípio"
pereira_nao_resolvidos = []
for _, row in df.iterrows():
    raw = str(row[col_municipio]).strip()
    uf = cidade_uf_index.get(raw)
    ano = extrai_ano(row["Ano de Implementação"])
    if uf:
        add(raw, uf, "Pereira 2023", "Estudo acadêmico", "estudo de caso (FFPT)", ano, None)
    else:
        pereira_nao_resolvidos.append(raw)
        warnings.append(f"Pereira 2023: UF nao resolvida para '{raw}' -- registro descartado")

# resolve as linhas pendentes de Angelo/Vermander usando o indice (que agora
# ja inclui Pereira-independent sources + conhecimento geografico)
for raw, ano in angelo_sem_uf:
    uf = cidade_uf_index.get(raw)
    if uf:
        add(raw, uf, "Angelo 2023", "Estudo acadêmico", "estudo de caso (FFPT)", ano, None)
    else:
        warnings.append(f"Angelo 2023: UF nao resolvida para '{raw}' -- registro descartado")

for raw, ano in vermander_sem_uf:
    uf = cidade_uf_index.get(raw)
    if uf:
        add(raw, uf, "Vermander 2021", "Estudo acadêmico", "estudo de caso (FFPT, pioneiros)", ano, None)
    else:
        warnings.append(f"Vermander 2021: UF nao resolvida para '{raw}' -- registro descartado")

# ---------------------------------------------------------------------------
# 6. NTU 2023.csv  (Ano de Implementação vem como "set/21" etc.)
#    Correcao: "São Caetano do Sul-SC" e erro de digitacao da fonte -> SP
#    (confirmado por NTU 2025, reportagens_por_municipio e conhecimento geral)
# ---------------------------------------------------------------------------
MESES = {
    "jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
    "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12,
}


def ano_mes_abrev(valor):
    s = str(valor).strip().lower()
    m = re.match(r"^([a-z]{3})/(\d{2})$", s)
    if m:
        yy = int(m.group(2))
        return 2000 + yy if yy < 70 else 1900 + yy
    return extrai_ano(valor)


df = pd.read_csv(BASE / "NTU 2023.csv", sep=";", encoding="utf-8-sig")
for _, row in df.iterrows():
    raw = str(row["Cidade"]).strip()
    m = re.match(r"^(.*?)-([A-Za-z]{2})\s*$", raw)
    if not m:
        warnings.append(f"NTU 2023: nao consegui separar UF de '{raw}'")
        continue
    nome, uf = m.group(1).strip(), m.group(2).upper()
    if nome == "São Caetano do Sul" and uf == "SC":
        uf = "SP"
        warnings.append("NTU 2023: corrigido 'São Caetano do Sul-SC' -> SP (erro de digitação na fonte original; confirmado por NTU 2025 e reportagens)")
    ano = ano_mes_abrev(row["Ano de Implementação"])
    add(nome, uf, "NTU 2023", "Relatório institucional", "estudo de caso (relatório NTU)", ano, None)

# ---------------------------------------------------------------------------
# 7. NTU 2025 - TZ maiores cidades.csv
# ---------------------------------------------------------------------------
df = pd.read_csv(BASE / "NTU 2025 - TZ maiores cidades.csv", sep=";", encoding="utf-8-sig")
fonte_citacao_ntu2025 = str(df["Fonte"].iloc[0]).strip()
for _, row in df.iterrows():
    raw = str(row["Cidade"]).strip()
    m = re.match(r"^(.*?)-([A-Za-z]{2})\s*$", raw)
    if not m:
        warnings.append(f"NTU 2025: nao consegui separar UF de '{raw}'")
        continue
    nome, uf = m.group(1).strip(), m.group(2).upper()
    ano = extrai_ano(row["Data_inicio"])
    add(nome, uf, "NTU 2025 - TZ maiores cidades", "Relatório institucional",
        f"cidade com TZ universal e população >100 mil hab. (pop. {row['Populacao']})",
        ano, fonte_citacao_ntu2025)

# ---------------------------------------------------------------------------
# 8. reportagens_por_municipio.csv
# ---------------------------------------------------------------------------
df = pd.read_csv(BASE / "reportagens_por_municipio.csv", sep=";", encoding="utf-8-sig")
for _, row in df.iterrows():
    nome, uf = str(row["Município"]).strip(), str(row["UF"]).strip().upper()
    veiculo = str(row["Veículo"]).strip()
    ano = extrai_ano(row["Data"])
    add(nome, uf, f"Reportagem — {veiculo}", "Reportagem", row["Tema"], ano, row["URL"])

# ---------------------------------------------------------------------------
# 9. tz_bairros_perifericos.csv  (parse manual: 1 linha tem ';' dentro do
#    campo Escopo, quebrando o parser padrao de CSV)
# ---------------------------------------------------------------------------
with open(BASE / "tz_bairros_perifericos.csv", encoding="utf-8-sig") as f:
    linhas = [l.rstrip("\n").rstrip("\r") for l in f if l.strip()]
header = linhas[0].split(";")
for linha in linhas[1:]:
    campos = linha.split(";")
    if len(campos) > len(header):
        # junta os campos extras de volta na coluna "Escopo (periférico)" (indice 2)
        campos = campos[:2] + [";".join(campos[2:2 + (len(campos) - len(header) + 1)])] + campos[2 + (len(campos) - len(header) + 1):]
    municipio, uf, escopo, inicio, status, confianca, fonte = campos
    ano = extrai_ano(inicio)
    descricao = escopo + (f" [status no cofre: {status}]" if status else "")
    link = fonte if fonte.startswith("http") else None
    add(municipio, uf, "tz_bairros_perifericos (coleta própria)", "Dado operacional/coleta própria",
        descricao, ano, link if link else fonte)

# ---------------------------------------------------------------------------
# 10. tz_fim_de_semana.csv
# ---------------------------------------------------------------------------
df = pd.read_csv(BASE / "tz_fim_de_semana.csv", sep=";", encoding="utf-8-sig")
for _, row in df.iterrows():
    nome, uf = str(row["Município"]).strip(), str(row["UF"]).strip().upper()
    partes_desc = [str(row["Dias"]).strip()]
    if pd.notna(row.get("Escopo")):
        partes_desc.append(str(row["Escopo"]))
    if pd.notna(row.get("Programa")):
        partes_desc.append(str(row["Programa"]))
    if pd.notna(row.get("Status no cofre")):
        partes_desc.append(f"[status no cofre: {row['Status no cofre']}]")
    descricao = " — ".join(partes_desc)
    ano = extrai_ano(row["Início"])
    link = row["Fonte"] if pd.notna(row["Fonte"]) else None
    add(nome, uf, "tz_fim_de_semana (coleta própria)", "Dado operacional/coleta própria",
        descricao, ano, link)

# ---------------------------------------------------------------------------
# Salva JSON
# ---------------------------------------------------------------------------
crosswalk_ordenado = {k: crosswalk[k] for k in sorted(crosswalk.keys())}
OUT.parent.mkdir(parents=True, exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(crosswalk_ordenado, f, ensure_ascii=False, indent=2)

total_municipios = len(crosswalk_ordenado)
total_entradas = sum(len(v) for v in crosswalk_ordenado.values())

print(f"Municipios distintos: {total_municipios}")
print(f"Entradas de fonte no total: {total_entradas}")
print(f"Arquivo salvo em: {OUT}")
print()
print("=== WARNINGS ===")
for w in warnings:
    print("-", w)
