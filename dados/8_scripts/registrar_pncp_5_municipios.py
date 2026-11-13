# -*- coding: utf-8 -*-
"""
Registra, em 5 fichas municipais (Mata de São João/BA, Palmas/PR, Cantagalo/RJ,
Mendes/RJ, Vilhena/RO), os achados relevantes da varredura PNCP em andamento
(buscar_pncp_completo.py, rodada de 18/09/2026, 97/175 municípios processados
no momento desta triagem) — os únicos 5, dos 52 municípios com >=1 achado no
PNCP até aqui, cujo objeto de contratação menciona explicitamente gratuidade/
tarifa zero sem termo de ruído (transporte escolar, de pacientes, etc.).

Não afirmo operador vencedor: são registros de PROCESSO de contratação
(edital/pregão/dispensa), não de resultado/vencedor — o PNCP consultado aqui
não confirma quem ganhou. Não infiro isso.
"""
import os, sys

ROOT = os.path.expanduser("~/mnt/doutorado")

def read(fn):
    p = os.path.join(ROOT, fn)
    with open(p, encoding="utf-8") as f:
        return f.read()

def write(fn, content):
    p = os.path.join(ROOT, fn)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)

def apply_replace(fn, old, new, expect=1):
    c = read(fn)
    n = c.count(old)
    if n != expect:
        print(f"ABORT: {fn} — esperado {expect} ocorrência(s), encontrado {n}")
        print("----- ANCHOR -----")
        print(repr(old[:300]))
        sys.exit(1)
    c = c.replace(old, new)
    write(fn, c)
    print(f"OK replace: {fn} (count={n})")

ANCORA = "- Análise: [[Analise Legislacao Tarifa Zero]] · [[Analise das Legislacoes de Tarifa Zero]]"

FICHAS = [
  dict(
    arq="04 - Análises/Casos municipais/Fichas por município/Ficha - Mata de São João (BA).md",
    bloco="""
📄 **Achado PNCP (18/09/2026) — varredura de contratações em andamento (buscar_pncp_completo.py):** 2 processos de **Concorrência Eletrônica** localizados, ambos com objeto "Concessão dos serviços de Transporte Público Gratuito Intramunicipal fundamentado através da Lei nº 945 de 11 de dezembro de 2023" — confirma documentalmente, por fonte independente do SAPL, que a concessão foi a mercado. Publicados via LICITANET: 04/03/2024 (valor estimado R$ 2.461.879,05) e 20/06/2024 (valor estimado R$ 2.675.317,73) — dois processos distintos, não sei se o 2º é republicação/correção do 1º (deserto?) ou objeto genuinamente diferente; não decido isso aqui. 🔴 **Não nomeiam o operador vencedor** — são editais de concorrência, não resultado de julgamento; "Operador: —" em §2 segue não resolvido por este achado. Links: portal.licitanet.com.br (acesso-visitante, ambos).
""",
  ),
  dict(
    arq="04 - Análises/Casos municipais/Fichas por município/Ficha - Palmas (PR).md",
    bloco="""
📄 **Achado PNCP (18/09/2026) — varredura de contratações em andamento (buscar_pncp_completo.py), IBGE 4117602 confirmado (não é Palmas/TO):** 3 processos de **Pregão Eletrônico** para locação de ônibus com condutor para o "projeto de transporte coletivo municipal urbano gratuito". 🎯 **Achado relevante — possível número de lei ainda não registrado nesta ficha:** dois dos três objetos citam **"Lei municipal nº 3.046/2023"** como base do programa — a Observação atual desta ficha só registra "decreto (ago/2022); nº não confirmado", sem essa lei. 🔴 **Não decido aqui se é a norma instituidora, uma lei posterior que reorganiza o programa, ou uma coincidência de numeração com a Lei 3.046/2023 de Palmas/TO** (mesmo número, município diferente — confirmado por IBGE 4117602 vs. o de Palmas/TO, não é erro de casamento) — fica para o autor ler o texto da Lei 3.046/2023 de Palmas/**PR** especificamente antes de tratar isso como resolvido. Processos: Registro de preço, publicado 26/07/2022 (valor estimado R$ 4.633.992,00, sem citar a lei); contratação direta citando a Lei 3.046/2023, publicada 27/05/2024 (valor estimado R$ 3.647.535,00) e reaberta/republicada 16/08/2024 (mesmo valor). 🔴 Não nomeiam o operador vencedor.
""",
  ),
  dict(
    arq="04 - Análises/Casos municipais/Fichas por município/Ficha - Cantagalo (RJ).md",
    bloco="""
📄 **Achado PNCP (18/09/2026) — varredura de contratações em andamento (buscar_pncp_completo.py):** 1 processo de **Pregão Eletrônico**, publicado 08/04/2026, objeto "Contratação de empresa especializada para a prestação de serviços públicos de Transporte Coletivo de Passageiros no Município de Cantagalo/RJ, abrangendo as áreas urbanas e rurais, sob o regime de Tarifa Zero (subsídio integral), **com remuneração por quilômetro rodado**" — valor estimado R$ 16.769.619,13. 🎯 **Achado relevante para a régua analítica (Cap 6):** "remuneração por quilômetro rodado" é o critério-chave do próprio Cap 6 para distinguir T3-comum de T3-bolsa-empresário (remuneração por km/custo operacional vs. por passageiro) — este processo confirma remuneração por km, um dado que a ficha não tinha antes. Não decido a classificação T3 aqui; fica para quem preencher a seção "Régua analítica (Cap 6)" usar este achado. 🔴 Não nomeia o operador vencedor deste pregão — não sei se resultou em contrato assinado nem com quem.
""",
  ),
  dict(
    arq="04 - Análises/Casos municipais/Fichas por município/Ficha - Mendes (RJ).md",
    bloco="""
📄 **Achado PNCP (18/09/2026) — varredura de contratações em andamento (buscar_pncp_completo.py):** 1 processo de **Pregão Eletrônico**, publicado 21/02/2025, objeto "locação de veículos, do tipo ônibus urbano, micro-ônibus e van, com motorista para atendimento específico ao transporte público diário e **gratuito** de passageiros" — valor estimado R$ 3.110.370,72. Compatível em cronologia com o lançamento do programa em 29/04/2025 já registrado nesta ficha (pregão ~2 meses antes do lançamento — plausível para um processo de contratação anteceder a operação). 🔴 Não confirma o número da lei instituidora (segue "não localizado") nem nomeia o operador vencedor.
""",
  ),
  dict(
    arq="04 - Análises/Casos municipais/Fichas por município/Ficha - Vilhena (RO).md",
    bloco="""
📄 **Achado PNCP (18/09/2026) — varredura de contratações em andamento (buscar_pncp_completo.py):** 1 processo de **Dispensa de Licitação**, publicado 12/05/2026, objeto "**Processo Emergencial Tarifa Zero** para contratação de empresa especializada para prestação de serviços de Transporte Coletivo Urbano, visando o transporte da população da zona urbana do município de Vilhena" — valor estimado R$ 2.010.099,18. 🔴 **Achado relevante para a trajetória, não decidido aqui:** esta dispensa é de mai/2026, **~8 meses depois** da Lei nº 6.557/2025 (02/09/2025) já registrada como instituidora. Não sei se isso é (a) uma recontratação emergencial por fim/rompimento do contrato original, (b) uma segunda etapa/expansão do mesmo programa, ou (c) evidência de instabilidade operacional — as três leituras são compatíveis com o rótulo "Processo Emergencial" no objeto. Fica como pergunta em aberto para o autor, relevante ao Cap 5 (trajetória) e ao já registrado "portão de cadastro" (Art. 10 da Lei 6.557/2025, ver achados de normas acima). 🔴 Não nomeia o operador vencedor desta dispensa.
""",
  ),
]

for f in FICHAS:
    apply_replace(f["arq"], ANCORA, f["bloco"].strip("\n") + "\n" + ANCORA)

print("\nTODOS OS PASSOS CONCLUÍDOS COM SUCESSO.")
