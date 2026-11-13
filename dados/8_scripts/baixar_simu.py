#!/usr/bin/env python3
"""baixar_simu.py — SIMU / Sistema Nacional de Informações em Mobilidade Urbana
(Ministério das Cidades). Baixa os pacotes municipais (CSV zipados, hospedados na
Fiocruz/PCDaS), extrai e imprime o esquema de cada base. Só pandas — sem pysus.
Rode na SUA máquina (a Fiocruz é bloqueada no sandbox do Cowork).

URLs capturadas do painel de Downloads do SIMU (jul/2026):
  https://simu.cidades.gov.br/downloads/

USO:
  python3 baixar_simu.py                # baixa o conjunto relevante (padrão)
  python3 baixar_simu.py --todos        # baixa tudo (15 bases)
  python3 baixar_simu.py --so mortes tarifas frota   # apenas essas
Saída: _data/SIMU/<chave>/*.csv  + impressão de colunas/linhas de cada CSV
       (a INTEGRAÇÃO ao banco v3 é feita depois, com o esquema em mãos)."""
import argparse, os, io, zipfile, urllib.request, glob, pandas as pd
HERE=os.path.dirname(os.path.abspath(__file__))
V=os.path.join(os.path.abspath(os.path.join(HERE,"..","..")),"03 - Dados","_data")
OUT=os.path.join(V,"SIMU")
B="https://bigdata-arquivos.icict.fiocruz.br/PUBLICO/SIMU"
FONTES={
 # base de dados (séries municipais) — mais úteis para a tese
 "mortes":            f"{B}/bases_dados/MORTES/simu-mortes-mun-T.zip",
 "feridos":           f"{B}/bases_dados/FERIDOS/simu-feridos-mun-T.zip",
 "tarifas":           f"{B}/bases_dados/TARIFAS/simu-tarifas-mun_T.zip",
 "frota":             f"{B}/bases_dados/FROTA/simu-frota-mun_T.zip",
 "tempo_deslocamento":f"{B}/bases_dados/TEMPO_DESLOCAMENTO/simu-tempo-deslocamento_mun_T.zip",
 "pemob":             f"{B}/bases_dados/PEMOB/simu-pemob-mun_T.zip",
 "poluentes":         f"{B}/bases_dados/POLUENTES/simu-emissao-poluentes-mun-T.zip",
 "carteira":          f"{B}/bases_dados/CARTEIRA/simu-carteira-mun-T.zip",
 # temas (indicadores consolidados)
 "acidentes":         f"{B}/temas/simu-acidentes-transportes-mun-T.zip",
 "acesso_sistema":    f"{B}/temas/simu-acesso-sistema-mobilidade-urbana-mun-T.zip",
 "infraestrutura":    f"{B}/temas/simu-infraestrutura-mobilidade-urbana-mun-T.zip",
 "politica_tarifaria":f"{B}/temas/simu-politica-tarifaria-mun-T.zip",
 "servicos":          f"{B}/temas/simu-servicos-mobilidade-urbana-mun-T.zip",
 "sustentabilidade":  f"{B}/temas/simu-sustentabilidade-ambiental-mun-T.zip",
}
PADRAO=["mortes","feridos","tarifas","frota","tempo_deslocamento","pemob",
        "acidentes","politica_tarifaria","servicos","carteira","infraestrutura"]
# 'carteira' = Carteira de Empreendimentos (INVESTIMENTOS em obras de mobilidade,
#              ex.: PAC/OGU) por município — complementa os investimentos do FINBRA.
# 'infraestrutura' = indicador consolidado de infraestrutura de mobilidade.

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--todos",action="store_true")
    ap.add_argument("--so",nargs="+",choices=list(FONTES))
    a=ap.parse_args()
    chaves=list(FONTES) if a.todos else (a.so or PADRAO)
    os.makedirs(OUT,exist_ok=True)
    for k in chaves:
        dst=os.path.join(OUT,k); os.makedirs(dst,exist_ok=True)
        if not glob.glob(f"{dst}/*.csv"):
            print(f"\n== baixando {k} ==",FONTES[k])
            try:
                data=urllib.request.urlopen(FONTES[k],timeout=180).read()
                zipfile.ZipFile(io.BytesIO(data)).extractall(dst)
            except Exception as e:
                print("  ! falhou:",e); continue
        for csv in glob.glob(f"{dst}/*.csv"):
            try:
                d=pd.read_csv(csv,sep=None,engine="python",nrows=200,dtype=str)
                print(f"\n[{k}] {os.path.basename(csv)}  cols={len(d.columns)}")
                print("  colunas:",list(d.columns))
                print(d.head(2).to_string()[:800])
            except Exception as e:
                print("  ! leitura:",csv,e)
    print("\nOK. Me diga (ou eu leio do disco) as colunas de 'mortes'/'tarifas'/'frota' "
          "para eu escrever a integração ao banco v3.")

if __name__=="__main__": main()
