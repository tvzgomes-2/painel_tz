#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""corrigir_ano_citekey.py — corrige o ano herdado errado nas citekeys da rede.

Contexto: "05 - Referências/Rede bibliométrica/LEIA-ME — Rede bibliométrica.md" e a
pendência aberta no fichamento de Pereira, Carvalho, Souza e Camarano (2014), que
registrava o caso `camarano1966` (o número de série do TD do Ipea lido como ano).

A varredura de 04/09/2026 mostrou que o caso do TD era um de DOIS defeitos:
  (a) SÉRIE LIDA COMO ANO  — "TD n. 1966 ... 2014"  -> camarano1966
  (b) INTERVALO DO TÍTULO  — "(1992-2009) ... 2013" -> pereira1992
O segundo é o mais frequente (9 de 10 casos) e não estava registrado.

Regra adotada (compatível com ABNT, onde o ano de publicação fecha a entrada):
percorrer os anos candidatos na ordem em que aparecem e devolver o PRIMEIRO que
  * não esteja dentro de um intervalo AAAA-AAAA ou AAAA-AA, e
  * não venha logo depois de um marcador de série (n., nº, no., v., vol., p., TD).
Mantém-se "o primeiro" e não "o último" de propósito: parte das entradas do
corpus vem com duas referências coladas pela extração, e o último ano seria o da
referência seguinte.

Colisão: se a chave corrigida já existir apontando para OUTRA referência, a nova
recebe sufixo (b, c, ...). É o caso de Márcia Sandoval Gregori (tese, 2018) e
Lúcio Gregori (TarifaZero.org, 2018) — homônimos que NÃO podem ser fundidos, pelo
mesmo motivo do caso Calejon/Santos.

USO   python3 corrigir_ano_citekey.py [--aplicar]
      Sem --aplicar apenas relata (padrão).
"""
import argparse, csv, os, re

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REDE = os.path.join(RAIZ, "05 - Referências", "Rede bibliométrica")
ARQS = {
    "referencias_brutas.csv":    "chave",
    "citacoes_completas.csv":    "chave_citada",
    "referencias_distintas.csv": "chave",
}

Y     = re.compile(r'\b(19[0-9]{2}|20[0-2][0-9])\b')
SER   = re.compile(r'(?:\bn\.|\bnº|\bno\.|\bnum\.|\bTD|\bv\.|\bvol\.|\bp\.)\s*°?\s*$', re.I)
RANGE = re.compile(r'\b(19[0-9]{2}|20[0-2][0-9])\s*[-–—/]\s*(?:19[0-9]{2}|20[0-2][0-9]|[0-9]{2})\b')


def ano_de(e):
    """Ano de publicação de uma entrada de referência. Ver a regra no cabeçalho."""
    faixas = [(m.start(), m.end()) for m in RANGE.finditer(e)]
    for m in Y.finditer(e):
        s = m.start()
        if any(a <= s < b for a, b in faixas):
            continue
        if SER.search(e[max(0, s - 12):s].rstrip()):
            continue
        return m.group(1)
    achados = Y.findall(e)
    return achados[0] if achados else "sd"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--aplicar", action="store_true", help="grava; sem isto so relata")
    a = p.parse_args()

    dist = os.path.join(REDE, "referencias_distintas.csv")
    with open(dist, encoding="utf-8") as f:
        linhas = list(csv.DictReader(f, delimiter=";"))
    ocupadas = {r["chave"]: r["referencia"] for r in linhas}

    corr = {}
    for r in linhas:
        ch, ref = r["chave"], r["referencia"]
        anos = Y.findall(ref)
        if not anos or not ch.endswith(anos[0]):
            continue
        novo_ano = ano_de(ref)
        if novo_ano == anos[0]:
            continue
        base = ch[:-4] + novo_ano
        cand = base
        suf = ord("b")
        while cand in ocupadas and ocupadas[cand] != ref:
            cand = base + chr(suf)
            suf += 1
        corr[ch] = cand
        ocupadas[cand] = ref

    if not corr:
        print("nada a corrigir.")
        return
    print(f"{len(corr)} chaves a corrigir:")
    for k, v in sorted(corr.items()):
        print(f"  {k:22} -> {v}")
    if not a.aplicar:
        print("\n(dry-run; use --aplicar para gravar)")
        return

    for nome, col in ARQS.items():
        caminho = os.path.join(REDE, nome)
        with open(caminho, encoding="utf-8") as f:
            rd = csv.DictReader(f, delimiter=";")
            campos = rd.fieldnames
            rows = list(rd)
        n = 0
        for r in rows:
            if r[col] in corr:
                r[col] = corr[r[col]]
                n += 1
        with open(caminho, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=campos, delimiter=";")
            w.writeheader()
            w.writerows(rows)
        print(f"  {nome}: {n} linhas alteradas")


if __name__ == "__main__":
    main()
