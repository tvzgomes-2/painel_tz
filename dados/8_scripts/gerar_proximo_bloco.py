#!/usr/bin/env python3
"""
Gera o próximo bloco de municípios para a pesquisa de operadores (Cruzamento GE x TZ).

Reconstrói a lista de municípios já cobertos de forma PERSISTENTE e AUDITÁVEL,
lendo diretamente das fontes de verdade em vez de listas hardcoded reconstruídas
de memória a cada rodada (método antigo, que causou um buraco de 20 municípios
grandes/capitais nunca pesquisados — ver nota do autor em 13/08/2026).

Fontes de verdade combinadas:
1. `municipio_x_operador_consolidado.csv` — os 47 municípios da consolidação original.
2. Todas as tabelas de "Bloco N" já escritas na nota
   `04 - Análises/Consolidação - Operadores reconhecidos por município (ago-2026).md`,
   extraídas por regex do padrão "| Nome/UF (pop...) |" — não depende de manter
   uma lista separada em memória.

Uso:
    python3 gerar_proximo_bloco.py [--n 20]

Saída:
- Imprime os próximos N municípios elegíveis (maior população primeiro).
- Salva `covered_ibge_master.csv` (auditável) com todos os cod_ibge já cobertos e a origem.
"""
import re
import sys
import unicodedata
from pathlib import Path
import pandas as pd

VAULT = Path("/sessions/kind-sleepy-feynman/mnt/doutorado")
NOTE_PATH = VAULT / "04 - Análises" / "Consolidação - Operadores reconhecidos por município (ago-2026).md"
MX_PATH = VAULT / "03 - Dados" / "_data" / "Cruzamento GE x TZ (ago-2026)" / "municipio_x_operador_consolidado.csv"
BASE_PATH = VAULT / "03 - Dados" / "_data" / "Base Municipal v3" / "base_municipal_v3.csv"
OUT_CSV = Path("/tmp/covered_ibge_master.csv")

MEGA_METROS_NORM = {
    "sao paulo", "rio de janeiro", "brasilia", "fortaleza", "salvador",
    "belo horizonte", "manaus", "curitiba", "recife", "goiania",
    "porto alegre", "belem",
}
# Parado a pedido do autor (Task #64) — não incluir na fila até decisão explícita.
PARKED_NORM = {"duque de caxias"}

# Aliases manuais para nomes que a Base Municipal v3 grafa de forma diferente
# do nome usual/IBGE — cada entrada aqui deve ter uma justificativa comentada.
ALIAS_NAME_UF = {
    ("embu das artes", "SP"): ("embu", "SP"),  # base usa "Embu" (nome histórico curto)
}


def norm(s: str) -> str:
    s = str(s).lower()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"[^a-z0-9 ]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def extract_bloco_pairs(text: str):
    pattern = re.compile(r"^\|\s*([A-ZÀ-Ýa-zà-ÿ][^|/]*?)\s*/\s*([A-Z]{2})\s*\(([^)]*)\)\s*\|", re.MULTILINE)
    pairs = set()
    for name, uf, _pop in pattern.findall(text):
        name = name.strip()
        if name.lower() == "município":
            continue
        pairs.add((name, uf))
    return pairs


def build_covered_ibge(base: pd.DataFrame, verbose=True):
    text = NOTE_PATH.read_text(encoding="utf-8")
    pairs = extract_bloco_pairs(text)

    base = base.copy()
    base["nome_norm"] = base["nome_mun"].apply(norm)
    base["key"] = base["nome_norm"] + "|" + base["uf"]

    matched = {}
    unmatched = []
    for name, uf in pairs:
        key_name, key_uf = ALIAS_NAME_UF.get((norm(name), uf), (norm(name), uf))
        key = key_name + "|" + key_uf
        m = base[base["key"] == key]
        if len(m) >= 1:
            matched[int(m.iloc[0]["cod_ibge"])] = f"bloco:{name}/{uf}"
        else:
            unmatched.append((name, uf))

    if unmatched and verbose:
        print("⚠️  Pares não resolvidos (checar alias manual):", unmatched, file=sys.stderr)

    mx = pd.read_csv(MX_PATH, low_memory=False)
    for ibge in mx["cod_ibge"].dropna().astype(int).tolist():
        matched.setdefault(ibge, "consolidado_47")

    return matched


def main():
    n = 20
    if "--n" in sys.argv:
        n = int(sys.argv[sys.argv.index("--n") + 1])

    base = pd.read_csv(BASE_PATH, low_memory=False)
    covered = build_covered_ibge(base)

    pd.DataFrame(
        [{"cod_ibge": k, "origem": v} for k, v in sorted(covered.items())]
    ).to_csv(OUT_CSV, index=False)
    print(f"Total de municípios já cobertos (auditável): {len(covered)} -> {OUT_CSV}")

    base["nome_norm"] = base["nome_mun"].apply(norm)
    filt = base[base["munic_onibus_intramun_2020"] == 1].copy()
    filt = filt[~filt["cod_ibge"].isin(covered.keys())]
    filt = filt[~filt["nome_norm"].isin(MEGA_METROS_NORM | PARKED_NORM)]
    filt = filt.sort_values("pop_2022", ascending=False)

    print(f"Total ainda elegível (ônibus intramunicipal, não coberto, não mega-metro): {len(filt)}")
    print(filt[["nome_mun", "uf", "pop_2022", "cod_ibge"]].head(n).to_string(index=False))


if __name__ == "__main__":
    main()
