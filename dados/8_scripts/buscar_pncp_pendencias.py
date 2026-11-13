# -*- coding: utf-8 -*-
r"""buscar_pncp_pendencias.py — busca no PNCP os contratos dos municípios com pendência de contrato ou legislação.

Autor: Thiago Von Zeidler Gomes · Orientadora: Prof.ª Dra. Silvana Zioni · script escrito com Claude (05/11/2026; revisão no mesmo dia: saída própria e retomada).

Para quê: rodada reprodutível da busca do PNCP para a nota "Pendências de contratos e legislação (05-11-2026)".
  1. Remonta a lista a partir da base viva (montar_lista_pncp_pendencias.py), salvo --sem-remontar.
  2. Roda buscar_operadores_pncp.py (API pública de consulta do PNCP, só leitura; cache, retomada, espera em 429)
     com essa lista. Todas as opções extras passam direto para ele (--de N, --so MUN UF, --paralelo, --offline…).
Saída: "04 - Análises/Pesquisa legal/PNCP — pendências de contratos e legislação (DD-MM-AAAA[, grupo N]).csv" e o log no cache.
Retomar depois de parar: use --sem-remontar (a ordem da lista não muda) e --de N, com o mesmo --grupo:
  python _meta/scripts/buscar_pncp_pendencias.py --sem-remontar --grupo 2 --de 15
Limite conhecido: a etapa 1 busca pelo código IBGE do município; compras feitas por consórcio (ex.: ICISMEP em Mário Campos)
não aparecem. Nesses casos, ponha o CNPJ do consórcio em "orgaos_conhecidos" na lista (etapa 2 busca os contratos do órgão).
O resultado é pista até conferência; nada entra na base sem o Registro de alterações pós-congelamento.

Precisa de rede até pncp.gov.br (roda na máquina do autor, ambiente conda "tz-download"):
  conda activate tz-download
  python _meta/scripts/buscar_pncp_pendencias.py                 # remonta a lista e busca os 125 (05/11/2026)
  python _meta/scripts/buscar_pncp_pendencias.py --grupo 2       # só um grupo (1 a 4)
  python _meta/scripts/buscar_pncp_pendencias.py --de 40         # retoma do 40º município
"""
import argparse, csv, os, subprocess, sys
AQUI = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, AQUI)
RAIZ = os.path.abspath(os.path.join(AQUI, ".."))
RAIZ = os.path.dirname(RAIZ) if os.path.basename(RAIZ) == "_meta" else RAIZ
SAIDA_LISTA = os.path.join(RAIZ, "_meta", "scripts", "_scratch", "releitura-1030", "lista_pncp_pendencias_1105.csv")

def remontar(lista):
    try:
        import montar_lista_pncp_pendencias as M  # precisa de openpyxl (lê a base-mestre .xlsx)
    except ModuleNotFoundError as e:
        sys.exit(f"Falta o pacote {e.name} neste ambiente. Instale com:  pip install {e.name}\n"
                 f"ou rode sem remontar a lista (usa a lista já gravada):  python _meta\\scripts\\buscar_pncp_pendencias.py --sem-remontar ...")
    out = M.montar(); M.gravar(out, lista); print(f"lista remontada: {len(out)} municípios → {lista}")

def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0], add_help=True)
    ap.add_argument("--sem-remontar", action="store_true", help="usa a lista já gravada, sem reler a base")
    ap.add_argument("--grupo", type=int, choices=[1, 2, 3, 4], help="só os municípios de um grupo")
    a, resto = ap.parse_known_args()
    lista = SAIDA_LISTA
    if not a.sem_remontar or not os.path.exists(lista):
        remontar(lista)
    if a.grupo:
        rows = list(csv.DictReader(open(lista, encoding="utf-8-sig"), delimiter=";"))
        sel = [r for r in rows if r["grupo"].startswith(f"{a.grupo}.")]
        lista = lista.replace(".csv", f"_grupo{a.grupo}.csv")
        with open(lista, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter=";"); w.writeheader(); w.writerows(sel)
        print(f"grupo {a.grupo}: {len(sel)} municípios → {lista}")
    if "--saida" not in resto:
        import datetime
        rot = datetime.date.today().strftime("%d-%m-%Y") + (f", grupo {a.grupo}" if a.grupo else "")
        resto += ["--saida", os.path.join(RAIZ, "04 - Análises", "Pesquisa legal", f"PNCP — pendências de contratos e legislação ({rot}).csv")]
    cmd = [sys.executable, os.path.join(AQUI, "buscar_operadores_pncp.py"), "--lista", lista] + resto
    print("rodando:", " ".join(f'"{c}"' if " " in c else c for c in cmd), flush=True)
    sys.exit(subprocess.call(cmd, cwd=RAIZ))

if __name__ == "__main__":
    main()
