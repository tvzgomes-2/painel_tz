# -*- coding: utf-8 -*-
"""
regressao_premio_pendular.py — testa se o "prêmio do pendular" achado nos
microdados do Censo 2022 sobrevive a controles de composição e a efeito fixo de
município.

======================================================================
O QUE ESTÁ SENDO TESTADO, E POR QUÊ
======================================================================
O achado bruto (09/09/2026, registrado no Diário de pesquisa) é que o rendimento
de quem trabalha em OUTRO município é maior que o de quem trabalha no próprio, na
mesma direção em todas as posições de arranjo: polo 1,37× · isolado 1,27× ·
co-polo 1,21× · satélite 1,18×. Isso contraria a leitura corrente de que a
pendularidade é do trabalhador mais pobre.

Uma razão média não é um prêmio. Duas explicações rivais precisam ser eliminadas
antes de a diferença poder ser chamada de prêmio do deslocamento:

  (1) COMPOSIÇÃO DA PESSOA. Quem sai do município pode ser mais escolarizado,
      mais velho, ocupado em setor e posição melhor pagos. Aí a diferença é de
      quem a pessoa é, não de para onde ela vai. Controles: instrução, idade,
      idade², sexo, cor ou raça, grande grupo ocupacional, atividade, posição na
      ocupação e carteira assinada.

  (2) COMPOSIÇÃO DO MUNICÍPIO. Município rico exporta trabalhador e paga mais a
      quem fica. Comparar pendulares de um município com não-pendulares de outro
      mistura as duas coisas. Solução: EFEITO FIXO DE MUNICÍPIO DE RESIDÊNCIA —
      o coeficiente passa a comparar apenas vizinhos, gente que mora no MESMO
      município e trabalha dentro ou fora dele.

A referência é deliberadamente estreita: quem trabalha FORA DE CASA no próprio
município (P1120 = 2). Quem trabalha EM CASA (P1120 = 1) não se desloca e entra
só como categoria separada de robustez — jogá-lo na referência mistura "não sai
do município" com "não sai de casa", que são coisas diferentes.

O que este script NÃO faz: não estabelece causalidade. Mesmo com efeito fixo, a
escolha de trabalhar fora é da pessoa (seleção em característica não observada:
disposição, rede de contatos, qualificação não medida pela escolaridade). O
resultado é uma associação condicional, e é assim que deve ser escrito.

======================================================================
DADO DE ACESSO CONTROLADO
======================================================================
⚠️ A entrada é a versão personalizada e rastreável dos microdados, vinculada ao
termo de compromisso assinado. Este script produz APENAS coeficientes agregados.
Nem o cache intermediário (`_cache_regressao/`) nem qualquer saída em nível de
pessoa ou de área de ponderação entram no pacote de replicação. O que pode ser
depositado é este script e a tabela de coeficientes.

======================================================================
COMO USAR — DUAS ETAPAS
======================================================================
  1) python regressao_premio_pendular.py --extrair
        Lê a tabela Pessoas de dentro do .zip, uma UF por vez, em blocos, aplica
        o filtro de universo e guarda em `_cache_regressao/PESSOAS_<UF>.npz`
        apenas as ~12 colunas necessárias, como inteiros pequenos. Checkpoint por
        UF: UF já extraída é pulada. Nunca descompacta os ~3,5 GB.

  2) python regressao_premio_pendular.py --estimar
        Roda sobre o cache (~300 MB, não sobre os 3,5 GB). Permite re-especificar
        o modelo sem reler o dado bruto — que é o ponto de separar as etapas.

======================================================================
COMO A CONTA É FEITA (e por que não é statsmodels)
======================================================================
São ~5.570 efeitos fixos de município e milhões de linhas: a matriz de desenho
com dummies de município não cabe em memória. Usa-se a transformação within
(Frisch-Waugh-Lovell) com pesos, em três passagens sobre o cache:

  passagem 1 — média ponderada de y e de cada X DENTRO de cada município
  passagem 2 — acumula S_xx = Σ w·(x−x̄_g)(x−x̄_g)' e S_xy, e resolve β
  passagem 3 — acumula o "meat" do sanduíche por município, para erro-padrão
                agrupado (clusterizado) no município

Erro-padrão agrupado no município é o certo aqui: pessoas do mesmo município
compartilham mercado de trabalho local, e o tratamento é definido em relação a
esse município. Erro-padrão comum superestimaria a precisão.
"""
import os
import sys
import glob
import zipfile
import numpy as np
import pandas as pd

# ---------------------------------------------------------------- caminhos
V = r"C:\Users\HOME\OneDrive\doutorado\03 - Dados\_data"
ZIP = (r"C:\Users\HOME\Downloads\07_Academico\Censo2022_Microdados"
       r"\microdados_censo_amostra_2022_csv_20260908_140041.zip")
# Sobreponíveis por variável de ambiente, para o script rodar fora da máquina do
# autor sem edição de código (editar caminho a mão já gravou caminho de sandbox
# na cópia do cofre uma vez).
V = os.environ.get("TZ_DATA", V)
ZIP = os.environ.get("CENSO_MICRO_ZIP", ZIP)
BASE_MUN = os.path.join(V, "Base Municipal v3", "base_municipal_v3.csv")
# O cache guarda LINHA DE PESSOA do dado de acesso controlado. Por isso mora ao
# lado do zip de origem, em Downloads, e NÃO dentro do OneDrive: pôr derivado em
# nível de pessoa numa pasta que sincroniza para a nuvem é o mesmo problema de
# custódia que o termo de compromisso trata. As saídas agregadas (coeficientes)
# vão para o cofre normalmente.
CACHE = os.environ.get("CENSO_MICRO_CACHE",
                       os.path.join(os.path.dirname(ZIP), "_cache_regressao"))
OUT = os.path.join(V, "Censo2022_Microdados", "agregados")

FORCAR = False
BLOCO = 400_000
# Versão do universo de análise, gravada no NOME do arquivo de cache.
# Mudar a definição do universo (o filtro de _filtrar) exige subir esta
# string: sem isso, o checkpoint reaproveita silenciosamente um cache
# construído com outra amostra, e o modelo roda sobre dado errado sem
# erro nenhum. Nada é apagado -- o cache antigo só deixa de ser lido.
#   v1 (09/09/2026) -- exigia P1000 em {1,2}, o que sem intenção
#                      restringia a amostra a empregados. Descartada.
#   v2 (09/09/2026) -- todos os ocupados de 14 a 70 anos com rendimento
#                      do trabalho positivo e local de trabalho declarado.
VERSAO_CACHE = "v2"

# ---------------------------------------------------------------- variáveis
COLS = ["P0080", "P0111", "P1120", "P0160", "P0181", "P0210", "P0760",
        "P1000", "P1020", "P1030", "P1040", "P1080", "P1110"]

# Categorias FIXAS. Não derivar do dado: se um bloco não tiver uma categoria, a
# matriz de desenho mudaria de forma entre blocos e as somas acumuladas somariam
# colunas diferentes. Erro silencioso e fatal.
CAT = {
    "sexo":     [1, 2],                       # P0160
    "cor":      [1, 2, 3, 4, 5],              # P0210 (9 = ignorado, excluído)
    "instr":    [1, 2, 3, 4, 5, 6, 7],        # P0760 (8/9/90x = ignorado, excl.)
    "ocup":     list(range(1, 12)),           # P1040 grandes grupos
    "ativ":     list(range(1, 24)),           # P1030 atividade
    "posicao":  list(range(1, 11)),           # P1020 posição na ocupação
    "carteira": [1, 2],                       # P1000
}
REF = {"sexo": 1, "cor": 1, "instr": 5, "ocup": 5, "ativ": 7, "posicao": 1,
       "carteira": 1}   # categoria omitida de cada bloco de dummies


def _uf_de(nome):
    """Extrai o CÓDIGO NUMÉRICO da UF do nome do arquivo (Pessoas_11_controlado.csv
    -> "11"). Não procurar sigla: o nome do arquivo do IBGE não a tem, e uma versão
    anterior desta função devolvia "PE" para as 27 UFs (os dois primeiros caracteres
    de "PESSOAS"), o que faria os 27 caches se sobrescreverem em um só."""
    b = os.path.basename(nome)
    for p in b.replace(".", "_").split("_"):
        if len(p) == 2 and p.isdigit() and 11 <= int(p) <= 53:
            return p
    raise ValueError(f"não consegui identificar a UF em {b}")


# ====================================================================
# ETAPA 1 — extrair o universo de análise para cache compacto
# ====================================================================
def extrair():
    os.makedirs(CACHE, exist_ok=True)
    with zipfile.ZipFile(ZIP) as z:
        pes = [n for n in z.namelist()
               if n.lower().endswith(".csv") and "pesso" in n.lower()]
        if not pes:
            sys.exit("não achei a tabela Pessoas dentro do zip")
        print(f"{len(pes)} arquivo(s) de Pessoas no zip")
        for nome in sorted(pes):
            uf = _uf_de(nome)
            alvo = os.path.join(CACHE, f"PESSOAS_{VERSAO_CACHE}_{uf}.npz")
            if os.path.exists(alvo) and not FORCAR:
                print(f"  {uf}: cache já existe, pulando")
                continue
            print(f"  {uf}: lendo {os.path.basename(nome)} ...", flush=True)
            pedacos, n_lidas = [], 0
            leitor = pd.read_csv(z.open(nome), sep=";", encoding="latin-1",
                                 usecols=COLS, dtype=str, chunksize=BLOCO,
                                 low_memory=False)
            for ch in leitor:
                n_lidas += len(ch)
                pedacos.append(_filtrar(ch))
            d = pd.concat([p for p in pedacos if len(p)], ignore_index=True)
            # grava em temporário e só então renomeia: se a rodada for
            # interrompida no meio da escrita, o .npz truncado que sobra passaria
            # no teste de "arquivo existe" do checkpoint e seria lido como bom.
            tmp = alvo + ".parcial"
            np.savez_compressed(tmp, **{c: d[c].to_numpy() for c in d.columns})
            os.replace(tmp + ".npz" if os.path.exists(tmp + ".npz") else tmp, alvo)
            print(f"     {n_lidas} linhas lidas -> {len(d)} no universo "
                  f"({len(d)/max(n_lidas,1)*100:.1f}%)")
    print(f"\ncache em: {CACHE}")


def _filtrar(ch):
    """Aplica o universo de análise e devolve colunas compactas."""
    num = lambda c: pd.to_numeric(ch[c], errors="coerce")
    w = num("P0111")
    d = pd.DataFrame({
        "mun":  num("P0080"),
        "w":    w,
        "loc":  num("P1120"),
        "sexo": num("P0160"),
        "idade": num("P0181"),
        "cor":  num("P0210"),
        "instr": num("P0760"),
        "carteira": num("P1000"),
        "posicao": num("P1020"),
        "ativ": num("P1030"),
        "ocup": num("P1040"),
        "renda_trab": num("P1080"),
        "renda_tot": num("P1110"),
    })
    # universo: peso válido; ocupado com local de trabalho declarado em casa /
    # no próprio município / em outro município (4 = outro país e 5 = mais de um
    # ficam fora: não há "o" município de trabalho); idade de 14 a 70; renda do
    # trabalho positiva; e todas as covariáveis em categoria válida.
    m = (d["w"] > 0) & d["loc"].isin([1, 2, 3])
    m &= d["idade"].between(14, 70)
    m &= d["renda_trab"] > 0
    # ⚠️ "carteira" (P1000) fica FORA do filtro de universo, de propósito. Uma
    # versão anterior a incluía junto com as outras covariáveis, e o efeito
    # colateral era grave e invisível: P1000 vem em BRANCO para militar,
    # servidor estatutário, empregador, conta própria e trabalhador familiar
    # auxiliar -- para quem a pergunta "tem carteira assinada?" não se aplica.
    # Exigir P1000 em {1,2} apagava todos esses do universo, e a análise virava,
    # sem aviso, "somente empregados". O sintoma foi que as dummies posicao_7 a
    # posicao_10 saíram como colineares: eram colunas vazias. Carteira segue
    # guardada no cache (com 0 para o branco) para quem queira especificar sem
    # P1020, mas não restringe a amostra.
    for k, cats in CAT.items():
        if k == "carteira":
            continue
        m &= d[k].isin(cats)
    d = d[m].copy()
    if d.empty:
        return d
    d["carteira"] = d["carteira"].where(d["carteira"].isin([1, 2]), 0)
    d["mun"] = d["mun"].astype("int32")
    for c in ("loc", "sexo", "cor", "instr", "carteira", "posicao", "ativ", "ocup"):
        d[c] = d[c].astype("int8")
    d["idade"] = d["idade"].astype("int8")
    d["w"] = d["w"].astype("float32")
    d["renda_trab"] = d["renda_trab"].astype("float32")
    d["renda_tot"] = d["renda_tot"].astype("float32")
    return d


# ====================================================================
# ETAPA 2 — estimar
# ====================================================================
def _nomes_colunas(por_posicao):
    nomes = ["sai", "trab_em_casa", "idade", "idade2"]
    # "carteira" (P1000) NÃO entra: P1020 (posição na ocupação) já distingue
    # "empregado COM carteira" de "empregado SEM carteira" em 6 das suas 10
    # categorias, e as outras 4 (militar/estatutário, empregador, conta própria,
    # trabalhador familiar) determinam a resposta. A dummy de carteira é
    # combinação linear exata das de posição -- a primeira rodada morreu em
    # "Singular matrix" exatamente por isso. Fica guardada no cache para quem
    # quiser especificar sem P1020.
    for k in ("sexo", "cor", "instr", "ocup", "ativ", "posicao"):
        for c in CAT[k]:
            if c != REF[k]:
                nomes.append(f"{k}_{c}")
    if por_posicao:
        # interação do tratamento com a posição no arranjo; "isolado" é a base
        for p in ("polo", "co-polo", "satelite"):
            nomes.append(f"sai_x_{p}")
    return nomes


def _montar(d, nomes, por_posicao, pos_de_mun):
    """Matriz de desenho float64 na ordem EXATA de `nomes`. A ordem é fixa e não
    depende do conteúdo do bloco -- ver comentário em CAT."""
    n = len(d["loc"])
    X = np.zeros((n, len(nomes)), dtype=np.float64)
    idx = {c: i for i, c in enumerate(nomes)}
    sai = (d["loc"] == 3).astype(np.float64)
    X[:, idx["sai"]] = sai
    X[:, idx["trab_em_casa"]] = (d["loc"] == 1).astype(np.float64)
    idade = d["idade"].astype(np.float64)
    X[:, idx["idade"]] = idade
    X[:, idx["idade2"]] = idade ** 2 / 100.0     # /100 só para escala legível
    for k in ("sexo", "cor", "instr", "ocup", "ativ", "posicao"):
        v = d[k]
        for c in CAT[k]:
            if c != REF[k]:
                X[:, idx[f"{k}_{c}"]] = (v == c).astype(np.float64)
    if por_posicao:
        p = pd.Series(d["mun"]).map(pos_de_mun).fillna("isolado").to_numpy()
        for q in ("polo", "co-polo", "satelite"):
            X[:, idx[f"sai_x_{q}"]] = sai * (p == q)
    return X


def _carregar(f, cols=None):
    z = np.load(f)
    cols = cols or z.files
    return {k: z[k] for k in cols}


LINHAS_POR_BLOCO = 250_000      # limita o pico de memória da matriz de desenho


def _colunas_de_rank_cheio(Sxx, nomes, tol=1e-10):
    """Índices de um subconjunto de colunas com rank cheio, na ordem de `nomes`.

    Método: Cholesky incremental com tolerância RELATIVA por coluna, que é o que
    R e Stata fazem. Para a coluna candidata j, calcula quanto da variância dela
    sobra depois de projetada nas colunas já aceitas; se sobra praticamente nada,
    ela é combinação linear das anteriores e sai. Como Sxx entra escalonada pela
    diagonal (matriz de correlação), a variância original de cada coluna é 1 e a
    tolerância não depende de unidade.

    ⚠️ Uma primeira versão desta função usava o NÚMERO DE CONDIÇÃO da submatriz
    acumulada como critério, e isso está errado: o número de condição piora
    monotonicamente conforme colunas legítimas entram, então, a partir de certo
    ponto, TODA coluna seguinte era rejeitada. Na prática ela descartou
    'posicao_8' (empregador), 'posicao_9' (conta própria) e 'posicao_10'
    (trabalhador familiar) -- categorias grandes e não colineares, cuja remoção
    contamina o coeficiente de interesse, porque posição na ocupação é um dos
    determinantes fortes de rendimento. Critério cumulativo não serve para
    detectar colinearidade de coluna.

    A ordem importa: as primeiras colunas de `nomes` são as de interesse ('sai' e
    as interações), então, em caso de dependência, a coluna descartada é sempre
    uma de controle -- nunca o tratamento.
    """
    d = np.sqrt(np.diag(Sxx))
    d[d == 0] = 1.0
    R = Sxx / np.outer(d, d)
    manter, L = [], np.zeros((0, 0))
    for j in range(len(nomes)):
        if len(manter) == 0:
            resto = R[j, j]
        else:
            v = np.linalg.solve(L, R[np.ix_(manter, [j])]).ravel()
            resto = R[j, j] - v @ v
        if resto <= tol:
            continue
        # estende o fator de Cholesky com a nova coluna
        m = len(manter)
        Lnovo = np.zeros((m + 1, m + 1))
        Lnovo[:m, :m] = L
        if m:
            Lnovo[m, :m] = v
        Lnovo[m, m] = np.sqrt(resto)
        L = Lnovo
        manter.append(j)
    return manter


def _blocos(d, nomes, por_posicao, pos_de_mun, cod_de_mun, y_col):
    """Gera (y, X, w, codigos_de_municipio) em blocos de linhas. Blocar é o que
    mantém o pico de memória em ~130 MB: São Paulo tem 1,08 milhão de pessoas no
    universo e a matriz de desenho inteira dessa UF passaria de 500 MB, sem contar
    as cópias da transformação within."""
    n = len(d["mun"])
    for a in range(0, n, LINHAS_POR_BLOCO):
        b = min(a + LINHAS_POR_BLOCO, n)
        pedaco = {k: v[a:b] for k, v in d.items()}
        y = np.log(pedaco[y_col].astype(np.float64))
        X = _montar(pedaco, nomes, por_posicao, pos_de_mun)
        w = pedaco["w"].astype(np.float64)
        cod = np.searchsorted(cod_de_mun, pedaco["mun"])
        yield y, X, w, cod


def estimar(y_col="renda_trab", por_posicao=False):
    arqs = sorted(glob.glob(os.path.join(CACHE, f"PESSOAS_{VERSAO_CACHE}_*.npz")))
    if not arqs:
        sys.exit("cache vazio -- rodar --extrair primeiro")
    pos_de_mun = {}
    if por_posicao:
        b = pd.read_csv(BASE_MUN, dtype=str, keep_default_na=False, low_memory=False)
        pos_de_mun = dict(zip(b["cod_ibge"].str.strip().astype(int),
                              b["posicao_arranjo"].str.strip()))
    nomes = _nomes_colunas(por_posicao)
    k = len(nomes)

    # índice global de município (as somas por grupo viram bincount, não máscara
    # booleana por município -- com ~5.570 grupos e milhões de linhas, a versão
    # com máscara varre o vetor inteiro uma vez por município)
    muns = np.unique(np.concatenate([np.load(f)["mun"] for f in arqs]))
    G = len(muns)
    print(f"\n{'='*72}")
    print(f"modelo: log({y_col}) ~ sai + controles + efeito fixo de município"
          f"{' + interação com posição no arranjo' if por_posicao else ''}")
    print(f"{k} parâmetros estimados; {G} efeitos fixos de município absorvidos")
    print(f"{'='*72}")

    # ---- passagem 1: médias ponderadas dentro do município --------------
    sw = np.zeros(G); swy = np.zeros(G); swx = np.zeros((G, k))
    n_tot = 0; w_tot = 0.0
    for f in arqs:
        d = _carregar(f)
        for y, X, w, cod in _blocos(d, nomes, por_posicao, pos_de_mun, muns, y_col):
            n_tot += len(y); w_tot += w.sum()
            sw += np.bincount(cod, w, G)
            swy += np.bincount(cod, w * y, G)
            wx = X * w[:, None]
            for jj in range(k):
                swx[:, jj] += np.bincount(cod, wx[:, jj], G)
        del d
    ybar = swy / sw
    xbar = swx / sw[:, None]
    print(f"passagem 1: {n_tot:,} pessoas na amostra, {w_tot:,.0f} representadas")

    # ---- passagem 2: S_xx, S_xy, beta -----------------------------------
    Sxx = np.zeros((k, k)); Sxy = np.zeros(k); Syy = 0.0
    for f in arqs:
        d = _carregar(f)
        for y, X, w, cod in _blocos(d, nomes, por_posicao, pos_de_mun, muns, y_col):
            y -= ybar[cod]
            X -= xbar[cod]
            Xw = X * w[:, None]
            Sxx += Xw.T @ X
            Sxy += Xw.T @ y
            Syy += (w * y * y).sum()
        del d
    manter = _colunas_de_rank_cheio(Sxx, nomes)
    if len(manter) < k:
        fora = [nomes[i] for i in range(k) if i not in manter]
        print(f"⚠️ colinearidade exata: {len(fora)} coluna(s) removida(s) para a "
              f"matriz ter rank cheio -- {fora}")
        print("   (não é conserto cosmético: coluna assim não tem coeficiente "
              "identificado, e deixá-la torna TODOS os coeficientes arbitrários)")
    beta_r = np.linalg.solve(Sxx[np.ix_(manter, manter)], Sxy[manter])
    beta = np.full(k, np.nan)
    beta[manter] = beta_r
    r2 = 1 - (Syy - beta_r @ Sxy[manter]) / Syy
    print(f"passagem 2: R² within = {r2:.4f}")

    # ---- passagem 3: erro-padrão agrupado no município ------------------
    Sxx_inv = np.linalg.inv(Sxx[np.ix_(manter, manter)])
    u = np.zeros((G, len(manter)))
    Xsel = np.array(manter)
    for f in arqs:
        d = _carregar(f)
        for y, X, w, cod in _blocos(d, nomes, por_posicao, pos_de_mun, muns, y_col):
            y -= ybar[cod]
            X -= xbar[cod]
            Xr = X[:, Xsel]
            e = w * (y - Xr @ beta_r)
            contrib = Xr * e[:, None]
            for jj in range(len(manter)):
                u[:, jj] += np.bincount(cod, contrib[:, jj], G)
        del d
    meat = u.T @ u
    dfc = G / max(G - 1, 1)
    V = Sxx_inv @ meat @ Sxx_inv * dfc
    se = np.full(k, np.nan)
    se[manter] = np.sqrt(np.diag(V))
    print(f"passagem 3: erro-padrão agrupado em {G} municípios")

    res = pd.DataFrame({"variavel": nomes, "coef": beta, "se": se})
    res["t"] = res["coef"] / res["se"]
    res["efeito_pct"] = (np.exp(res["coef"]) - 1) * 100
    res["ic95_baixo_pct"] = (np.exp(res["coef"] - 1.96 * res["se"]) - 1) * 100
    res["ic95_alto_pct"] = (np.exp(res["coef"] + 1.96 * res["se"]) - 1) * 100

    chave = ["sai", "trab_em_casa"] + [n for n in nomes if n.startswith("sai_x_")]
    print("\n--- coeficientes de interesse (efeito_pct = variação % do rendimento) ---")
    print(res[res["variavel"].isin(chave)].round(4).to_string(index=False))
    print("\n--- controles (conferência de sinal) ---")
    print(res[~res["variavel"].isin(chave)].round(4).to_string(index=False))

    os.makedirs(OUT, exist_ok=True)
    sfx = f"{y_col}{'_x_posicao' if por_posicao else ''}"
    cam = os.path.join(OUT, f"regressao_premio_pendular_{sfx}.csv")
    res.round(6).to_csv(cam, index=False, encoding="utf-8-sig")
    print(f"\ngravado: {cam}")
    return res


if __name__ == "__main__":
    if "--extrair" in sys.argv:
        extrair()
    elif "--estimar" in sys.argv:
        estimar("renda_trab", por_posicao=False)
        estimar("renda_trab", por_posicao=True)
        estimar("renda_tot", por_posicao=False)
    else:
        print(__doc__)
        print("\nuse --extrair e depois --estimar")
