# -*- coding: utf-8 -*-
r"""buscar_abertos_pacote.py — busca por script o que está aberto no Pacote de envio (v1, 17/10/2026).

Autor: Thiago Von Zeidler Gomes · Orientadora: Prof.ª Dra. Silvana Zioni · script escrito com Claude.

Junta numa execução só, na sua máquina (o ambiente do Claude não alcança o PNCP):
  1. Arquivos: baixa os documentos da fila de 17/10 (11 compras/contratos do PNCP + a Portaria 98/2021 de Cianorte)
     com o baixar_documentos_busca.py, para "_a triar/download-AAAA-MM-DD/".
  2. Contratadas: roda o buscar_operadores_pncp.py só para os 21 municípios abertos, desde 2024
     (as janelas de 2024 em diante batem com as do cache; para os 15 que já estavam na rodada v2, só a janela atual vai à rede).
  3. Novidades: compara o CSV novo com todos os "Operadoras — resultados do PNCP (*).csv" anteriores e grava só as linhas novas.

Uso (Anaconda Prompt):
  conda activate tz-download
  cd /d "%USERPROFILE%\OneDrive\doutorado"
  python _meta\scripts\buscar_abertos_pacote.py              # tudo (arquivos, contratadas, novidades)
  python _meta\scripts\buscar_abertos_pacote.py --simular    # só mostra o plano dos arquivos, sem rede
  opções: --so-arquivos · --so-pncp · --so-novidades · --paralelo 2 (rede fraca) · --desde 2021

Regras: só leitura; os dois scripts respeitam robots.txt, esperam entre pedidos e em HTTP 429; nada é contornado.
O resultado é pista até conferência; nada entra na base sem o Registro de alterações pós-congelamento.
"""
import argparse, csv, datetime, glob, os, re, subprocess, sys, time, unicodedata
RAIZ = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
SC = os.path.join(RAIZ, "_meta", "scripts")
PL = os.path.join(RAIZ, "04 - Análises", "Pesquisa legal")
FILA = os.path.join(PL, "Busca — abertos do Pacote, fila de script (17-10-2026).csv")
LISTA = os.path.join(SC, "_scratch", "operadores-1014", "lista_pncp_abertos_1017.csv")
HOJE = datetime.date.today()

def rodar(args):
    print("\n>>> " + " ".join(os.path.basename(a) if a.endswith(".py") else a for a in args), flush=True)
    t = time.time(); r = subprocess.call([sys.executable] + args, cwd=RAIZ)
    print(f"<<< {time.time() - t:.0f} s, código {r}", flush=True); return r

NUC = re.compile(r"transporte (publico )?coletivo|coletivo (urbano|municipal|rural)|transporte (publico )?((urbano|rural|municipal) )?de passageiros|(onibus|linha) circular|circular (gratuit|urbano|municipal)|linhas? (urbanas?|municipa(l|is)|regular(es)?)|tarifa zero|passe livre|onibus urbano|onibus com motorista|(locacao|fretamento) de onibus.*(motorista|km|quilometr)")
FORA = re.compile(r"escolar|aluno|estudant|universitar|saude|paciente|hemodial|tfd|ambulanc|evento|festa|turism|esport|atleta|carnaval|manutenc|pecas|pneu|combustivel|diesel|aquisicao de (onibus|micro|veiculo)|vistoria|seguro|imovel|lixo|residuos|carga|funerar|guincho|remocao|vale.?transporte|uniforme|motocicleta")
def sa(x): return unicodedata.normalize("NFKD", str(x or "")).encode("ascii", "ignore").decode().lower()
def nucleo(l):
    o = sa(l.get("objeto")) + " " + sa(l.get("tipo"))
    return bool(NUC.search(o)) and not FORA.search(o)

def chave(l): return (l.get("url", ""), l.get("cnpj_fornecedor", ""), l.get("tipo", ""), l.get("fonte", ""))

def novidades(novo, rotulo="abertos do Pacote"):
    hoje = f"{HOJE:%d-%m-%Y}"
    antigos = [p for p in glob.glob(os.path.join(PL, "Operadoras — resultados do PNCP (*).csv")) if os.path.abspath(p) != os.path.abspath(novo)
               and hoje not in os.path.basename(p) and "só cache" not in p]   # base de comparação: só rodadas de dias anteriores
    vistos = set()
    for p in antigos:
        with open(p, encoding="utf-8-sig") as f: vistos |= {chave(l) for l in csv.DictReader(f, delimiter=";")}
    with open(novo, encoding="utf-8-sig") as f: rd = csv.DictReader(f, delimiter=";"); campos = rd.fieldnames; linhas = list(rd)
    nov = [l for l in linhas if chave(l) not in vistos]
    for l in nov: l["nucleo_transporte_coletivo"] = "sim" if nucleo(l) else ""
    campos = list(campos) + ["nucleo_transporte_coletivo"]
    nov.sort(key=lambda l: (l["nucleo_transporte_coletivo"] != "sim", l["municipio"], l.get("ano", ""), l.get("sequencial", "")))
    saida = os.path.join(PL, f"Operadoras — novidades do PNCP, {rotulo} ({HOJE:%d-%m-%Y}).csv")
    with open(saida, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=campos, delimiter=";"); w.writeheader(); w.writerows(nov)
    nuc = [l for l in nov if l["nucleo_transporte_coletivo"]]
    print(f"\nNovidades: {len(nov)} de {len(linhas)} linhas (comparado com {len(antigos)} CSV anteriores); "
          f"{len(nuc)} com cara de transporte coletivo (primeiro no CSV) → {os.path.basename(saida)}")
    vistos2, por = set(), {}
    for l in nuc:
        k = (l["url"], l.get("cnpj_fornecedor", ""))
        if k in vistos2: continue
        vistos2.add(k); por.setdefault(f"{l['municipio']}/{l['uf']}", []).append(l)
    for m, ls in sorted(por.items()):
        print(f"  {m}: {len(ls)}")
        for l in ls[:6]:
            quem = (l.get("fornecedor") or "(sem vencedor)")[:34]; obj = " ".join((l.get("objeto") or "").split())[:70]
            print(f"     {l['ano']}/{l['sequencial']:<5} {l['fonte'][:22]:22} {quem:34} {l.get('cnpj_fornecedor',''):>14}  {obj}")

def main():
    ap = argparse.ArgumentParser(description="Busca por script o que está aberto no Pacote de envio.")
    ap.add_argument("--so-arquivos", action="store_true"); ap.add_argument("--so-pncp", action="store_true")
    ap.add_argument("--so-novidades", action="store_true", help="refaz só a comparação, com o último CSV dos abertos")
    ap.add_argument("--simular", action="store_true"); ap.add_argument("--paralelo", default="4"); ap.add_argument("--desde", default="2024")
    a = ap.parse_args()
    for p in (FILA, LISTA): assert os.path.isfile(p), f"não achei {p}"
    print(f"Cofre: {RAIZ}\nPython: {sys.executable}")
    if a.simular:
        return rodar([os.path.join(SC, "baixar_documentos_busca.py"), "--fila", FILA, "--simular"])
    if not (a.so_pncp or a.so_novidades):
        rodar([os.path.join(SC, "baixar_documentos_busca.py"), "--fila", FILA])
    if a.so_arquivos: return
    alvo = os.path.join(PL, f"Operadoras — resultados do PNCP, abertos do Pacote ({HOJE:%d-%m-%Y}).csv")
    if not a.so_novidades:
        padrao = os.path.join(PL, f"Operadoras — resultados do PNCP ({HOJE:%d-%m-%Y}).csv")
        if os.path.exists(padrao):   # um CSV de rodada completa do mesmo dia não pode ser sobrescrito
            os.replace(padrao, padrao.replace(").csv", f", guardado {time.strftime('%H%M%S')}).csv"))
        r = rodar([os.path.join(SC, "buscar_operadores_pncp.py"), "--lista", LISTA, "--desde", a.desde, "--validade", "0", "--paralelo", a.paralelo])
        if os.path.exists(padrao): os.replace(padrao, alvo)
        if r not in (0, None) and not os.path.exists(alvo): sys.exit("A busca no PNCP parou antes de gravar; rode de novo com --so-pncp (o cache guarda o que veio).")
    else:
        cands = sorted(glob.glob(os.path.join(PL, "Operadoras — resultados do PNCP, abertos do Pacote (*).csv")), key=os.path.getmtime)
        if not cands: sys.exit("Nenhum CSV dos abertos ainda.")
        alvo = cands[-1]
    novidades(alvo)
    print("\nPronto. Avise no chat: eu leio as novidades e a pasta _a triar, confiro na fonte e registro.")

if __name__ == "__main__":
    main()
