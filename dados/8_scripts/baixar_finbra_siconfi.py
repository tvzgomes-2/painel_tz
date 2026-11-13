#!/usr/bin/env python3
"""
baixar_finbra_siconfi.py — coleta o FINBRA nacional (todos os municípios) via API
pública do Siconfi/STN, gravando CSV por tipo/ano. Só depende da biblioteca padrão.

CONTEXTO: o dump da POLO só tinha FINBRA de SP e PA (e SP truncado). Este script
rebaixa o dado NACIONAL da fonte oficial. Rode na SUA máquina — a API do Siconfi
é bloqueada no sandbox do Cowork (proxy 403), mas funciona normalmente localmente.

Fonte/API: https://apidatalake.tesouro.gov.br/ords/siconfi/tt/  (docs: /docs/siconfi/)
Demonstrativo DCA (Declaração de Contas Anuais):
  - Anexo I-C = Balanço Orçamentário — Receitas Orçamentárias
  - Anexo I-D = Balanço Orçamentário — Despesas por categoria econômica (natureza)
  - Anexo I-E = Despesas por Função  ← p/ Urbanismo (f.15: infra urbana/serviços
                urbanos/zeladoria) e Transporte (f.26). CONFIRMAR o rótulo exato
                do anexo na 1ª chamada (imprime o 'anexo' retornado).
Parâmetros obrigatórios: an_exercicio (ano) + id_ente (código IBGE do município).

USO:
  python3 baixar_finbra_siconfi.py --anos 2019 2020 2021 2022 2023 \
      --tipos receitas despesas --saida ./finbra_nacional
  # despesa por FUNÇÃO (Urbanismo/zeladoria + Transporte):
  python3 baixar_finbra_siconfi.py --anos 2019 2020 2021 2022 2023 \
      --tipos funcao --saida ./finbra_nacional
  # retomável: rode de novo se cair; pula o que já baixou (pasta .done/).

Saída: finbra_<tipo>_<ano>.csv (uma linha por conta × município), colunas:
  exercicio, cod_ibge, uf, instituicao, populacao, anexo, rotulo, coluna,
  cod_conta, conta, valor
"""
import urllib.request, urllib.parse, json, csv, os, sys, time, argparse

BASE = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt"
ANEXOS = {"receitas": "DCA-Anexo I-C", "despesas": "DCA-Anexo I-D",
          "funcao": "DCA-Anexo I-E"}  # I-E = Despesas por Função (confirmar rótulo)
CAMPOS = ["exercicio", "cod_ibge", "uf", "instituicao", "populacao",
          "anexo", "rotulo", "coluna", "cod_conta", "conta", "valor"]
UA = {"User-Agent": "pesquisa-doutorado-PGT-UFABC (uso academico)"}


def get(path, **params):
    url = f"{BASE}/{path}?" + urllib.parse.urlencode(params)
    last = None
    for tent in range(6):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=90) as r:
                return json.load(r)
        except Exception as e:
            last = e
            time.sleep(3 * (tent + 1))
    raise last


def lista_municipios():
    """Todos os entes municipais (esfera 'M') do Siconfi."""
    out, offset = [], 0
    while True:
        d = get("entes", offset=offset)
        for i in d.get("items", []):
            if i.get("esfera") == "M":
                out.append(str(i["cod_ibge"]))
        if not d.get("hasMore"):
            break
        offset += d.get("limit", 500)
    return sorted(set(out))


def baixa_ente(ano, anexo, ente):
    """Todas as linhas de um município/ano/anexo (com paginação)."""
    linhas, offset = [], 0
    while True:
        d = get("dca", an_exercicio=ano, no_anexo=anexo, id_ente=ente, offset=offset)
        linhas += d.get("items", [])
        if not d.get("hasMore"):
            break
        offset += d.get("limit", 5000)
    return linhas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--anos", nargs="+", type=int, required=True)
    ap.add_argument("--tipos", nargs="+", default=["receitas", "despesas"],
                    choices=list(ANEXOS))
    ap.add_argument("--saida", default="./finbra_nacional")
    ap.add_argument("--pausa", type=float, default=0.15, help="segundos entre chamadas")
    args = ap.parse_args()

    os.makedirs(args.saida, exist_ok=True)
    done_dir = os.path.join(args.saida, ".done")
    os.makedirs(done_dir, exist_ok=True)

    print("Buscando lista de municípios no Siconfi...", flush=True)
    entes = lista_municipios()
    print(f"  {len(entes)} municípios.", flush=True)

    for ano in args.anos:
        for tipo in args.tipos:
            anexo = ANEXOS[tipo]
            out_csv = os.path.join(args.saida, f"finbra_{tipo}_{ano}.csv")
            novo = not os.path.exists(out_csv)
            fh = open(out_csv, "a", newline="", encoding="utf-8")
            w = csv.DictWriter(fh, fieldnames=CAMPOS, extrasaction="ignore")
            if novo:
                w.writeheader()
            feitos = 0
            for k, ente in enumerate(entes, 1):
                mk = os.path.join(done_dir, f"{ano}_{tipo}_{ente}")
                if os.path.exists(mk):
                    continue
                try:
                    for row in baixa_ente(ano, anexo, ente):
                        w.writerow(row)
                    fh.flush()
                    open(mk, "w").close()
                    feitos += 1
                except Exception as e:
                    print(f"  ! {ano}/{tipo}/{ente}: {e} (será retomado)", flush=True)
                if k % 200 == 0:
                    print(f"  {ano}/{tipo}: {k}/{len(entes)}", flush=True)
                time.sleep(args.pausa)
            fh.close()
            print(f"OK {tipo} {ano}: +{feitos} municípios -> {out_csv}", flush=True)
    print("CONCLUÍDO.", flush=True)


if __name__ == "__main__":
    main()
