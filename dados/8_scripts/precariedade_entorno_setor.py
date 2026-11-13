# -*- coding: utf-8 -*-
"""
precariedade_entorno_setor.py — baixa os agregados de CARACTERÍSTICAS URBANÍSTICAS
DO ENTORNO DOS DOMICÍLIOS do Censo 2022 por SETOR CENSITÁRIO e monta um índice
composto de precariedade viária.

======================================================================
POR QUE ESTE SCRIPT EXISTE, E O QUE ELE NÃO É
======================================================================
Não vem do microdado da amostra. Vale registrar o porquê, porque a intuição
contrária é forte: (1) o Entorno é instrumento do UNIVERSO, não da amostra — a
tabela de Domicílios dos microdados não tem uma única variável de entorno; e
(2) a geografia mais fina do microdado é ÁREA DE PONDERAÇÃO (D0090/P0090), por
desenho de sigilo — setor censitário não existe ali e não é recuperável.

A fonte certa é pública, não exige termo de compromisso, e pesa ~33 MB:
  Censos/Censo_Demografico_2022/
    Agregados_por_Setores_Censitarios_Caracteristicas_urbanisticas_do_entorno_dos_domicilios/

Três tabelas por setor, todas Brasil inteiro:
  entorno_faces      — contagem de FACES DE QUADRA por característica. É a unidade
                       em que o IBGE coleta o entorno; é o que mais se aproxima de
                       "logradouro" sem precisar de junção espacial com OSM/Overture.
  entorno_domicilios — domicílios por característica do entorno
  entorno_moradores   — moradores por característica do entorno

======================================================================
COMO USAR — DUAS ETAPAS, DE PROPÓSITO
======================================================================
  1) python precariedade_entorno_setor.py            # baixa, descompacta e DESCOBRE
                                                     # os nomes reais das colunas
  2) preencher MAPA_COLUNAS abaixo com o que a etapa 1 imprimiu
  3) python precariedade_entorno_setor.py --indice   # monta o índice

A etapa 1 existe porque programar contra nome de coluna adivinhado já custou três
rodadas perdidas neste projeto (ver a 13ª e 14ª rodada do LEIA-ME dos scripts de
dados). O script se recusa a montar o índice sem mapeamento explícito.

======================================================================
DECISÃO METODOLÓGICA A RESPEITAR — NA ≠ 0
======================================================================
Face rural, rodovia isolada ou área sem questionário de entorno aplicado recebe
NA, nunca 0. Zero significaria "infraestrutura perfeita" e faria o algoritmo ler
área não recenseada como área sem precariedade. É a mesma correção que a v1.1.0
da base de precariedade viária do Zenodo (Passos, 2026) documenta.

⚠️ E uma armadilha do índice composto, medida na base municipal desta pesquisa:
iluminação tem média 97,2% e quase nenhuma variância entre municípios; rampa tem
média 12,7%. Uma média simples dos componentes é dominada por um só. Por isso o
índice sai em DUAS versões — bruta (média das ausências) e padronizada (z-score
por componente) — e o script reporta a variância de cada componente, para a
escolha ser informada e declarada.

Uso em consultoria: o script é genérico por desenho (nada específico da tese).
Sai por setor, por município e — se a malha de setores estiver disponível —
pronto para junção espacial.
"""
import os
import sys
import zipfile
import urllib.parse
import pandas as pd
import requests

BASE_FTP = ("https://ftp.ibge.gov.br/Censos/Censo_Demografico_2022/"
            "Agregados_por_Setores_Censitarios_Caracteristicas_urbanisticas_"
            "do_entorno_dos_domicilios")
ARQUIVOS = {
    "faces":      "Agregados_por_Setor_csv/Agregados_por_setores_entorno_faces_BR.zip",
    "domicilios": "Agregados_por_Setor_csv/Agregados_por_setores_entorno_domicílios_BR.zip",
    "moradores":  "Agregados_por_Setor_csv/Agregados_por_setores_entorno_moradores_BR.zip",
    "dicionario": "dicionarios_de_dados_entorno.zip",
}
DEST = os.environ.get(
    "CENSO_ENTORNO_DIR",
    r"C:\Users\HOME\OneDrive\doutorado\03 - Dados\_data\Censo2022_Entorno")
# CENSO_ENTORNO_DIR existe para o script rodar tambem fora da maquina do autor
# (sandbox/servidor) sem editar o codigo -- editar o caminho a mao ja causou
# um caminho de sandbox ficar gravado na copia do cofre em 09/09/2026.
HEADERS = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")}

# ---------------------------------------------------------------------
# PREENCHER NA ETAPA 2 — nome do componente : nome REAL da coluna de AUSÊNCIA
# (ou par (coluna_com, coluna_total) se a tabela vier em "faces com X")
# ---------------------------------------------------------------------
# Preenchido em 09/09/2026 a partir de dicionario_entorno_faces.xlsx.
# Par (coluna NÃO, coluna SIM). O denominador é SIM + NÃO — a categoria
# "NÃO DECLARADO" fica FORA da conta, não entra como ausência: é justamente a
# disciplina NA ≠ 0. Face sem declaração não é face sem infraestrutura.
MAPA_COLUNAS = {
    "pavimentacao": ("V05407", "V05406"),
    "bueiro":       ("V05410", "V05409"),
    "iluminacao":   ("V05413", "V05412"),
    "calcada":      ("V05422", "V05421"),
}
# Componentes extra, FORA do índice composto, guardados como colunas próprias.
# Aqui a chave é o nome COMPLETO da coluna de saída, não um sufixo: é o que
# permite que uma delas tenha o prefixo "com_" em vez de "aus_".
#
# ⚠️ CORREÇÃO DE SINAL (09/09/2026): "obstáculo na calçada" é a ÚNICA variável
# do bloco em que SIM é a coisa ruim -- nas outras, SIM é a infraestrutura
# presente. Calculada com a mesma fórmula das demais, ela media a AUSÊNCIA de
# obstáculo, isto é, um indicador POSITIVO com nome de negativo, e entraria em
# qualquer soma com o sinal trocado. O erro apareceu na matriz de correlação:
# era o único componente com correlação NEGATIVA contra todos os outros
# (-0,35 com rampa, -0,21 com bueiro). Agora é "com_obstaculo_calcada_pct" e o
# par está invertido de propósito, para que em TODAS as colunas deste script
# valor maior signifique situação pior.
MAPA_EXTRA = {
    "aus_ponto_onibus_pct":      ("V05416", "V05415"),   # ⭐ relevante à tese
    "aus_rampa_cadeirante_pct":  ("V05428", "V05427"),
    "com_obstaculo_calcada_pct": ("V05424", "V05425"),   # invertida (ver acima)
    "aus_via_bicicleta_pct":     ("V05419", "V05418"),
}
COL_SETOR = "COD_SETOR_M22FINAL"
COL_TOTAL_FACES = "V05400"
TABELA_INDICE = "faces"


def baixar():
    os.makedirs(DEST, exist_ok=True)
    for rot, caminho in ARQUIVOS.items():
        nome = os.path.basename(caminho)
        alvo = os.path.join(DEST, nome)
        if os.path.exists(alvo) and os.path.getsize(alvo) > 0:
            print(f"  {rot}: {nome} já no disco ({os.path.getsize(alvo)/1048576:.1f} MB)")
            continue
        url = BASE_FTP + "/" + urllib.parse.quote(caminho)
        print(f"  {rot}: baixando {nome} ...", flush=True)
        r = requests.get(url, headers=HEADERS, timeout=300, stream=True)
        if r.status_code != 200:
            print(f"    FALHOU (status {r.status_code}) — url: {url}")
            continue
        with open(alvo, "wb") as f:
            for ch in r.iter_content(1 << 20):
                f.write(ch)
        print(f"    ok, {os.path.getsize(alvo)/1048576:.1f} MB")
    return True


def descobrir():
    """Descompacta e imprime os nomes REAIS de coluna de cada tabela."""
    relatorio = []
    for rot, caminho in ARQUIVOS.items():
        alvo = os.path.join(DEST, os.path.basename(caminho))
        if not os.path.exists(alvo):
            continue
        pasta = os.path.join(DEST, rot)
        os.makedirs(pasta, exist_ok=True)
        with zipfile.ZipFile(alvo) as z:
            z.extractall(pasta)
            itens = z.namelist()
        print(f"\n===== {rot} =====")
        print(f"  {len(itens)} arquivo(s) no zip: {itens[:6]}")
        relatorio.append(f"===== {rot} =====\n{itens}\n")
        if rot == "dicionario":
            continue
        for it in itens:
            p = os.path.join(pasta, it)
            if not it.lower().endswith((".csv", ".CSV")):
                continue
            for sep in (";", ","):
                try:
                    d = pd.read_csv(p, sep=sep, encoding="latin-1", nrows=3, dtype=str)
                    if d.shape[1] > 1:
                        break
                except Exception:
                    d = None
            if d is None:
                continue
            print(f"  -- {it}: {d.shape[1]} colunas (sep '{sep}')")
            for c in d.columns:
                print(f"       {c}")
            relatorio.append(f"-- {it} (sep '{sep}', {d.shape[1]} col)\n" +
                             "\n".join(f"   {c}" for c in d.columns) + "\n")
    saida = os.path.join(DEST, "_campos_descobertos.txt")
    with open(saida, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(relatorio))
    print(f"\nlista completa gravada em: {saida}")
    print("\nPRÓXIMO PASSO: colar este conteúdo para eu preencher MAPA_COLUNAS e COL_SETOR.")


def indice():
    if not MAPA_COLUNAS or COL_SETOR is None:
        sys.exit("MAPA_COLUNAS/COL_SETOR vazios — rodar a etapa 1 primeiro e preencher.")
    pasta = os.path.join(DEST, TABELA_INDICE)
    csvs = [os.path.join(dp, f) for dp, _, fs in os.walk(pasta) for f in fs if f.lower().endswith(".csv")]
    d = pd.concat([pd.read_csv(x, sep=";", encoding="latin-1", dtype=str, low_memory=False)
                   for x in csvs], ignore_index=True)
    print(f"{TABELA_INDICE}: {len(d)} setores lidos")

    def taxa(col_numerador, col_outro):
        """% de faces na categoria do numerador, sobre SIM+NÃO. NÃO DECLARADO fica
        fora do denominador -- face sem declaração não é face sem infraestrutura
        (disciplina NA ≠ 0). Chama-se "taxa", e não "ausência", porque para
        obstáculo na calçada o numerador é o SIM: ver MAPA_EXTRA."""
        num = pd.to_numeric(d[col_numerador], errors="coerce")
        out = pd.to_numeric(d[col_outro], errors="coerce")
        base = num + out
        return (num / base * 100).where(base > 0)      # NA quando não há face declarada

    P = pd.DataFrame({"cd_setor": d[COL_SETOR]})
    P["faces_no_setor"] = pd.to_numeric(d[COL_TOTAL_FACES], errors="coerce")
    for nome, (cn, cs) in MAPA_COLUNAS.items():
        P[f"aus_{nome}_pct"] = taxa(cn, cs).round(2)
    for coluna, (cn, cs) in MAPA_EXTRA.items():
        P[coluna] = taxa(cn, cs).round(2)

    comp = [f"aus_{k}_pct" for k in MAPA_COLUNAS]
    print("\nvariância de cada componente do índice (% de ausência de faces):")
    print(P[comp].describe().T[["count", "mean", "std", "min", "max"]].round(2).to_string())
    P["ipv_bruto"] = P[comp].mean(axis=1).round(2)
    z = (P[comp] - P[comp].mean()) / P[comp].std()
    P["ipv_padronizado"] = z.mean(axis=1).round(4)
    P["n_componentes_validos"] = P[comp].notna().sum(axis=1)
    P.to_csv(os.path.join(DEST, "ipv_por_setor.csv"), index=False, encoding="utf-8-sig")

    P["cod_ibge"] = P["cd_setor"].astype(str).str[:7]
    # agregação municipal PONDERADA pelo nº de faces do setor -- setor grande pesa mais.
    # Vetorizada (soma de v*w / soma de w, por coluna) em vez de groupby.apply com
    # função Python: mesmo número, mas roda em segundos e não em minutos.
    # O peso é recalculado COLUNA POR COLUNA, ignorando os setores em que aquela
    # coluna é NA -- se usássemos um peso único, um setor sem declaração de calçada
    # entraria no denominador da calçada com peso e sem valor, e puxaria a média
    # do município para baixo. É a mesma disciplina NA ≠ 0, agora na agregação.
    todas = comp + list(MAPA_EXTRA) + ["ipv_bruto", "ipv_padronizado"]
    g = P.groupby("cod_ibge", sort=True)
    mun = pd.DataFrame(index=g.size().index)
    w0 = P["faces_no_setor"].where(P["faces_no_setor"] > 0)
    for col in todas:
        v = P[col]
        w = w0.where(v.notna())
        num = (v * w).groupby(P["cod_ibge"]).sum(min_count=1)
        den = w.groupby(P["cod_ibge"]).sum(min_count=1)
        mun[col] = num / den.where(den > 0)
    mun["n_setores"] = g.size()
    mun["faces_total"] = g["faces_no_setor"].sum()
    # nº de setores em que o componente mais frágil (calçada) pôde ser medido --
    # serve de aviso de cobertura: município com poucos setores declarados tem
    # média municipal frágil mesmo que o valor pareça bem-comportado.
    mun["n_setores_com_calcada"] = P["aus_calcada_pct"].notna().groupby(P["cod_ibge"]).sum()
    mun = mun.round(2).reset_index()
    mun.to_csv(os.path.join(DEST, "ipv_por_municipio.csv"), index=False, encoding="utf-8-sig")
    sem_face = int(P["aus_pavimentacao_pct"].isna().sum())
    print(f"\ncobertura: {len(P)} setores na tabela de faces, dos quais {sem_face} sem "
          f"nenhuma face declarada (ficam NA, não 0)")
    print("  ⚠️ este total é MENOR que o nº de setores do Censo 2022: o questionário de "
          "entorno não foi aplicado em todo setor. Setor ausente desta tabela é setor "
          "SEM MEDIÇÃO, não setor sem precariedade -- não preencher com 0 na junção.")
    print(f"\nipv_por_setor.csv: {len(P)} setores | ipv_por_municipio.csv: {len(mun)} municípios")
    print("\nagregação municipal é PONDERADA pelo nº de faces do setor (setor grande pesa mais)")

if __name__ == "__main__":
    # O bloco __main__ foi perdido em 09/09/2026 quando a reescrita de indice()
    # substituiu um trecho que ia ate o fim do arquivo. Reposto aqui -- e a razao
    # pela qual a rodada com --indice terminou em 2,7 s sem imprimir nada: o
    # script carregava as funcoes e saia sem chamar nenhuma. Licao: patch que
    # troca "funcao inteira" tem de terminar num delimitador conhecido.
    if "--indice" in sys.argv:
        indice()
    else:
        baixar()
        descobrir()
