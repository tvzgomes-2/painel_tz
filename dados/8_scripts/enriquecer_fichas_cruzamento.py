#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
enriquecer_fichas_cruzamento.py — insere nas fichas municipais o achado do
cruzamento PlanMob × Legislação de TPC × TZ (busca direta no SAPL da Câmara),
para os municípios em que esse cruzamento encontrou alguma das três leis.

CONTEXTO
  `Tabela cruzada - PlanMob x Legislação TPC x TZ (SAPL) (11-09-2026).xlsx`
  varreu o site SAPL das câmaras dos 850 municípios com host confirmado,
  buscando três leis por município: PlanMob, legislação de TPC estruturante
  e a lei-base da própria Tarifa Zero. Em 39 municípios a busca achou (ou
  buscou e não achou, registrando o resultado) a lei de TZ — esses 39 já
  estão nas fichas municipais (04 - Análises/Casos municipais/Fichas por
  município/), mas a ficha ainda não registra esse achado.

  Este script não decide qual fonte está certa quando há tensão entre o que
  a ficha já tinha em §5 Legislação e o que o cruzamento achou (ex.: uma
  candidata a norma na ficha vs. "não encontrei" no cruzamento, ou duas leis
  de números diferentes). Ele SINALIZA a tensão — comparando números de lei
  extraídos por regex de ambos os lados — e deixa a decisão para o autor.

USO
  python enriquecer_fichas_cruzamento.py --pasta "<caminho para Fichas por município>" \
      --cruzamento "<caminho para a xlsx>" [--simular]

  --simular: só imprime o que faria, não escreve nada (padrão: escreve).
  Idempotente: se o bloco `<!-- CRUZAMENTO-SAPL-PLANMOB-TPC-TZ:INICIO -->` já
  existir na ficha, o script pula (não duplica, não atualiza — atualização
  manual se o cruzamento for refeito).

SAÍDA
  Bloco inserido depois da seção "## 5. Legislação" (e do bloco de normas
  padronizadas, se houver), antes do próximo "## " de nível 2. Imprime no
  console um resumo por município: inserido / já tinha bloco / não achou
  seção 5 (não deveria ocorrer, mas o script não força).

Autor: Thiago Von Zeidler Gomes · Orientadora: Prof. Dra. Silvana Zioni
"""

import argparse
import datetime
import re
import shutil
import sys
from pathlib import Path

import openpyxl

MARCA_INICIO = "<!-- CRUZAMENTO-SAPL-PLANMOB-TPC-TZ:INICIO -->"
MARCA_FIM = "<!-- CRUZAMENTO-SAPL-PLANMOB-TPC-TZ:FIM -->"

# (município como está na tabela cruzada, UF) -> nome exato do arquivo da ficha
MAPEAMENTO = {
    ("Mata De São João", "BA"): "Ficha - Mata de São João (BA).md",
    ("Aquiraz", "CE"): "Ficha - Aquiraz (CE).md",
    ("Eusébio", "CE"): "Ficha - Eusébio (CE).md",
    ("Formosa", "GO"): "Ficha - Formosa (GO).md",
    ("Luziânia", "GO"): "Ficha - Luziânia (GO).md",
    ("Arcos", "MG"): "Ficha - Arcos (MG).md",
    ("Cláudio", "MG"): "Ficha - Cláudio (MG).md",
    ("Dores Do Indaiá", "MG"): "Ficha - Dores do Indaiá (MG).md",
    ("Ijaci", "MG"): "Ficha - Ijaci (MG).md",
    ("Itatiaiuçu", "MG"): "Ficha - Itatiaiuçu (MG).md",
    ("Lagoa Da Prata", "MG"): "Ficha - Lagoa da Prata (MG).md",
    ("Mário Campos", "MG"): "Ficha - Mário Campos (MG).md",
    ("Piumhi", "MG"): "Ficha - Piumhi (MG).md",
    ("Santana Do Deserto", "MG"): "Ficha - Santana do Deserto (MG).md",
    ("Sarzedo", "MG"): "Ficha - Sarzedo (MG).md",
    ("São José Da Barra", "MG"): "Ficha - São José da Barra (MG).md",
    ("Ribas Do Rio Pardo", "MS"): "Ficha - Ribas do Rio Pardo (MS).md",
    ("Carambeí", "PR"): "Ficha - Carambeí (PR).md",
    ("Centenário Do Sul", "PR"): "Ficha - Centenário do Sul (PR).md",
    ("Clevelândia", "PR"): "Ficha - Clevelândia (PR).md",
    ("Irati", "PR"): "Ficha - Irati (PR).md",
    ("Ivaiporã", "PR"): "Ficha - Ivaiporã (PR).md",
    ("Quatro Barras", "PR"): "Ficha - Quatro Barras (PR).md",
    ("Rio Branco Do Sul", "PR"): "Ficha - Rio Branco do Sul (PR).md",
    ("Cantagalo", "RJ"): "Ficha - Cantagalo (RJ).md",
    ("Comendador Levy Gasparian", "RJ"): "Ficha - Comendador Levy Gasparian (RJ).md",
    ("Conceição De Macabu", "RJ"): "Ficha - Conceição de Macabu (RJ).md",
    ("Mendes", "RJ"): "Ficha - Mendes (RJ).md",
    ("São Fidélis", "RJ"): "Ficha - São Fidélis (RJ).md",
    ("Cacoal", "RO"): "Ficha - Cacoal (RO).md",
    ("Vilhena", "RO"): "Ficha - Vilhena (RO).md",
    ("Artur Nogueira", "SP"): "Ficha - Arthur Nogueira (SP).md",
    ("Ilha Comprida", "SP"): "Ficha - Ilha Comprida (SP).md",
    ("Itaporanga", "SP"): "Ficha - Itaporanga (SP).md",
    ("Jardinópolis", "SP"): "Ficha - Jardinópolis (SP).md",
    ("Monte Mor", "SP"): "Ficha - Monte Mor (SP).md",
    ("Piedade", "SP"): "Ficha - Piedade (SP).md",
    ("Porto Feliz", "SP"): "Ficha - Porto Feliz (SP).md",
    ("Palmas", "TO"): "Ficha - Palmas (TO).md",
}

# Extrai o NÚMERO da lei/decreto (ignora o ano) a partir do texto que segue
# "Lei"/"Decreto" + qualificadores + "nº" — funciona tanto para citação em
# formato "1.279/2018" quanto "nº 1.279, de 06/06/2018" (formatos que os dois
# lados — ficha e cruzamento — usam de forma inconsistente entre si).
# Comparar por NÚMERO, não por "número/ano" inteiro, porque o ano só aparece
# de forma confiável quando a citação usa a barra.
RE_NUM_LEI = re.compile(
    r"(?:lei|decreto)[a-zçãáéíóõú]*\.?\s*(?:complementar\s+)?(?:ordin[aá]ria\s+)?"
    r"(?:municipal\s+)?n?[ºo°]?\.?\s*(\d{1,3}(?:\.\d{3})?)",
    re.IGNORECASE,
)


def ler_cruzamento(caminho_xlsx):
    wb = openpyxl.load_workbook(caminho_xlsx, data_only=True)
    ws = wb["PlanMob x TPC x TZ"]
    linhas = list(ws.iter_rows(values_only=True))
    header = linhas[0]
    idx = {h: i for i, h in enumerate(header)}
    achados = []
    for r in linhas[1:]:
        tz_lei = r[idx["TZ — base-mestre (lei)"]]
        situacao = r[idx["Situação TZ"]]
        if (tz_lei and str(tz_lei).strip()) or (situacao and str(situacao).strip()):
            achados.append({
                "municipio": r[idx["Município"]],
                "uf": r[idx["UF"]],
                "sapl": r[idx["Site da Câmara (SAPL)"]],
                "planmob": r[idx["PlanMob (lei)"]],
                "tpc": r[idx["Legislação de TPC — estruturante (lei)"]],
                "tz_lei": tz_lei,
                "situacao": situacao,
            })
    return achados


def vazio(v):
    return v is None or str(v).strip() == ""


def formatar(v, rotulo_vazio="não encontrada nesta busca"):
    return str(v).strip() if not vazio(v) else rotulo_vazio


def comparar_numeros(texto_ficha, texto_cruzamento):
    """Compara números de lei (regex) entre o que já estava na ficha (§5) e o
    achado do cruzamento. Retorna uma frase de avaliação — nunca decide."""
    if vazio(texto_cruzamento) or "não encontr" in str(texto_cruzamento).lower() or "não localizad" in str(texto_cruzamento).lower():
        if texto_ficha and RE_NUM_LEI.search(texto_ficha):
            return ("⚠️ **Tensão a resolver:** a ficha já registra uma norma candidata em §5, mas "
                    "o cruzamento buscou no SAPL e **não achou** lei de TZ. Não decidir por conta "
                    "própria — conferir se a candidata de §5 é a certa antes de tratar qualquer um "
                    "dos dois lados como resolvido.")
        return "Convergente: nem a ficha (§5) nem este cruzamento têm norma de TZ confirmada."
    def normalizar_num(s):
        return s.replace(".", "").lstrip("0") or "0"

    nums_cruzamento_raw = RE_NUM_LEI.findall(str(texto_cruzamento))
    nums_ficha_raw = RE_NUM_LEI.findall(texto_ficha or "")
    nums_cruzamento = {normalizar_num(n) for n in nums_cruzamento_raw}
    nums_ficha = {normalizar_num(n) for n in nums_ficha_raw}
    if not nums_ficha:
        return "Ficha (§5) não tinha número de norma registrado — este é o primeiro achado de número via SAPL."
    if nums_cruzamento & nums_ficha:
        return f"✅ Compatível: número já registrado em §5 aparece também neste achado ({', '.join(sorted(nums_cruzamento & nums_ficha))})."
    return (f"⚠️ **Divergência de número a resolver:** §5 registra {sorted(nums_ficha_raw)}, "
            f"este cruzamento achou {sorted(nums_cruzamento_raw)} — não presumir qual é a norma "
            f"certa sem ler as duas.")


def extrair_secao_5(texto):
    m = re.search(r"^## 5\. Legisla[cç][aã]o\s*$", texto, re.MULTILINE)
    if not m:
        return None, None, None
    inicio_conteudo = m.end()
    m_prox = re.search(r"^## ", texto[inicio_conteudo:], re.MULTILINE)
    fim_secao = inicio_conteudo + m_prox.start() if m_prox else len(texto)
    return m.start(), inicio_conteudo, fim_secao


def montar_bloco(achado):
    linhas = [
        "",
        MARCA_INICIO,
        "### 🔎 Cruzamento SAPL — PlanMob × TPC × TZ (11/09/2026)",
        "_Fonte: [[Tabela cruzada - PlanMob x Legislação TPC x TZ (SAPL)]] — busca direta no site "
        "da Câmara (SAPL) por três leis (PlanMob, legislação de TPC estruturante, lei-base da TZ), "
        "independente da base-mestre e das fontes já citadas em §5._",
        "",
        f"- **Site da Câmara (SAPL) usado na busca:** {formatar(achado['sapl'])}",
        f"- **PlanMob (lei), achado via SAPL:** {formatar(achado['planmob'])}",
        f"- **Legislação de TPC — estruturante, achado via SAPL:** {formatar(achado['tpc'])}",
        f"- **TZ — base-mestre (lei), achado via SAPL:** {formatar(achado['tz_lei'])}",
        f"- **Situação TZ (registrada nesta busca):** {formatar(achado['situacao'])}",
        "",
        f"**Avaliação (não substitui leitura do texto):** {achado['avaliacao']}",
        "",
        MARCA_FIM,
        "",
    ]
    return "\n".join(linhas)


_BACKUP_DIR = None  # criado sob demanda no 1º arquivo realmente gravado (ver _backup_antes_de_gravar)


def _backup_antes_de_gravar(caminho):
    """Copia o conteúdo atual de `caminho` para _meta/_backups/ antes de sobrescrever,
    seguindo o mesmo padrão dos demais scripts enriquecer_*.py."""
    global _BACKUP_DIR
    if _BACKUP_DIR is None:
        raiz = caminho.parents[2]  # .../Fichas por município -> Casos municipais -> 04 - Análises -> raiz
        _BACKUP_DIR = raiz / "_meta" / "_backups" / (
            "cruzamento-sapl-" + datetime.datetime.now().strftime("%Y-%m-%d_%H%M")
        )
        _BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(caminho, _BACKUP_DIR / caminho.name)


def processar_ficha(caminho, achado, simular):
    texto = caminho.read_text(encoding="utf-8")
    if MARCA_INICIO in texto:
        return "já tinha bloco (pulado)"
    inicio_titulo, inicio_conteudo, fim_secao = extrair_secao_5(texto)
    if inicio_titulo is None:
        return "🔴 não achou '## 5. Legislação' — não escrito, conferir manualmente"
    texto_secao5 = texto[inicio_conteudo:fim_secao]
    achado["avaliacao"] = comparar_numeros(texto_secao5, achado["tz_lei"])
    bloco = montar_bloco(achado)
    novo_texto = texto[:fim_secao].rstrip("\n") + "\n" + bloco + "\n" + texto[fim_secao:]
    if not simular:
        _backup_antes_de_gravar(caminho)
        caminho.write_text(novo_texto, encoding="utf-8")
    return f"inserido — {achado['avaliacao'][:70]}..."


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--pasta", required=True, help="pasta 'Fichas por município'")
    ap.add_argument("--cruzamento", required=True, help="caminho da xlsx do cruzamento")
    ap.add_argument("--simular", action="store_true")
    args = ap.parse_args()

    pasta = Path(args.pasta)
    achados = ler_cruzamento(args.cruzamento)
    print(f"{len(achados)} municípios com achado de TZ no cruzamento.")

    n_inserido = n_pulado = n_erro = n_sem_mapa = 0
    for achado in achados:
        chave = (achado["municipio"], achado["uf"])
        nome_arquivo = MAPEAMENTO.get(chave)
        if not nome_arquivo:
            print(f"🔴 sem mapeamento de arquivo: {chave}")
            n_sem_mapa += 1
            continue
        caminho = pasta / nome_arquivo
        if not caminho.exists():
            print(f"🔴 arquivo não existe: {caminho}")
            n_erro += 1
            continue
        resultado = processar_ficha(caminho, achado, args.simular)
        marca = "✅" if resultado.startswith("inserido") else ("⏭️" if "pulado" in resultado else "🔴")
        print(f"{marca} {nome_arquivo}: {resultado}")
        if resultado.startswith("inserido"):
            n_inserido += 1
        elif "pulado" in resultado:
            n_pulado += 1
        else:
            n_erro += 1

    print(f"\nResumo: {n_inserido} inseridos · {n_pulado} já tinham bloco · {n_erro} erro/sem arquivo · {n_sem_mapa} sem mapeamento.")
    if args.simular:
        print("(--simular: nada foi escrito)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
