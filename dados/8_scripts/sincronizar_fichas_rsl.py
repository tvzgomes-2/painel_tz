#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sincronizar_fichas_rsl.py — grava no frontmatter de cada ficha o vínculo com o item
do corpus da RSL, e confere a consistência nos dois sentidos.

PROBLEMA QUE RESOLVE (medido em 07/09/2026). O vínculo item↔ficha era inferido do
NOME DO ARQUIVO, por ano + sobrenome + título: acertava 81 de 107 e deixava 26 sem
casamento — e os 26 não eram itens sem ficha, eram falhas do casador (ano ausente do
nome, autoria como "et al.", acento divergente). Um vínculo com 24% de incerteza
silenciosa é pior que nenhum. Aqui o vínculo passa a ser DECLARADO no frontmatter.

CAMPOS GRAVADOS (todos com prefixo rsl_, para não colidir com o frontmatter do autor)
  rsl_id            🔒 CANÔNICO. Inteiro do corpus_rsl.csv. NUNCA muda: é a chave que
                    junta corpus_rsl.csv, arestas_manuais.csv, citacoes_completas.csv
                    e _meta/textos_rsl/<id>.txt. Renumerar quebra a rede inteira.
  rsl_ref           legível, DERIVADO: <estrato|NE>-r<rodada>-i<id>, ex. RSL2-r06-i073.
                    Serve para conversar e citar; é regenerado a cada execução e
                    NUNCA vira nome de arquivo (link do Obsidian resolve por nome).
  rsl_estrato · rsl_rodada · rsl_procedimento · rsl_estado
  rsl_motivo_exclusao · rsl_posicionalidade   (vazios quando não se aplicam)

DIREÇÃO DA AUTORIDADE — regra, não convenção
  ➡️ O `corpus_rsl.csv` MANDA nos campos rsl_*. A ficha é ESPELHO.
  ⬅️ A ficha manda no CAPÍTULO DE DESTINO, que fica nas TAGS (`cap3`, `cap5`, …) e é
     decisão de leitura, não de catalogação. Este script LÊ as tags e nunca as escreve.
  🔒 Um fato, um lugar. Não criar campo `cap_destino` no frontmatter: as tags já são
     a autoridade, e duplicar cria duas verdades no mesmo arquivo.

USO
  python3 sincronizar_fichas_rsl.py --conferir            # relatório, não escreve nada
  python3 sincronizar_fichas_rsl.py --aplicar             # grava nas fichas já vinculadas
  python3 sincronizar_fichas_rsl.py --aplicar --mapa mapa_item_ficha.csv --confianca alta
                                                          # primeira vinculação, pelo mapa

⚠️ Escreve SOMENTE dentro do bloco de frontmatter, e somente linhas rsl_*. Nenhuma
   linha de prosa é tocada. Escrita atômica: arquivo temporário, releitura, substituição.
"""
import argparse, csv, io, os, re, shutil, sys, collections

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CORP = os.path.join(RAIZ, "05 - Referências", "Rede bibliométrica", "corpus_rsl.csv")
FICH = os.path.join(RAIZ, "05 - Referências", "Notas de leitura")

CAMPOS = ["rsl_id", "rsl_ref", "rsl_estrato", "rsl_rodada", "rsl_procedimento",
          "rsl_estado", "rsl_motivo_exclusao", "rsl_posicionalidade"]
TAG_CAP = re.compile(r'\bcap-?(\d)\b')


def corpus():
    with open(CORP, encoding="utf-8-sig") as f:
        return {r["id"].strip(): r for r in csv.DictReader(f, delimiter=";")}


def ref(r):
    est = (r.get("estrato") or "").strip() or "NE"          # NE = não estratificado
    rod = (r.get("rodada") or "").strip() or "0"
    return f"{est}-r{int(float(rod)):02d}-i{int(r['id']):03d}"


def parte_frontmatter(txt):
    """Devolve (antes, corpo_do_frontmatter, depois) ou None se não houver."""
    if not txt.startswith("---"):
        return None
    fim = txt.find("\n---", 3)
    if fim == -1:
        return None
    return txt[:4], txt[4:fim + 1], txt[fim + 1:]


def le_id(txt):
    p = parte_frontmatter(txt)
    if not p:
        return None
    m = re.search(r'^rsl_id:[ \t]*(\d+)[ \t]*$', p[1], re.M)
    return m.group(1) if m else None


def caps(txt):
    p = parte_frontmatter(txt)
    fm = p[1] if p else ""
    return sorted({int(x) for x in TAG_CAP.findall(fm) if 1 <= int(x) <= 7})


def grava(caminho, r):
    txt = open(caminho, encoding="utf-8").read()
    p = parte_frontmatter(txt)
    if not p:
        return "SEM FRONTMATTER"
    ini, fm, resto = p
    novo = {"rsl_id": r["id"].strip(), "rsl_ref": ref(r),
            "rsl_estrato": (r.get("estrato") or "").strip(),
            "rsl_rodada": (r.get("rodada") or "").strip(),
            "rsl_procedimento": (r.get("procedimento") or "").strip(),
            "rsl_estado": (r.get("estado") or "").strip(),
            "rsl_motivo_exclusao": (r.get("motivo_exclusao") or "").strip(),
            "rsl_posicionalidade": (r.get("posicionalidade") or "").strip()}
    linhas = [l for l in fm.split("\n") if not re.match(r'^rsl_[a-z_]+:', l)]
    while linhas and not linhas[-1].strip():
        linhas.pop()
    bloco = [f"{k}: {novo[k]}" for k in CAMPOS]
    fm2 = "\n".join(linhas + bloco) + "\n"
    if fm2 == fm:
        return "sem mudanca"
    tmp = caminho + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(ini + fm2 + resto)
    conf = open(tmp, encoding="utf-8").read()
    if le_id(conf) != novo["rsl_id"] or len(conf) < len(txt) - 5:
        os.remove(tmp)
        return "VALIDACAO FALHOU"
    shutil.move(tmp, caminho)
    return "gravado"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--aplicar", action="store_true")
    ap.add_argument("--conferir", action="store_true")
    ap.add_argument("--mapa", help="CSV com colunas id e nota_fichamento (primeira vinculação)")
    ap.add_argument("--confianca", default="alta", help="filtro da coluna confianca do mapa")
    a = ap.parse_args()
    if not (a.aplicar or a.conferir):
        sys.exit("informe --conferir ou --aplicar")

    C = corpus()
    fichas = [f for f in os.listdir(FICH) if f.endswith(".md")]
    vinc = {}                                    # id -> arquivo, já declarado no frontmatter
    dup = collections.defaultdict(list)
    for f in fichas:
        i = le_id(open(os.path.join(FICH, f), encoding="utf-8", errors="replace").read())
        if i:
            dup[i].append(f)
            vinc[i] = f

    if a.mapa:
        with open(a.mapa, encoding="utf-8-sig") as fh:
            for r in csv.DictReader(fh, delimiter=";"):
                i = (r.get("id") or "").strip()
                nome = (r.get("nota_fichamento") or "").strip()
                if not i or not nome or nome.startswith("FICHA SEM ITEM"):
                    continue
                if a.confianca and (r.get("confianca") or "").strip() != a.confianca:
                    continue
                if i in vinc or not os.path.exists(os.path.join(FICH, nome)):
                    continue
                vinc[i] = nome

    print(f"corpus: {len(C)} itens · fichas: {len(fichas)} · vinculadas: {len(vinc)}")
    for i, L in dup.items():
        if len(L) > 1:
            print(f"  🔴 id {i} declarado em {len(L)} fichas: {L}")
    orfaos = [i for i in vinc if i not in C]
    if orfaos:
        print(f"  🔴 fichas com rsl_id inexistente no corpus: {sorted(orfaos, key=int)}")

    lidos = [i for i, r in C.items() if r["estado"] in ("fichado", "excluido_apos_leitura")]
    sem = sorted((i for i in lidos if i not in vinc), key=int)
    print(f"  ⚠️ itens lidos SEM ficha vinculada: {len(sem)} de {len(lidos)} -> {sem}")

    cc = collections.Counter()
    for i, f in sorted(vinc.items(), key=lambda x: int(x[0])):
        if i not in C:
            continue
        p = os.path.join(FICH, f)
        if a.aplicar:
            cc[grava(p, C[i])] += 1
        else:
            txt = open(p, encoding="utf-8", errors="replace").read()
            pm = parte_frontmatter(txt)
            # ⚠️ [ \t]* e nao \s*: \s inclui \n, e num campo vazio ("rsl_estrato: ")
            # o \s* engolia a quebra e capturava a LINHA SEGUINTE como valor — o que
            # fazia 21 fichas aparecerem divergentes sem nenhuma divergencia real.
            atual = dict(re.findall(r'^(rsl_[a-z_]+):[ \t]*(.*)$', pm[1], re.M)) if pm else {}
            esp = {"rsl_estado": (C[i].get("estado") or "").strip(),
                   "rsl_estrato": (C[i].get("estrato") or "").strip(),
                   "rsl_ref": ref(C[i])}
            div = [k for k, v in esp.items() if atual.get(k, "").strip() != v]
            cc["divergente: " + ",".join(div) if div else "ok"] += 1
    print("  resultado:", dict(cc))

    semcap = [i for i, f in vinc.items() if not caps(open(os.path.join(FICH, f), encoding="utf-8", errors="replace").read())]
    print(f"  ⚠️ fichas vinculadas SEM tag de capítulo (capN): {len(semcap)} de {len(vinc)}")


if __name__ == "__main__":
    main()
