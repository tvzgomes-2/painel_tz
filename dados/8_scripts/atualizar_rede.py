#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
atualizar_rede.py — um comando para incorporar um item novo à rede bibliométrica.

Faz, em sequência, o que antes eram quatro passos manuais:
  1. extrai o texto do PDF para _meta/textos_rsl/<id>.txt (ou aceita um .txt pronto)
  2. atualiza a linha do item em corpus_rsl.csv (estado, gênero, escopo, polo, confiança)
  3. roda extrair_referencias.py sobre TODOS os textos acumulados
  4. roda rede_bibliometrica.py (figuras + relatório)

USO
  python3 atualizar_rede.py --pdf "Cardozo 2025.pdf" --id 40 \
      --genero comunicacao_congresso --escopo "Brasil (44 munic.)" --polo academico
  python3 atualizar_rede.py --txt 40.txt --id 40            # texto já extraído
  python3 atualizar_rede.py --so-regerar                    # só refaz 3 e 4
  python3 atualizar_rede.py --listar-generos                # vocabulário aceito

GÊNEROS aceitos (a taxonomia da RSL — ver LEIA-ME da pasta da rede):
  pesquisa_academica · artigo_academico · comunicacao_congresso · ensaio_teorico
  ensaio_intervencao · entrevista · livro · coletanea · relatorio_patronal
  relatorio_advocacy · analise_conjuntura · a_confirmar

⚠️ O texto extraído fica em _meta/textos_rsl/ (gitignored: é saída derivada do PDF).
   Sem ele, a extração de referências não pode ser refeita — por isso o script o guarda.
⚠️ O parser de referências é heurístico. SEMPRE conferir a contagem que o passo 3 imprime:
   zero entradas pode ser falha do parser OU ausência real de seção de referências.
"""
import argparse, csv, os, shutil, subprocess, sys

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SCR  = os.path.join(RAIZ, "_meta", "scripts")
TXT  = os.path.join(RAIZ, "_meta", "textos_rsl")
REDE = os.path.join(RAIZ, "05 - Referências", "Rede bibliométrica")
CORP = os.path.join(REDE, "corpus_rsl.csv")

GENEROS = ["pesquisa_academica","artigo_academico","comunicacao_congresso","ensaio_teorico",
           "ensaio_intervencao","entrevista","livro","coletanea","relatorio_patronal",
           "relatorio_advocacy","analise_conjuntura","a_confirmar"]

def extrai_pdf(pdf, destino):
    try:
        import pdfplumber
    except ImportError:
        sys.exit("ERRO: pdfplumber não está instalado (pip install pdfplumber).\n"
                 "      Alternativa: extraia o texto por fora e use --txt.")
    partes=[]
    with pdfplumber.open(pdf) as doc:
        for i,pg in enumerate(doc.pages):
            partes.append(f"===PAG {i+1}===")
            partes.append(pg.extract_text() or "")
            for tb in (pg.extract_tables() or []):
                partes.append("[TAB] " + " || ".join(
                    " ; ".join(str(c).replace("\n"," ") for c in linha) for linha in tb))
    open(destino,"w",encoding="utf-8", newline="\n").write("\n".join(partes))
    return len(doc.pages)

def atualiza_corpus(cid, **campos):
    if not os.path.exists(CORP): sys.exit(f"ERRO: não encontrei {CORP}")
    with open(CORP,encoding="utf-8",newline="") as f:
        r=csv.DictReader(f,delimiter=";"); cols=list(r.fieldnames or []); linhas=[dict(x) for x in r]
    achou=False
    for l in linhas:
        if l["id"]!=cid: continue
        achou=True
        antes=dict(l)
        l["estado"]="fichado"; l["confianca_classificacao"]="alta"
        for k,v in campos.items():
            if v: l[k]=v
        mud=[f"{k}: {antes[k]!r} -> {l[k]!r}" for k in cols if antes[k]!=l[k]]
        print(f"  item {cid} ({l['autores'].strip(chr(34))}, {l['ano']})")
        for m in mud: print("    ", m)
        if not mud: print("     (sem mudanças)")
    if not achou:
        sys.exit(f"ERRO: id {cid} não existe em corpus_rsl.csv.\n"
                 "      Se é um item fora dos 42, acrescente a linha à mão antes de rodar.")
    with open(CORP,"w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=cols,delimiter=";"); w.writeheader(); w.writerows(linhas)

def roda(script, *args):
    print(f"\n$ {os.path.basename(script)} {' '.join(args)}")
    p=subprocess.run([sys.executable, os.path.join(SCR,script), *args],
                     capture_output=True, text=True)
    print(p.stdout.rstrip())
    if p.stderr.strip(): print("stderr:", p.stderr.rstrip(), file=sys.stderr)
    if p.returncode: sys.exit(f"ERRO em {script} (rc={p.returncode})")

def main():
    ap=argparse.ArgumentParser(description="Incorpora um item novo à rede bibliométrica da RSL.")
    ap.add_argument("--pdf"); ap.add_argument("--txt")
    ap.add_argument("--id", help="id do item no corpus_rsl.csv")
    ap.add_argument("--genero", choices=GENEROS)
    ap.add_argument("--escopo"); ap.add_argument("--polo"); ap.add_argument("--veiculo")
    ap.add_argument("--so-regerar", action="store_true", dest="so_regerar")
    ap.add_argument("--listar-generos", action="store_true", dest="listar")
    a=ap.parse_args()

    if a.listar:
        print("gêneros aceitos:"); [print("  ",g) for g in GENEROS]; return

    os.makedirs(TXT, exist_ok=True)

    if not a.so_regerar:
        if not a.id: sys.exit("ERRO: --id é obrigatório (ou use --so-regerar).")
        if not (a.pdf or a.txt): sys.exit("ERRO: informe --pdf ou --txt (ou use --so-regerar).")
        destino=os.path.join(TXT, f"{a.id}.txt")
        if a.pdf:
            if not os.path.exists(a.pdf): sys.exit(f"ERRO: não encontrei {a.pdf}")
            print(f"1) extraindo texto de {os.path.basename(a.pdf)}")
            n=extrai_pdf(a.pdf, destino)
            print(f"   {n} páginas -> _meta/textos_rsl/{a.id}.txt")
        else:
            if not os.path.exists(a.txt): sys.exit(f"ERRO: não encontrei {a.txt}")
            if os.path.abspath(a.txt)==os.path.abspath(destino):
                print(f"1) texto já está em _meta/textos_rsl/{a.id}.txt — nada a copiar")
            else:
                shutil.copyfile(a.txt, destino)
                print(f"1) copiado {os.path.basename(a.txt)} -> _meta/textos_rsl/{a.id}.txt")
        print("2) atualizando corpus_rsl.csv")
        atualiza_corpus(a.id, genero=a.genero, escopo=a.escopo, polo=a.polo, veiculo=a.veiculo)

    n=len([x for x in os.listdir(TXT) if x.endswith(".txt")])
    print(f"\n3) extraindo referências de {n} textos acumulados")
    roda("extrair_referencias.py", "--entrada", TXT)
    print("\n4) regerando figuras e relatório")
    roda("rede_bibliometrica.py")
    print("\n✅ pronto. Confira:")
    print("   05 - Referências/Rede bibliométrica/Relatório da rede (gerado).md")
    print("   ⚠️ e as contagens do passo 3 — zero entradas pede conferência manual.")

if __name__=="__main__": main()
