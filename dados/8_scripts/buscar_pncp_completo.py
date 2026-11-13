#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
buscar_pncp_completo.py

Runner de "rodada completa" para buscar_pncp.py: varre TODOS os 175
municípios da base-mestre (145... na verdade 165 ativas + 10 encerradas —
número reconciliado em 16-17/09/2026, ver Pendências.md) contra TODOS os
anos em que o PNCP existe (abril/2021 até hoje — o portal nasceu da Lei
14.133/2021, não faz sentido buscar antes disso), por padrão nas 8
modalidades de MODALIDADES_RODADA_COMPLETA (ajuste de 18/09/2026 — ver item
2 abaixo), não só as 6 da triagem rápida; os 13 completos continuam
disponíveis via --modalidades-todas-13.

Por que um script separado, e não só um comando do buscar_pncp.py: essa é
a rodada grande, de horas, que ninguém quer perder por causa de uma queda
de rede ou o notebook dormir no meio. Este runner:

  1. Usa por padrão `municipios_completo_175.csv` (nesta mesma pasta,
     gerado em 17/09/2026 a partir de `base_municipal_v3.csv`, filtro
     tz_situacao preenchido = Ativa/Encerrada) — sem precisar passar
     --arquivo na mão.
  2. Por padrão, roda as 8 modalidades de MODALIDADES_RODADA_COMPLETA (as 6
     da triagem + Manifestação de Interesse + Credenciamento) — não as 13
     completas nem as 6 da triagem rápida. Ajuste de 18/09/2026: uma rodada
     real de ~2 dias mostrou que os 13 códigos custam caro (paginação de
     centenas de dispensas/inexigibilidades por município × 13 modalidades)
     para pouco ganho — Leilão (1, 13), Diálogo Competitivo (2), Concurso (3)
     e Pré-qualificação (11) não são, por definição legal, modalidade de
     contrato de operação/concessão de transporte, e nas amostras vistas
     devolveram poucos ou zero registros. Use --modalidades-todas-13 para
     voltar aos 13 completos (ex.: se quiser gerar evidência própria sobre
     essas 4 modalidades antes de descartá-las de vez).
  3. TEM CHECKPOINT EM DOIS NÍVEIS (ajuste de 18/09/2026 — o de nível único
     por município perdia todo o progresso de um município quando uma única
     modalidade falhava no meio de uma rodada de dias):
       a. `<saida>/_processados.txt` — município/UF completo (todas as
          modalidades daquela rodada já processadas).
       b. `<saida>/_processados_modalidade.txt` — município/UF::código da
          modalidade, marcado assim que aquela modalidade termina; os
          achados parciais de um município em andamento ficam em
          `<saida>/_partial_achados_<município>-<UF>.json` até o município
          fechar todas as modalidades (então o parcial é apagado e o
          resultado final vai para `achados_<município>-<UF>.json`).
     Rodar de novo retoma de onde parou (por modalidade, não só por
     município) em vez de repetir tudo. Use --recomecar para ignorar os
     dois checkpoints e os parciais, e rodar tudo de novo.
  4. Reaproveita 100% da lógica de busca do buscar_pncp.py (import direto,
     mesmo arquivo na mesma pasta) — qualquer correção feita lá (ex.: o
     ajuste de --bloco-dias de 16/09) vale aqui também, sem duplicar código.

⚠️ MESMO BLOQUEIO DE REDE do buscar_pncp.py: rode isto do seu terminal
normal (fora do Cowork) — pncp.gov.br está bloqueado no sandbox e na ponte.

⏱️ Estimativa grosseira (não medida, só aritmética): 175 municípios × 13
modalidades × ~6 blocos de 365 dias (abr/2021→hoje) = até ~13.650 chamadas,
~1/segundo com a pausa padrão de 1s ⇒ perto de 4 horas no pior caso (cada
bloco só custa 1 chamada se não houver muita paginação). Rode em horário
que possa deixar a máquina ligada, ou interrompa e retome quando quiser
graças ao checkpoint.

⏱️ MAIS VELOCIDADE (ajuste de 18/09/2026, 2ª rodada — aplicado a pedido do
autor, que vai rodar ainda hoje; NENHUMA das duas mudanças abaixo foi
validada contra a API real — pncp.gov.br está bloqueado neste sandbox — por
isso as duas são desligadas por padrão e a recomendação é testar em degraus
pequenos, observando a taxa de erro/`ERRO_INTERVALO` nos primeiros minutos
antes de subir):
  - **`--paralelo N`** (padrão 1 = sequencial, comportamento idêntico ao de
    antes): processa N municípios ao mesmo tempo com
    `concurrent.futures.ThreadPoolExecutor`, cada worker com sua própria
    `requests.Session` (via `threading.local`, reaproveitada entre os
    municípios que aquele worker processa) e a mesma `--pausa` entre
    chamadas dentro de cada worker. Ganho esperado ≈ Nx no tempo de parede,
    sem aumentar a taxa de chamadas por segundo de UM worker (a taxa total
    do processo sim, sobe para ≈ N/pausa chamadas/s — é isso que pode
    incomodar um rate limit não documentado). Os dois checkpoints
    (`_processados.txt`, `_processados_modalidade.txt`), o `resumo.csv` e a
    lista `linhas_resumo` em memória são protegidos por um `threading.Lock`
    único — testado offline (18/09/2026) com falha simulada em plena
    execução paralela, sem perda nem duplicação de achados. O que NÃO foi
    testado é o comportamento do PNCP em si sob paralelismo: comece com
    `--paralelo 2` ou `3`, observe uns minutos, só suba se a taxa de
    `ERRO_INTERVALO`/exceções não subir visivelmente. Ctrl+C a qualquer
    momento é seguro — o checkpoint por modalidade preserva o progresso.
  - **`--tamanho-pagina N`** (padrão 50, igual a antes): tamanho de página
    passado à API. Valores maiores reduziriam as chamadas de paginação nas
    modalidades de maior volume bruto (Dispensa, Inexigibilidade, que já
    chegaram a 750 registros brutos num único município/janela) — mas a API
    já demonstrou (16/09/2026) devolver HTTP 200 com resultado vazio/
    truncado em vez de erro para um parâmetro que não aceita, em vez de
    recusar visivelmente. Testar primeiro num único município conhecido
    (compare a contagem de registros brutos por modalidade com uma rodada
    anterior em `--tamanho-pagina 50` antes de confiar no valor maior em
    lote).

Uso:
    # rodada completa, do zero ou retomando de onde parou (8 modalidades):
    python3 buscar_pncp_completo.py

    # forçar tudo de novo, ignorando os dois checkpoints e os parciais:
    python3 buscar_pncp_completo.py --recomecar

    # voltar às 13 modalidades completas (inclui as 4 pouco plausíveis):
    python3 buscar_pncp_completo.py --modalidades-todas-13

    # Fase 2 (aprofundamento) só roda manualmente depois, com
    # buscar_pncp.py --buscar-contrato num CSV pequeno — este runner é só
    # a Fase 1 exaustiva.

Autor: Thiago Von Zeidler Gomes
Orientadora: Prof.ª Silvana Zioni
"""

import argparse
import json
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

import pandas as pd

# Reaproveita tudo do script principal (mesma pasta).
sys.path.insert(0, str(Path(__file__).resolve().parent))
import buscar_pncp as bp  # noqa: E402

MUNICIPIOS_PADRAO = Path(__file__).resolve().parent / "municipios_completo_175.csv"


def _carregar_checkpoint(saida: Path) -> set:
    arq = saida / "_processados.txt"
    if not arq.exists():
        return set()
    return set(l.strip() for l in arq.read_text(encoding="utf-8").splitlines() if l.strip())


def _marcar_processado(saida: Path, chave: str):
    arq = saida / "_processados.txt"
    with arq.open("a", encoding="utf-8") as f:
        f.write(chave + "\n")


def _carregar_checkpoint_modalidade(saida: Path) -> set:
    arq = saida / "_processados_modalidade.txt"
    if not arq.exists():
        return set()
    return set(l.strip() for l in arq.read_text(encoding="utf-8").splitlines() if l.strip())


def _marcar_modalidade_processada(saida: Path, chave: str, cod_mod: int):
    arq = saida / "_processados_modalidade.txt"
    with arq.open("a", encoding="utf-8") as f:
        f.write(f"{chave}::{cod_mod}\n")


def _partial_path(saida: Path, municipio: str, uf: str) -> Path:
    return saida / f"_partial_achados_{municipio}-{uf}.json".replace("/", "-")


_local = threading.local()


def _sessao_do_worker():
    """Uma requests.Session por thread, reaproveitada entre os municípios que
    aquela thread processa — equivalente à sessão única de antes quando
    --paralelo 1 (só existe uma thread de trabalho nesse caso)."""
    if not hasattr(_local, "sessao"):
        _local.sessao = bp._sessao()
    return _local.sessao


def _processar_municipio(i, row, total, modalidades, data_ini, data_fim, args, saida,
                          modalidades_feitas, lock, linhas_resumo, resumo_path):
    """Processa um município (todas as modalidades pendentes dele), com checkpoint por
    modalidade. Extraído do corpo de main() em 18/09/2026 para poder rodar tanto
    sequencialmente (--paralelo 1, comportamento idêntico ao de antes) quanto em paralelo
    via ThreadPoolExecutor — o acesso aos dois arquivos de checkpoint, ao resumo.csv e à
    lista `linhas_resumo` compartilhada é protegido por `lock` (um único
    threading.Lock, criado em main()); tudo o que não toca esse estado compartilhado
    (a própria busca na API) roda livre, sem lock, para não serializar o paralelismo."""
    municipio, uf, ibge = row["municipio"], row["uf"], row["cod_ibge"]
    chave = f"{municipio}/{uf}"
    sessao = _sessao_do_worker()
    print(f"\n=== [{i+1}/{total}] {chave} (IBGE {ibge}) ===")

    parcial_arq = _partial_path(saida, municipio, uf)
    achados = []
    if parcial_arq.exists():
        try:
            achados = json.loads(parcial_arq.read_text(encoding="utf-8"))
            print(f"  ↻ [{chave}] retomando: {len(achados)} achado(s) já salvos de "
                  f"modalidade(s) anterior(es) deste município nesta rodada.")
        except Exception:
            achados = []

    interrompido = False
    for cod_mod, nome_mod in modalidades.items():
        chave_mod = f"{chave}::{cod_mod}"
        with lock:
            ja_feita = chave_mod in modalidades_feitas
        if ja_feita:
            continue
        try:
            achados_mod = bp.buscar_modalidade(sessao, ibge, cod_mod, nome_mod, data_ini, data_fim,
                                                args.pausa, tamanho_pagina=args.tamanho_pagina,
                                                bloco_dias=args.bloco_dias)
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(f"  ⚠️ [{chave}] ERRO na modalidade [{nome_mod}]: {e!r} — município fica "
                  f"pendente (retoma a partir desta modalidade na próxima rodada; as "
                  f"modalidades já concluídas deste município nesta rodada não se perdem).")
            interrompido = True
            break
        achados.extend(achados_mod)
        # checkpoint por modalidade + parcial gravados assim que cada modalidade termina —
        # uma queda no meio de um município não perde o que já foi feito dele. Protegido por
        # lock porque, em paralelo, outra thread pode estar escrevendo o MESMO arquivo de
        # checkpoint (de outro município) ao mesmo tempo.
        with lock:
            parcial_arq.write_text(json.dumps(achados, ensure_ascii=False), encoding="utf-8")
            _marcar_modalidade_processada(saida, chave, cod_mod)
            modalidades_feitas.add(chave_mod)

    if interrompido:
        return

    print(f"  [{chave}] {len(achados)} contratação(ões) com termo de transporte no objeto.")

    if achados:
        arq = saida / f"achados_{municipio}-{uf}.json".replace("/", "-")
        arq.write_text(
            json.dumps({"contratacoes": achados, "contratos": []}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"  📄 [{chave}] salvo: {arq}")

    linhas_novas = []
    for a in achados:
        orgao = a.get("orgaoEntidade", {}) or {}
        linhas_novas.append({
            "municipio": municipio, "uf": uf, "cod_ibge": ibge,
            "tipo": "contratacao",
            "modalidade": a.get("_modalidade_nome", ""),
            "orgao": orgao.get("razaoSocial", ""),
            "cnpj_orgao": orgao.get("cnpj", ""),
            "objeto": (a.get("objetoCompra") or "")[:300],
            "valor_estimado": a.get("valorTotalEstimado"),
            "data_publicacao": a.get("dataPublicacaoPncp"),
            "link_pncp": a.get("linkSistemaOrigem") or a.get("numeroControlePNCP"),
        })

    # checkpoint de município + resumo gravados ao fechar todas as modalidades; o parcial
    # já cumpriu seu papel (proteger o meio do caminho) e é apagado. Tudo dentro do lock:
    # linhas_resumo é compartilhada entre threads, e o resumo.csv é reescrito por inteiro
    # a cada município (mesma lógica de antes) — duas threads escrevendo ao mesmo tempo
    # corromperiam o arquivo sem essa proteção.
    with lock:
        linhas_resumo.extend(linhas_novas)
        pd.DataFrame(linhas_resumo).to_csv(resumo_path, index=False, encoding="utf-8-sig")
        _marcar_processado(saida, chave)
        parcial_arq.unlink(missing_ok=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--arquivo", default=str(MUNICIPIOS_PADRAO),
                     help=f"CSV municipio,uf,cod_ibge (padrão: {MUNICIPIOS_PADRAO.name}, os 175 da base-mestre)")
    ap.add_argument("--saida", default="resultados_completo")
    ap.add_argument("--data-inicial", default="2021-04-01")
    ap.add_argument("--data-final", default=None, help="AAAA-MM-DD, padrão hoje")
    ap.add_argument("--bloco-dias", type=int, default=365)
    ap.add_argument("--pausa", type=float, default=1.0)
    ap.add_argument("--recomecar", action="store_true",
                     help="ignora os checkpoints (município e modalidade) e os parciais, "
                          "reprocessa todos os municípios do zero")
    ap.add_argument("--modalidades-todas-13", action="store_true",
                     help="usa as 13 modalidades completas (MODALIDADES_PADRAO) em vez do "
                          "padrão de 8 (MODALIDADES_RODADA_COMPLETA, ajuste de 18/09/2026) — "
                          "inclui Leilão (1,13), Diálogo Competitivo (2), Concurso (3) e "
                          "Pré-qualificação (11), pouco plausíveis para este tipo de contrato "
                          "mas mantidas disponíveis para quem quiser exaustão total")
    ap.add_argument("--paralelo", type=int, default=1,
                     help="nº de municípios processados ao mesmo tempo (padrão 1 = "
                          "sequencial, comportamento idêntico ao de antes deste ajuste). "
                          "NÃO testado contra a API real — comece com 2 ou 3 e observe a "
                          "taxa de erro antes de subir. Ver nota no docstring do módulo.")
    ap.add_argument("--tamanho-pagina", type=int, default=50,
                     help="tamanhoPagina passado à API (padrão 50, igual a antes). Valores "
                          "maiores NÃO foram testados — a API pode devolver 200 com "
                          "resultado vazio/truncado em vez de erro. Teste num único "
                          "município antes de usar em lote. Ver nota no docstring.")
    args = ap.parse_args()

    data_ini = date.fromisoformat(args.data_inicial)
    data_fim = date.fromisoformat(args.data_final) if args.data_final else date.today()
    modalidades = bp.MODALIDADES_PADRAO if args.modalidades_todas_13 else bp.MODALIDADES_RODADA_COMPLETA

    saida = Path(args.saida)
    saida.mkdir(exist_ok=True, parents=True)

    if args.recomecar:
        (saida / "_processados.txt").unlink(missing_ok=True)
        (saida / "_processados_modalidade.txt").unlink(missing_ok=True)
        for parcial in saida.glob("_partial_achados_*.json"):
            parcial.unlink(missing_ok=True)
    ja_feitos = _carregar_checkpoint(saida)
    modalidades_feitas = _carregar_checkpoint_modalidade(saida)

    alvos = pd.read_csv(args.arquivo, dtype={"cod_ibge": str})
    alvos["cod_ibge"] = alvos["cod_ibge"].str.strip()

    _rotulo_modalidades = "13 completas" if args.modalidades_todas_13 else "8 (MODALIDADES_RODADA_COMPLETA)"
    print(f"Rodada completa: {len(alvos)} município(s) × {len(modalidades)} modalidades "
          f"({_rotulo_modalidades}) × {data_ini.isoformat()}–{data_fim.isoformat()}.")
    if ja_feitos:
        print(f"↻ Retomando: {len(ja_feitos)} município(s) já processado(s) no checkpoint "
              f"({saida}/_processados.txt) — pulando esses. Use --recomecar para ignorar.")
    print("⚠️ Rodando fora do Cowork? Este script (como o buscar_pncp.py) NÃO funciona "
          "dentro do sandbox/ponte — pncp.gov.br está bloqueado nos dois ambientes "
          "testados em 16/09/2026. Rode do seu terminal normal.\n")

    linhas_resumo = []
    resumo_path = saida / "resumo.csv"
    # Se já existe resumo de uma rodada anterior (retomada), carrega para não perder.
    if resumo_path.exists() and not args.recomecar:
        try:
            linhas_resumo = pd.read_csv(resumo_path).to_dict("records")
        except Exception:
            linhas_resumo = []

    pendentes = [
        (i, row) for i, row in alvos.iterrows()
        if f"{row['municipio']}/{row['uf']}" not in ja_feitos
    ]
    print(f"{len(pendentes)} de {len(alvos)} município(s) a processar nesta rodada.")
    if args.paralelo > 1:
        print(f"⚡ Rodando com --paralelo {args.paralelo} — NÃO testado contra a API real "
              f"nesta sessão. Observe a saída dos primeiros municípios; se a taxa de erro "
              f"subir visivelmente, interrompa (Ctrl+C, o checkpoint preserva o progresso) "
              f"e rode de novo com --paralelo menor.\n")
    else:
        print()

    lock = threading.Lock()

    if args.paralelo <= 1:
        for i, row in pendentes:
            _processar_municipio(i, row, len(alvos), modalidades, data_ini, data_fim, args,
                                  saida, modalidades_feitas, lock, linhas_resumo, resumo_path)
    else:
        with ThreadPoolExecutor(max_workers=args.paralelo) as executor:
            futuros = {
                executor.submit(_processar_municipio, i, row, len(alvos), modalidades, data_ini,
                                 data_fim, args, saida, modalidades_feitas, lock, linhas_resumo,
                                 resumo_path): f"{row['municipio']}/{row['uf']}"
                for i, row in pendentes
            }
            for futuro in as_completed(futuros):
                chave = futuros[futuro]
                try:
                    futuro.result()
                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    print(f"  ⚠️ [{chave}] erro não tratado na thread: {e!r} — município fica "
                          f"pendente, retoma na próxima rodada.")

    print(f"\n=== Rodada completa: {len(linhas_resumo)} linha(s) de achado em "
          f"{len(pd.DataFrame(linhas_resumo)['municipio'].unique()) if linhas_resumo else 0} "
          f"município(s) ===")
    print(f"Detalhe em {resumo_path} e um .json por município com achado.")
    print("\n➡️ Próximo passo: revise o resumo.csv, monte um CSV menor só com os casos "
          "relevantes, e rode buscar_pncp.py --buscar-contrato (Fase 2) nesse subconjunto.")


if __name__ == "__main__":
    main()
