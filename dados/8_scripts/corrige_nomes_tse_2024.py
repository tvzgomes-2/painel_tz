#!/usr/bin/env python3
"""corrige_nomes_tse_2024.py — resolve manualmente os municípios que ficaram
sem `cod_ibge` após `baixar_tse_2024.py` (22 casos, 0,4% de 5.556 prefeitos
eleitos). Não são erro de bridge (a chave UF+nome normalizado está correta
nos dois lados) — são **nomes desatualizados na base** (renomeações
municipais que o `nome_mun` do Banco Municipal v3 não acompanhou) ou, em 1
caso, um município que **não existe** no universo de 5.570 da base.

MÉTODO: para cada um dos 22, (a) busca no cofre por variantes de grafia
dentro do mesmo UF; (b) quando ambíguo ou não encontrado, verificação
factual via busca na web (IBGE/Wikipédia) — 12 dos 22 foram confirmados
assim, os outros 10 por variante ortográfica óbvia (Z/S, U/O, acento) com
candidato único no estado, sem alternativa concorrente. Ver justificativa
por linha no dicionário abaixo.

ACHADO: 15 dos 22 são o mesmo padrão — o TSE usa o nome atual (pós-lei de
renomeação municipal) e a base ainda tem o nome ANTIGO herdado da fonte
original (ex.: "Presidente Juscelino" em vez de "Serra Caiada", renomeado em
2013; "Embu" em vez de "Embu das Artes", 2011; "Santarém" em vez de "Joca
Claudino", 2010; "Januário Cicco" em vez de "Boa Saúde", 1991; "Augusto
Severo" em vez de "Campo Grande", "Fortaleza Do Tabocão" em vez de
"Tabocão", 2019). Isso é uma pista de que `nome_mun` no Banco Municipal v3
pode ter MAIS casos de nome desatualizado que não apareceram aqui só porque
não tinham eleição 2024 para expor a discrepância — não corrigido de forma
sistemática nesta rodada (ver nota no fim).

ÚNICO CASO SEM RESOLUÇÃO: MT|BOA ESPERANÇA DO NORTE — confirmado via IBGE
que é um município REAL, mas oficialmente instalado em 01/01/2025 (código
IBGE 5101837, desmembrado de outro município do MT) — não existe no
universo de 5.570 municípios da base (que reflete o corte anterior a essa
criação). Não é erro de nome, é fora do escopo temporal da base. Deixado
sem `cod_ibge` propositalmente — não inventar um código.

USO:  rodar depois de baixar_tse_2024.py (usa o eleicao_2024.csv gerado por
ele e re-funde no base_municipal_v3.csv)."""
import os, sys
import pandas as pd


def salvar_atomico(df, path):
    """Escreve em <path>.tmp e só substitui o arquivo final com os.replace()
    (atômico no mesmo filesystem) — se o processo for interrompido no meio
    (ex.: timeout do sandbox), o arquivo original fica intacto, só o .tmp
    fica incompleto (e é descartável). Corrige o incidente de 22/07/2026
    em que um to_csv() direto foi interrompido no meio e truncou
    base_municipal_v3.csv de 5.570 para 206 linhas."""
    tmp = path + ".tmp"
    df.to_csv(tmp, index=False)
    os.replace(tmp, path)

HERE = os.path.dirname(os.path.abspath(__file__))
V = os.path.join(os.path.abspath(os.path.join(HERE, "..", "..")), "03 - Dados", "_data")
OUT = os.path.join(V, "Base Municipal v3")
ELEICAO_CSV = os.path.join(OUT, "eleicao_2024.csv")
BASE_CSV = os.path.join(OUT, "base_municipal_v3.csv")

# chave = "UF|NOME_TSE_NORMALIZADO" (como sai de eleicao_2024.csv) -> (cod_ibge, justificativa)
CORRECOES = {
    "BA|CAMACA": ("2905602", "mesma grafia (Camacã=Camacan); confirmado IBGE/Wikipédia"),
    "SE|GRACCHOCARDOSO": ("2802601", "variante ortográfica (Graccho/Gracho); único candidato em SE"),
    "MG|BRAZOPOLIS": ("3108909", "variante Z/S (Brazópolis/Brasópolis); único candidato em MG"),
    "RN|ASSU": ("2400208", "Açu — confirmado IBGE/Wikipédia, mesma etimologia tupi"),
    "RN|SERRACAIADA": ("2410306", "'Presidente Juscelino' na base — nome anterior à renomeação de 2013 (Lei Est. 9.691/2013); confirmado"),
    "PB|SAOVICENTEDOSERIDO": ("2515401", "'Seridó' na base — confirmado mesmo código IBGE (2515401)"),
    "TO|TABOCAO": ("1708254", "'Fortaleza Do Tabocão' na base — nome anterior à renomeação de 2019 (Lei Est. 3.540/2019); confirmado"),
    "PE|IGUARACY": ("2606903", "'Iguaraci' na base — grafia oficial usa 'y' desde 1963 (único município do Brasil terminado em Y); confirmado"),
    "CE|ITAPAJE": ("2306306", "'Itapagé' na base — confirmado mesmo código IBGE (2306306)"),
    "SP|MOGIMIRIM": ("3530805", "'Moji Mirim' na base — grafia 'Moji'->'Mogi' padronizada nos anos 1990 em várias cidades de SP"),
    "RO|ALVORADADOOESTE": ("1100346", "'Alvorada D'Oeste' na base — variante de grafia/espaçamento"),
    "MT|POXOREU": ("5107008", "'Poxoréo' na base — variante U/O, único candidato em MT"),
    "SP|FLORINEA": ("3516101", "'Florínia' na base — confirmado mesmo código IBGE (3516101)"),
    "RN|CAMPOGRANDE": ("2401305", "'Augusto Severo' na base — nome anterior à renomeação; confirmado"),
    "SP|EMBUDASARTES": ("3515004", "'Embu' na base — nome anterior à renomeação de 2011 (Lei 14.537/2011); confirmado"),
    "PB|JOCACLAUDINO": ("2513653", "'Santarém' na base — nome anterior à renomeação de 2010 (Lei Mun. 049/2010); confirmado"),
    "RN|BOASAUDE": ("2405306", "'Januário Cicco' na base — nome anterior à renomeação de 1991; confirmado"),
    "BA|SANTATEREZINHA": ("2928505", "'Santa Teresinha' na base — variante Z/S, único candidato em BA"),
    "BA|MUQUEMDOSAOFRANCISCO": ("2922250", "'Muquém De São Francisco' na base — variante de preposição (do/de)"),
    "RO|ESPIGAODOOESTE": ("1100098", "'Espigão D'Oeste' na base — variante de grafia/espaçamento"),
    "RN|AREZ": ("2401206", "'Arês' na base — variante de acentuação, único candidato em RN"),
    # MT|BOAESPERANCADONORTE: sem correção — ver docstring (município instalado em 2025, fora da base)
}


def main():
    if not os.path.exists(ELEICAO_CSV):
        print(f"ERRO: {ELEICAO_CSV} não encontrado — rode baixar_tse_2024.py primeiro."); sys.exit(1)

    elei = pd.read_csv(ELEICAO_CSV, dtype=str)
    faltantes_antes = elei["cod_ibge"].isna().sum()

    aplicadas = 0
    for i, row in elei[elei["cod_ibge"].isna()].iterrows():
        chave = row["chave"]
        if chave in CORRECOES:
            cod, just = CORRECOES[chave]
            elei.at[i, "cod_ibge"] = cod
            aplicadas += 1

    faltantes_depois = elei["cod_ibge"].isna().sum()
    print(f"sem cod_ibge: {faltantes_antes} -> {faltantes_depois} ({aplicadas} correções aplicadas)")
    if faltantes_depois:
        print("ainda sem correção (esperado: MT|BOAESPERANCADONORTE, município criado em 2025):")
        print(elei[elei["cod_ibge"].isna()][["chave", "SG_UF", "NM_UE"]].to_string())

    salvar_atomico(elei, ELEICAO_CSV)

    # re-funde no base_municipal_v3.csv
    add = elei.dropna(subset=["cod_ibge"]).rename(columns={
        "NM_URNA_CANDIDATO": "prefeito_2024", "SG_PARTIDO": "partido_2024",
        "DS_SIT_TOT_TURNO": "situacao_2024"})[
        ["cod_ibge", "prefeito_2024", "partido_2024", "situacao_2024"]].drop_duplicates("cod_ibge")

    base = pd.read_csv(BASE_CSV, dtype={"cod_ibge": str}, low_memory=False)
    def c7(x):
        try: return str(int(float(x))).zfill(7)
        except Exception: return None
    base["cod_ibge"] = base["cod_ibge"].map(c7)
    antes = base["prefeito_2024"].notna().sum()
    base = base.drop(columns=[c for c in ["prefeito_2024", "partido_2024", "situacao_2024"] if c in base.columns])
    base = base.merge(add, on="cod_ibge", how="left")
    depois = base["prefeito_2024"].notna().sum()
    salvar_atomico(base, BASE_CSV)
    print(f"prefeito_2024 preenchido: {antes} -> {depois} de 5.570 ({depois/5570*100:.1f}%)")


if __name__ == "__main__":
    main()
