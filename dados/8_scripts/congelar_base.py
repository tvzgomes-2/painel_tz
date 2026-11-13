#!/usr/bin/env python3
"""congelar_base.py — grava um novo congelamento da base (cópias + SHA-256), a nota de números canônicos, arquiva o Registro de
alterações do congelamento anterior e abre um Registro novo. O congelamento anterior nunca é apagado.
Autor: Thiago Von Zeidler Gomes · Orientadora: Prof.ª Dra. Silvana Zioni · escrito em 17/10/2026 (decisão do autor de recongelar).
Uso (da raiz do cofre): python _meta/scripts/congelar_base.py AAAA-MM-DD            → simula (mostra os números)
                         python _meta/scripts/congelar_base.py AAAA-MM-DD --gravar   → grava
Depois: python _meta/scripts/verificar_congelamento.py (passa a ler o congelamento mais recente) tem de dar 0 diferenças."""
import os, sys, re, shutil, hashlib, datetime, collections, openpyxl
sys.path.insert(0, os.path.join(os.getcwd(), "_meta/scripts")); import numeros_base as nb
R = os.getcwd(); D = sys.argv[1]; G = "--gravar" in sys.argv
# 18/10/2026: --motivo "..." substitui a justificativa da nota; --regra "..." entra no Registro novo como regra de alteração
def _arg(k, d=""):
    return sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
MOTIVO = _arg("--motivo", "decisão do autor, que autorizou recongelar depois da varredura de downloads de 17/10/2026"); REGRA = _arg("--regra")
MESES = ["janeiro","fevereiro","março","abril","maio","junho","julho","agosto","setembro","outubro","novembro","dezembro"]
dd = datetime.date.fromisoformat(D); BR = dd.strftime("%d/%m/%Y"); TAG = dd.strftime("%d-%m-%Y")
DATA = os.path.join(R, "03 - Dados/_data"); NOVO = os.path.join(DATA, f"congelamento-{D}")
ANT = sorted(x for x in os.listdir(DATA) if x.startswith("congelamento-") and x != f"congelamento-{D}")[-1]
ANTD = datetime.date.fromisoformat(ANT.replace("congelamento-", "")); ANTBR = ANTD.strftime("%d/%m/%Y"); ANTTAG = ANTD.strftime("%d-%m-%Y")
ARQ = [("03 - Dados/_data/casos por fonte/Municípios TZ - consolidado.xlsx", "Municípios TZ - consolidado.xlsx"),
       ("03 - Dados/_data/casos por fonte/Tipologias TZ - consolidado.xlsx", "Tipologias TZ - consolidado.xlsx"),
       ("04 - Análises/Pesquisa legal/Controle unificado dos casos — base, régua, log e leitura.xlsx", "Controle unificado dos casos — base, régua, log e leitura.xlsx"),
       ("04 - Análises/Pesquisa legal/Log de busca jurídica e contratual — municípios.md", "Log de busca jurídica e contratual — municípios.md.txt"),
       ("04 - Análises/Pesquisa legal/e-SIC — pedidos de informação por município.md", "e-SIC — pedidos de informação por município.md.txt"),
       ("05 - Referências/Conceitos/Regras de classificacao das reguas.md", "Regras de classificacao das reguas.md.txt"),
       ("04 - Análises/Pesquisa legal/Normas padronizadas/_índice - Normas padronizadas.md", "_índice - Normas padronizadas.md.txt")]
for s, _ in ARQ: assert os.path.isfile(os.path.join(R, s)), s
REG = os.path.join(R, "03 - Dados/Registro de alterações pós-congelamento.md")
REGARQ = os.path.join(R, f"03 - Dados/Registro de alterações pós-congelamento — {ANTTAG} a {TAG}.md")
NOTA = os.path.join(R, f"03 - Dados/Congelamento da base — {TAG}.md"); NOTANT = os.path.join(R, f"03 - Dados/Congelamento da base — {ANTTAG}.md")
VER = os.path.join(R, "_meta/scripts/verificar_congelamento.py")
a = nb.contar(os.path.join(R, ARQ[0][0]), os.path.join(R, ARQ[1][0]))
b = nb.contar(os.path.join(DATA, ANT, "Municípios TZ - consolidado.xlsx"), os.path.join(DATA, ANT, "Tipologias TZ - consolidado.xlsx"))
reg_txt = open(REG, encoding="utf-8").read()
nreg = sum(1 for ln in reg_txt.splitlines() if re.match(r"\|\s*\d{2}/\d{2}/\d{4}\s*\|", ln))
# listas
M = nb.ler(os.path.join(R, ARQ[0][0]), "consolidado")
parc = [f"{d['Município']} ({nb.s(d.get('Régua — subtipo'))})" for d in M if d.get("Situação") == "Ativa" and nb.s(d.get("Régua — aba")) == "2 Parcial"]
enc = nb.ler(os.path.join(R, ARQ[1][0]), "3 Encerradas")
encl = [f"{d['Município']} ({nb.s(d.get('Subtipo (antes de encerrar)')) or 'a decidir'})" for d in enc]
def L(c, ordem=None): return nb.fmt(c, ordem)
def dif(k, fm=lambda x: x):
    return "" if a[k] == b[k] else f" (em {ANTBR}: {fm(b[k])})"
E = a["estado"]; fech = sum(v for k, v in E.items() if k.startswith("Fechado")); agu = sum(v for k, v in E.items() if k.startswith("Aguarda"))
Eb = b["estado"]; fechb = sum(v for k, v in Eb.items() if k.startswith("Fechado")); agub = sum(v for k, v in Eb.items() if k.startswith("Aguarda"))
PO = ["direta ou empresa pública", "contrato com operador", "locação de veículos", "não encontrada/não apurada"]
GO = ["em grupo econômico", "isolado na rede", "sem operador privado", "não apurado", "fora dos 6 CNAEs", "outros"]
txt = f"""---
title: "Congelamento da base — {TAG}"
tags:
  - dados
  - congelamento
  - canonico
publish: false
created: {D}
---

# Congelamento da base — {BR}

Autor: Thiago Von Zeidler Gomes
Orientadora: Prof.ª Dra. Silvana Zioni

> [!important] Números canônicos
> A partir de {BR}, os números desta nota são os **canônicos** da tese ({MOTIVO}). Substitui o [[Congelamento da base — {ANTTAG}]]. No texto, citar como "base de {dd.day} de {MESES[dd.month-1]} de {dd.year}". Toda alteração na base-mestre ou na régua entra no [[Registro de alterações pós-congelamento]] (aberto de novo, vazio, em {BR}); as {nreg} linhas do período {ANTBR}–{BR} estão arquivadas em [[Registro de alterações pós-congelamento — {ANTTAG} a {TAG}]]. Números gerados por script (`_meta/scripts/congelar_base.py`, contagens em `numeros_base.py`): rodar de novo dá os mesmos números.

## 1. Arquivos congelados

Cópias em `03 - Dados/_data/congelamento-{D}/` (notas como `.md.txt`), com SHA-256 em `MANIFESTO-sha256.txt`. O congelamento de {ANTBR} continua em `congelamento-{ANT[13:]}/`, intacto. A tabela de grupos econômicos (`Tabela mestre - Empresas, Grupos e Clusters (ago-2026).xlsx`, 12/08/2026) segue como versão fechada: 327 grupos, 7.681 empresas, 207 clusters.

## 2. Universo

| Recorte | Nº | Observação |
|---|---|---|
| Linhas da base-mestre | {a['linhas']} | {b['linhas']} em {ANTBR} |
| **Em escopo (municípios com Tarifa Zero)** | **{a['escopo']}** | = {a['ativas']} ativas + {a['encerradas']} encerradas{dif('escopo')} |
| Ativas | {a['ativas']} | {L(a['aba_ativas'])} |
| Encerradas | {a['encerradas']} | {", ".join(encl)} |
| Regulamentada e não implantada (A.1.6) | {len(a['fora']['Regulamentada — não implantada'])} | {", ".join(a['fora']['Regulamentada — não implantada'])} |
| Excluídas | {len(a['fora']['Excluída (fora de escopo)'])} | {", ".join(a['fora']['Excluída (fora de escopo)'])} |
| Pistas (a verificar) | {len(a['fora']['Pista (a verificar)'])} | {", ".join(a['fora']['Pista (a verificar)'])}{dif('fora', lambda x: ", ".join(x['Pista (a verificar)']))} |

Ativas na Parcial (aba 2 da base-mestre): {", ".join(parc)}. **Qual citar:** {a['escopo']} para "municípios com Tarifa Zero"; {a['ativas']} para "ativas"; {a['aba_ativas'].get('1 Universal', 0)} para a Tarifa Zero universal. Mesmo total de {ANTBR}, com composição diferente (entradas e saídas no arquivo do Registro).

## 3. Régua descritiva (abas da planilha de tipologias; nunca a RESUMO)

| Aba | Registros | Subtipos |
|---|---|---|
| 1 Universal | {a['regua'].get('1 Universal')} | {L(a['aba1'], ['1a', '1b', '1c', '1d', 'sem subtipo'])} |
| 2 Parcial | {a['regua'].get('2 Parcial')} (uma linha por município, A.1.15) | por subtipo, não exclusivo: {L(a['aba2_nao_exclusivo'], ['2a', '2b', '2c', '2d', '2e'])} |
| 3 Encerradas | {a['regua'].get('3 Encerradas')} | último desenho: {L(a['aba3'])}{dif('aba3', L)} |
""" + "".join(f"| {k} | {v} | — |\n" for k, v in a["regua"].items() if k not in ("1 Universal", "2 Parcial", "3 Encerradas")) + f"""
Dos {a['regua'].get('2 Parcial')} municípios da aba 2, só {len(parc)} estão na base-mestre; os outros são programas parciais em cidades sem Tarifa Zero e não somam ao escopo.

## 4. Completude (A.2e) — coluna "Estado terminal"

| Estado | Nº | em {ANTBR} |
|---|---|---|
| **Fechado** | **{fech}** | {fechb} |
| — com norma | {E.get('Fechado — com norma', 0)} | {Eb.get('Fechado — com norma', 0)} |
| — política sem norma | {E.get('Fechado — política sem norma', 0)} | {Eb.get('Fechado — política sem norma', 0)} |
| — encerrada | {E.get('Fechado — encerrada', 0)} | {Eb.get('Fechado — encerrada', 0)} |
| **Aguarda e-SIC** | **{agu}** | {agub} |
| — enviado | {E.get('Aguarda e-SIC — enviado', 0)} | {Eb.get('Aguarda e-SIC — enviado', 0)} |
| — pronto para envio | {E.get('Aguarda e-SIC — pronto para envio', 0)} | {Eb.get('Aguarda e-SIC — pronto para envio', 0)} |
| **Lacuna declarada (fim da coleta, 11/11/2026)** | **{E.get('Lacuna declarada (fim da coleta)', 0)}** | {Eb.get('Lacuna declarada (fim da coleta)', 0)} |
| **Aberto** | **{E.get('Aberto/outro', 0)}** | {Eb.get('Aberto/outro', 0)} |

## 5. Prova, norma, operador e contrapartida (casos em escopo)

| Indicador | {BR} | {ANTBR} |
|---|---|---|
| Prova de operação 2025–26 (ativas) | {L(a['prova'], ['atende', 'a conferir', 'não atende', 'sem prova datada'])} | {L(b['prova'], ['atende', 'a conferir', 'não atende', 'sem prova datada'])} |
| Norma lida (A.2e) | {L(a['norma'], ['lida com arquivo', 'lida sem arquivo', 'não existe (política sem norma)', 'não localizada'])} | {L(b['norma'], ['lida com arquivo', 'lida sem arquivo', 'não existe (política sem norma)', 'não localizada'])} |
| Operador com CNPJ comprovado | {a['cnpj']} | {b['cnpj']} |
| Prestação (eixo 2) | {L(a['prestacao'], PO)} | {L(b['prestacao'], PO)} ¹ |
| Operador × grupo econômico | {L(a['opge'], GO)} | {L(b['opge'], GO)} |
| Contrapartida (camada 1, regra B.1.3) | {L(a['contrap'], ['com', 'sem', 'não apurado'])} | não codificada |

¹ A nota de {ANTBR} publicou 62 · 57 · 14 · 53, agrupando a prestação à mão; a regra escrita em `numeros_base.py` dá 63 · 56 · 14 · 53 para a mesma base (um caso muda de grupo). Daqui em diante vale a regra do script.

**Leitura:** a frente dos CNPJs e as rodadas de busca de 12 a 17/10 reduziram a prestação "não encontrada" de {b['prestacao'].get('não encontrada/não apurada')} para {a['prestacao'].get('não encontrada/não apurada')} e o operador "não apurado" de {b['opge'].get('não apurado')} para {a['opge'].get('não apurado')}; o operador em grupo econômico passou de {b['opge'].get('em grupo econômico')} para {a['opge'].get('em grupo econômico')}. Os números descrevem a base; não testam a hipótese (ver [[Controle estratégico dos números — 11-10-2026]]).

## 6. Perfil dos {a['escopo']}

| Recorte | Distribuição |
|---|---|
| UF | {L(a['uf'])} |
| População (Censo 2022) | {L(a['pop'], ['< 10 mil', '10–20 mil', '20–50 mil', '50–100 mil', '100–500 mil', '≥ 500 mil', 'NA'])} |
| Ano de início | {L(a['ano'], ['≤ 2000', '2001–2012', '2013–2019', '2020–2022', '2023', '2024', '2025', '2026', 'NA'])} |
| Nº de levantamentos que registram o caso | {L(a['lev'], ['0', '1', '2', '3', '4', '5+', 'NA'])} |
| PlanMob declarado (MUNIC) | {L(a['planmob'])} |

## 7. Citações de fonte (não confundir com a base)

137 (Santini, 2025) · 143 municípios e 8 reversões (NTU, Pesquisa Temática Tarifa Zero, 3ª ed., 10/06/2026) · 168 (NTU, relatório diário, não citável).

## 8. Números superados

Todos os do [[Congelamento da base — {ANTTAG}]] que diferem desta nota (o total de {a['escopo']} se mantém). Ao citar números de {ANTBR} em texto já escrito, trocar pelos desta nota.

## Ligações

- [[Registro de alterações pós-congelamento]] · [[Registro de alterações pós-congelamento — {ANTTAG} a {TAG}]]
- [[Congelamento da base — {ANTTAG}]] · [[Controle estratégico dos números — 11-10-2026]]
- [[Regras de classificacao das reguas]] · [[Log de busca jurídica e contratual — municípios]] · [[e-SIC — pedidos de informação por município]]
"""
print(txt[:200]); print("… linhas do Registro a arquivar:", nreg)
if not G: print(txt); sys.exit(0)
assert not os.path.exists(NOVO), "congelamento já existe: " + NOVO
os.makedirs(NOVO); man = []
for s, d in ARQ:
    shutil.copy2(os.path.join(R, s), os.path.join(NOVO, d)); man.append(f"{hashlib.sha256(open(os.path.join(NOVO, d), 'rb').read()).hexdigest()}  {d}")
open(os.path.join(NOVO, "MANIFESTO-sha256.txt"), "w", encoding="utf-8").write("\n".join(man) + "\n")
bk = os.path.join(R, "_meta/_backups", "congelar-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")); os.makedirs(bk)
for p in (REG, NOTANT, VER): shutil.copy2(p, bk)
# Registro: arquiva e abre novo
arq = reg_txt.replace('title: "Registro de alterações pós-congelamento"', f'title: "Registro de alterações pós-congelamento — {ANTTAG} a {TAG}"', 1)
arq = arq.replace("# Registro de alterações pós-congelamento\n", f"# Registro de alterações pós-congelamento — {ANTTAG} a {TAG} (arquivado)\n\n> [!note] Arquivado em {BR}\n> Registro do congelamento de {ANTBR}, encerrado no recongelamento de {BR} ({nreg} linhas). O registro vivo é o [[Registro de alterações pós-congelamento]]; os números novos estão no [[Congelamento da base — {TAG}]].\n", 1)
open(REGARQ, "w", encoding="utf-8").write(arq)
i = reg_txt.index("|---|---|---|---|---|---|---|---|---|---|\n") + len("|---|---|---|---|---|---|---|---|---|---|\n")
cab = reg_txt[:i].replace(f"[[Congelamento da base — {ANTTAG}]]", f"[[Congelamento da base — {TAG}]]").replace(f"base de {ANTBR}", f"base de {BR}").replace("base de 11/10/2026", f"base de {BR}")
cab = cab.replace("created: " + ANT[13:], "created: " + D, 1)
cab = cab.replace("# Registro de alterações pós-congelamento\n", f"# Registro de alterações pós-congelamento\n\n> [!info] Registro aberto de novo em {BR}\n> Vale para o [[Congelamento da base — {TAG}]]. As {nreg} linhas de {ANTBR} a {BR} estão em [[Registro de alterações pós-congelamento — {ANTTAG} a {TAG}]].\n" + (f"\n> [!warning] Regra de alteração a partir de {BR}\n> {REGRA}\n" if REGRA else ""), 1)
novo = cab + "\n## Efeito acumulado nos números canônicos\n\n| Data | Número | Antes | Depois | Por quê |\n|---|---|---|---|---|\n\n## Ligações\n\n" + f"- [[Congelamento da base — {TAG}]]\n- [[Registro de alterações pós-congelamento — {ANTTAG} a {TAG}]]\n- [[Controle estratégico dos números — 11-10-2026]]\n"
open(REG, "w", encoding="utf-8").write(novo)
open(NOTA, "w", encoding="utf-8").write(txt)
na = open(NOTANT, encoding="utf-8").read()
if "> [!warning] Superado" not in na:
    k = na.index(f"# Congelamento da base — {ANTBR}\n") + len(f"# Congelamento da base — {ANTBR}\n")
    na = na[:k] + f"\n> [!warning] Superado em {BR}\n> Os números canônicos agora estão no [[Congelamento da base — {TAG}]] (recongelamento, decisão do autor). Esta nota fica como histórico.\n" + na[k:]
    open(NOTANT, "w", encoding="utf-8").write(na)
print("gravado:", NOVO, "| nota:", os.path.basename(NOTA), "| registro arquivado:", os.path.basename(REGARQ), "| backup:", bk)
