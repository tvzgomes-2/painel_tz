#!/usr/bin/env python3
"""baixar_tse_2024.py — Eleições municipais 2024 (TSE, dados abertos): prefeito
ELEITO e partido por município. Baixa o pacote de candidaturas, filtra os eleitos
ao cargo de Prefeito e integra ao v3. Rode na SUA máquina.

Fonte: https://dadosabertos.tse.jus.br/dataset/candidatos-2024
Pacote: https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_2024.zip
  -> contém consulta_cand_2024_BRASIL.csv (sep ';', encoding latin-1).

USO:  python3 baixar_tse_2024.py
Saídas: _data/TSE/consulta_cand_2024.zip (bruto) + eleicao_2024.csv
        e colunas no base_municipal_v3.csv: prefeito_2024, partido_2024,
        situacao_2024 (turno em que foi eleito).
Ponte TSE→IBGE por nome (uf|nome normalizado), reaproveitando o PIB como
dicionário de código; casos não casados ficam sem preenchimento (conferir).

⚠️⚠️⚠️ AUDITORIA (22/07/2026) — 3 bugs encontrados e corrigidos nesta versão,
a partir da checagem pedida pelo autor sobre por que `prefeito_2024` vinha
vazio para os 7 municípios do Grande ABC. Achado: não era ausência pontual —
2.132/5.570 municípios (38%) tinham a coluna preenchida, e a distribuição por
UF ia de 0% (SP, RJ, MG, RS, SC, MT, MS, DF, AP, RR) a ~100% (BA, CE, GO, MA,
PE, TO, AM, AC, ES, PA, AL, PI, SE, RO) — um padrão que não é aleatório, é
assinatura de bug de chave de junção. Três causas, todas na versão anterior
deste script:
  1. **Chave UF errada.** O bridge (ramo sem `/tmp/v3src/pib_2020.csv`) busca
     a 1ª coluna da base cujo nome esteja em `("uf","sigla_uf","nome_uf")` —
     como `nome_uf` (nome por extenso, ex. "SÃO PAULO") aparece ANTES de `uf`
     (sigla, "SP") na ordem de colunas do CSV, o `next()` pegava `nome_uf` e
     truncava as 2 primeiras letras do NOME por extenso como se fosse a
     sigla ("SÃO PAULO"[:2] = "SÃ", não "SP"). Só "casava" nos 14 estados em
     que as 2 primeiras letras do nome por extenso coincidem com a sigla
     oficial (Bahia→BA, Ceará→CE, Goiás→GO, Maranhão→MA, Pernambuco→PE,
     Tocantins→TO, Amazonas→AM, Acre→AC, Espírito Santo→ES, Pará→PA,
     Alagoas→AL, Piauí→PI, Sergipe→SE, Rondônia→RO) — e ainda causava
     colisão falsa em Paraná/Pará e Paraíba/Pará (ambos truncam para "PA").
     Corrigido: usar a coluna `uf` (sigla) diretamente, sem heurística de nome.
  2. **Filtro de situação por substring.** `DS_SIT_TOT_TURNO.str.contains
     ("ELEITO")` também casa "NÃO ELEITO" (contém a substring "ELEITO") — de
     30.490 candidatos a prefeito "capturados", 19.354 eram NÃO ELEITOS.
     Corrigido: comparação exata (`== "ELEITO"`). Isso também resolve os
     ~100 municípios de 2º turno corretamente: o candidato eleito no 2º turno
     tem uma linha própria (NR_TURNO=2) com DS_SIT_TOT_TURNO="ELEITO" no
     mesmo arquivo — não é preciso tratar 2º turno à parte (conferido com
     São Paulo capital: Ricardo Nunes aparece com NR_TURNO=2 / ELEITO,
     Guilherme Boulos com NR_TURNO=1/"2º TURNO" e NR_TURNO=2/"NÃO ELEITO").
  3. **Filtro de cargo por substring.** `DS_CARGO.str.contains("PREFEITO")`
     também casa "VICE-PREFEITO". Combinado com o bug 2, o `drop_duplicates
     ("chave", keep="first")` podia manter a linha do VICE-prefeito eleito
     em vez do prefeito, dependendo da ordem do arquivo — sem forma de saber,
     sem reprocessar, quantos dos 2.132 preenchidos eram na really vice.
     Corrigido: comparação exata (`== "PREFEITO"`).
Os três bugs se somavam: mesmo nos ~2.132 municípios "preenchidos" antes da
correção, não há garantia de que o nome fosse do prefeito (podia ser vice) —
não é só uma lacuna de cobertura, é um problema de correção do dado já
gravado. Reexecutado com os 3 fixes; ver comparação de cobertura no fim do
log de execução."""
import urllib.request, os, zipfile, io, re, unicodedata, glob, pandas as pd, numpy as np
HERE=os.path.dirname(os.path.abspath(__file__))
V=os.path.join(os.path.abspath(os.path.join(HERE,"..","..")),"03 - Dados","_data")
TSE=os.path.join(V,"TSE"); OUT=os.path.join(V,"Base Municipal v3")
URL="https://cdn.tse.jus.br/estatistica/sead/odsele/consulta_cand/consulta_cand_2024.zip"
def c7(x):
    try: return str(int(float(x))).zfill(7)
    except: return None
def norm(s):
    s=unicodedata.normalize("NFKD",str(s)).encode("ascii","ignore").decode()
    return re.sub(r'[^A-Z0-9]','',s.upper())

os.makedirs(TSE,exist_ok=True)
zpath=f"{TSE}/consulta_cand_2024.zip"
if not os.path.exists(zpath):
    print("baixando TSE consulta_cand_2024.zip (~grande)..."); urllib.request.urlretrieve(URL,zpath)
with zipfile.ZipFile(zpath) as z:
    nome=next((n for n in z.namelist() if "BRASIL" in n.upper() and n.lower().endswith(".csv")),None)
    if not nome:  # fallback: concatena por UF
        nome=[n for n in z.namelist() if n.lower().endswith(".csv")]
    with z.open(nome if isinstance(nome,str) else nome[0]) as fh:
        d=pd.read_csv(fh,sep=";",encoding="latin-1",dtype=str)
d.columns=[c.strip().upper() for c in d.columns]
# filtra Prefeito ELEITO — comparação EXATA (não .contains): "PREFEITO" casaria
# "VICE-PREFEITO" e "ELEITO" casaria "NÃO ELEITO" por substring (bugs 2 e 3
# da auditoria de 22/07/2026, documentados no cabeçalho). O candidato eleito
# no 2º turno tem sua própria linha ELEITO (NR_TURNO=2) — não precisa de
# tratamento à parte.
cargo=d["DS_CARGO"].str.upper()=="PREFEITO"
elt=d["DS_SIT_TOT_TURNO"].str.upper()=="ELEITO"
p=d[cargo & elt].copy()
p["chave"]=p["SG_UF"]+"|"+p["NM_UE"].map(norm)
elei=p[["chave","SG_UF","NM_UE","NM_URNA_CANDIDATO","SG_PARTIDO","DS_SIT_TOT_TURNO"]].drop_duplicates("chave")
dup=p["chave"].duplicated().sum()
if dup:
    print(f"  ⚠️ {dup} chaves com mais de 1 'PREFEITO ELEITO' (coligação/registro duplicado?) — mantida a 1ª")

# ponte nome->código via PIB (tem código IBGE + "Nome (UF)")
pib=glob.glob("/tmp/v3src/pib_2020.csv")
if pib:
    b=pd.read_csv(pib[0],dtype=str); m=b["municipio"].str.extract(r'^(.*)\((\w{2})\)\s*$')
    b["chave"]=m[1]+"|"+m[0].str.strip().map(norm); b["cod_ibge"]=b["cod"].map(c7)
    bridge=b[["chave","cod_ibge"]].dropna().drop_duplicates("chave")
else:  # usa a própria base v3 (cod_ibge + sigla UF real, coluna "uf") como ponte
    # bug 1 da auditoria: a versão anterior escolhia a 1ª coluna entre
    # ("uf","sigla_uf","nome_uf") na ORDEM do CSV — como "nome_uf" (nome por
    # extenso) vem antes de "uf" (sigla) no base_municipal_v3.csv, pegava o
    # nome por extenso e truncava as 2 primeiras letras como se fosse sigla
    # (ex.: "SÃO PAULO"[:2]="SÃ" != "SP") — só casava nos ~14 estados em que
    # a sigla coincide com o início do nome por extenso. Agora usa a coluna
    # `uf` (sigla de 2 letras já correta) diretamente, sem heurística.
    bv=pd.read_csv(f"{OUT}/base_municipal_v3.csv",dtype={"cod_ibge":str},low_memory=False)
    ncol=next((c for c in bv.columns if re.search(r'nome.*mun|municipio|mun$',c,re.I)),None)
    ucol="uf" if "uf" in bv.columns else next((c for c in bv.columns if c.lower()=="sigla_uf"),None)
    bridge=bv.assign(chave=bv[ucol].astype(str).str.upper().str.strip()+"|"+bv[ncol].map(norm))[["chave","cod_ibge"]]
elei=elei.merge(bridge,on="chave",how="left")
elei=elei.rename(columns={"NM_URNA_CANDIDATO":"prefeito_2024","SG_PARTIDO":"partido_2024",
                          "DS_SIT_TOT_TURNO":"situacao_2024"})
elei.to_csv(f"{OUT}/eleicao_2024.csv",index=False)
print(f"eleicao_2024.csv: {len(elei)} eleitos | com código IBGE: {elei.cod_ibge.notna().sum()}")
print(elei.partido_2024.value_counts().head(10))

# integra ao wide
base=pd.read_csv(f"{OUT}/base_municipal_v3.csv",dtype={"cod_ibge":str},low_memory=False)
base["cod_ibge"]=base["cod_ibge"].map(c7)
add=elei.dropna(subset=["cod_ibge"])[["cod_ibge","prefeito_2024","partido_2024","situacao_2024"]].drop_duplicates("cod_ibge")
base=base.drop(columns=[c for c in ["prefeito_2024","partido_2024","situacao_2024"] if c in base.columns])
base=base.merge(add,on="cod_ibge",how="left")
base.to_csv(f"{OUT}/base_municipal_v3.csv",index=False)
print("wide atualizado:",base.shape,"| partido_2024 preench.:",base.partido_2024.notna().sum())
