#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
montar_ficha_norma_sapl.py

Monta o ESQUELETO de uma ficha "Norma padronizada" (padrão da pasta
`04 - Análises/Pesquisa legal/Normas padronizadas/`) a partir da saída do
SAPL (JSON + PDF/DOCX) produzida por `buscar_texto_normas_sapl.py` ou
`buscar_alternativos_sem_indicio.py`.

O QUE ESTE SCRIPT FAZ (confiável, mecânico):
  - Lê o .json de cada norma (id, numero, ano, data, ementa, texto_integral)
    — campos estruturados da API do SAPL, mais confiáveis que regex sobre
    PDF de leismunicipais/leis.org.
  - Extrai o texto do PDF (`pdftotext -layout`) ou do .docx (`python-docx`).
  - Tenta separar os artigos por regex "Art\\.? Nº" (heurística simples).
  - Preenche a tabela de campos, a ementa (da API) e a seção de artigos.

O QUE ESTE SCRIPT NÃO FAZ — e não deve fazer (postura questionadora do cofre):
  - NÃO decide o campo "vínculo_tz" (direto/parcial/indeterminado/não).
    A varredura por palavra-chave que ACHOU a norma não é prova de que ela
    institui gratuidade — o caso de Piumhi-MG (Lei 2.709/2023, achada por
    "tarifa" + "transporte público" mas que na leitura integral trata só
    de modalidade de prestação de serviço, sem nenhuma cláusula de
    gratuidade) é o exemplo que motivou essa regra. O script grava
    "vinculo_tz: REVISAR" e cabe ao autor decidir após ler o texto.
  - NÃO decide "confianca_extracao" além de um mínimo mecânico (se há
    texto extraído ou não). A leitura de qualidade (ex. texto truncado,
    artigos deslocados, assinatura ilegível) é do autor.
  - NÃO sobrescreve fichas existentes. Se o arquivo de saída já existe,
    grava um `.novo.md` ao lado e avisa — para o autor decidir se é
    atualização (ver [[Norma — Luziânia-GO — Lei Ordinária 4595-2023]]
    como exemplo de atualização feita manualmente em 11/09/2026) ou norma
    distinta (ver [[Norma — Aquiraz-CE — Lei Ordinária 1279-2018]]).

USO:
    python montar_ficha_norma_sapl.py --entrada saida_normas_sapl --saida rascunhos_normas

  --entrada   pasta produzida por buscar_texto_normas_sapl.py (uma
              subpasta "<Município>-<UF>" por município, cada uma com
              um .json e um .pdf/.docx por norma achada)
  --saida     pasta onde os rascunhos .md serão gravados (não é a pasta
              final do cofre — o autor revisa e move manualmente)

Autor: Thiago Von Zeidler Gomes
Orientadora: Prof.ª Silvana Zioni
"""
import argparse
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

MARCADOR_ARTIGO = re.compile(
    r"Art\.?\s*(\d{1,3}(?:[ºo°]|\.?)?)\s*[-–—.]?\s*",
    re.IGNORECASE,
)


def slug_uf_municipio(pasta: Path):
    nome = pasta.name  # "Município-UF"
    if "-" not in nome:
        return nome, "??"
    municipio, uf = nome.rsplit("-", 1)
    return municipio, uf


def extrair_texto(caminho: Path) -> str:
    sufixo = caminho.suffix.lower()
    if sufixo == ".pdf":
        try:
            r = subprocess.run(
                ["pdftotext", "-layout", str(caminho), "-"],
                capture_output=True, text=True, timeout=60,
            )
            return r.stdout or ""
        except Exception as e:
            print(f"    ⚠️ falha ao extrair PDF ({caminho.name}): {e}", file=sys.stderr)
            return ""
    if sufixo == ".docx":
        try:
            import docx
            d = docx.Document(str(caminho))
            return "\n".join(p.text for p in d.paragraphs)
        except Exception as e:
            print(f"    ⚠️ falha ao extrair DOCX ({caminho.name}): {e}", file=sys.stderr)
            return ""
    return ""


def extrair_artigos(texto: str, limite_chars=260):
    """Heurística simples: cada 'Art. N' inicia um novo item; corta em 260 c."""
    partes = MARCADOR_ARTIGO.split(texto)
    # partes alterna: [antes, num1, resto1, num2, resto2, ...]
    artigos = []
    for i in range(1, len(partes) - 1, 2):
        numero = partes[i].strip()
        corpo = partes[i + 1].strip().replace("\n", " ")
        corpo = re.sub(r"\s{2,}", " ", corpo)
        if corpo:
            artigos.append((numero, corpo[:limite_chars]))
    return artigos


def formatar_numero(numero: str) -> str:
    """1279 -> 1.279 ; 945 -> 945 (sem separador abaixo de 1000)."""
    n = numero.replace(".", "")
    if len(n) <= 3:
        return n
    return f"{n[:-3]}.{n[-3:]}"


def montar_ficha(municipio, uf, meta, texto, arquivo_fonte):
    numero_fmt = formatar_numero(str(meta.get("numero", "")))
    ano = meta.get("ano", "")
    data = meta.get("data") or ""
    ementa = (meta.get("ementa") or "").strip()
    artigos = extrair_artigos(texto) if texto else []

    linhas_artigos = "\n".join(
        f"- **Art. {n}** — {c}" for n, c in artigos
    ) or "🔴 **Nenhum artigo extraído automaticamente** — revisar se há texto no arquivo-fonte."

    confianca_mecanica = "média (ementa via API SAPL; ver revisão do autor para artigos)" if not texto else "REVISAR (texto extraído — autor deve avaliar limpeza/deslocamento)"

    ficha = f"""---
title: "{municipio} ({uf}) — Lei Ordinária nº {numero_fmt}/{ano}"
tags: [legislacao, norma, fonte-primaria, {uf}, vinculo-REVISAR, confianca-REVISAR]
publish: false
created: {__import__('datetime').date.today().isoformat()}
municipio: "{municipio}"
uf: {uf}
tipo_norma: "REVISAR (Lei Ordinária / Lei Complementar / Decreto / Projeto de Lei)"
numero: "{numero_fmt}"
ano: {ano}
data: {data}
vinculo_tz: REVISAR
confianca_extracao: REVISAR
---

# {municipio} ({uf}) — Lei Ordinária nº {numero_fmt}/{ano}

> [!warning] Rascunho gerado por script — requer revisão do autor antes de entrar no corpus
> Campos "REVISAR" precisam de leitura humana. Em especial: **vínculo com a Tarifa Zero não é decidido por palavra-chave** — ver o caso de Piumhi-MG (Lei 2.709/2023) na ficha correspondente para o motivo desta regra.

| campo | valor |
|---|---|
| **Município** | {municipio} ({uf}) |
| **Tipo de legislação** | REVISAR |
| **Número** | {numero_fmt} |
| **Ano** | {ano} |
| **Data** | {data or '⚠️ não informada pela API'} |
| **Assinatura** | ⚠️ não localizada automaticamente — revisar no texto |
| **Vínculo direto com a Tarifa Zero** | ❓ REVISAR — ler o texto antes de classificar |
| **Artigos extraídos** | {len(artigos)} |
| **Confiança da extração** | {confianca_mecanica} |

## Ementa

> {ementa or '⚠️ não disponível'}

_Ementa conforme campo estruturado da API do SAPL (`ementa`)._

## Artigos

⚠️ *Extração automática por regex "Art. Nº", truncada em 260 caracteres. Conferir no documento-fonte antes de citar.*

{linhas_artigos}

## Vínculo com a Tarifa Zero

❓ **REVISAR.** Não decidir por palavra-chave ou pela ementa isoladamente — ler o articulado. Rever se há cláusula explícita de gratuidade/isenção/passe-livre universal (→ direto), de arquitetura de custeio setorial sem gratuidade universal (→ parcial), ou se a lei trata só de modalidade de prestação de serviço/concessão sem tocar em tarifa ao usuário (→ não, mesmo que a palavra "Tarifa Zero" apareça na ementa).

## Fontes (arquivos)

- `{arquivo_fonte}`

Arquivo obtido via SAPL da Câmara de {municipio} em {__import__('datetime').date.today().isoformat()}. Mover para `03 - Dados/_data/Legislacao e contratos TZ/normas/{uf}/` (fora do git) e ajustar nome conforme convenção `UF__Município-UF - Lei nº X, de DATA (SAPL).ext`.

## Lacunas e ressalvas

🔴 **Ficha em rascunho — não inserir no índice sem revisão.**

## Ligações

- [[_índice - Normas padronizadas]] · [[Base de legislacao e contratos TZ]]

---

**Autor:** Thiago Von Zeidler Gomes
**Orientadora:** Prof.ª Silvana Zioni
"""
    return ficha


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--entrada", required=True, help="pasta de saída do buscar_texto_normas_sapl.py")
    ap.add_argument("--saida", default="rascunhos_normas", help="pasta onde gravar os rascunhos .md")
    args = ap.parse_args()

    entrada = Path(args.entrada)
    saida = Path(args.saida)
    saida.mkdir(parents=True, exist_ok=True)

    n_ok = 0
    for pasta_mun in sorted(entrada.iterdir()):
        if not pasta_mun.is_dir():
            continue
        municipio, uf = slug_uf_municipio(pasta_mun)
        for arquivo in sorted(pasta_mun.glob("*.json")):
            meta = json.loads(arquivo.read_text(encoding="utf-8"))
            primario = None
            for ext in (".pdf", ".docx"):
                candidato = arquivo.with_suffix(ext)
                if candidato.exists():
                    primario = candidato
                    break
            texto = extrair_texto(primario) if primario else ""
            ficha = montar_ficha(municipio, uf, meta, texto, primario.name if primario else "(sem arquivo — texto_integral null na API)")

            numero_fmt = formatar_numero(str(meta.get("numero", ""))).replace(".", "")
            nome_saida = f"Norma — {municipio}-{uf} — RASCUNHO {numero_fmt}-{meta.get('ano','')}.md"
            (saida / nome_saida).write_text(ficha, encoding="utf-8")
            print(f"  ✍️  {nome_saida}")
            n_ok += 1

    print(f"\n=== {n_ok} rascunho(s) gravado(s) em {saida}/ — revisar antes de mover para o cofre ===")


if __name__ == "__main__":
    main()
