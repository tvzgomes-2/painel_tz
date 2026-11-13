#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""corrigir_diario_camadas.py — registra no Diário a correção de 19/09/2026:
a régua em uso vai de 1 a 3 (A.1.4, 18/09/2026), e as duas entradas anteriores
desta data foram escritas com a numeração de 13/09, já substituída.

NÃO apaga as entradas erradas — marca cada uma com um aviso datado logo abaixo do
título, como o cofre já faz com números superados, e acrescenta a entrada nova.

Casa âncora exata e aborta se não bater (a ponte lê o OneDrive com defasagem).

USO  python corrigir_diario_camadas.py [--gravar]
"""
import argparse
import datetime
import os
import shutil
import sys

RAIZ = os.environ.get("TZ_VAULT") or os.getcwd()
DIA = os.path.join(RAIZ, "04 - Análises", "Diário de pesquisa",
                   "Diário de pesquisa — 2026-09 (corrente).md")

ANC1 = "### 19/09/2026 — 🚨 o critério que define a régua descritiva não estava nas fichas: o portão de acesso entra em 272/272\n"
ANC2 = "### 19/09/2026 — reclassificação por portão: 4 casos movidos com norma lida, 4 mantidos por evidência frágil, e uma camada nova\n"
ANC3 = "\n## Ligações\n"

AVISO1 = ("\n> [!warning] ⚠️ Entrada parcialmente superada em 19/09/2026 (ver a entrada "
          "\"a régua vai de 1 a 3\", no fim deste diário)\n"
          "> As **8 \"incoerências\"** nomeadas aqui foram medidas contra a numeração de "
          "13/09/2026, substituída pela regra **A.1.4** de [[Regras de classificacao das "
          "reguas]] (validada em 18/09/2026). Pela regra em vigor, **nenhuma das 8 é "
          "incoerência**: procedimento é 1b, residência é 1c e prazo ainda vigente é 1d — "
          "as três seguem na camada **1, universal**. O restante da entrada (o bloco do "
          "portão chegar a 272/272, os três estados do portão, a lacuna de cobertura e a "
          "lacuna da régua analítica) continua válido.\n")

AVISO2 = ("\n> [!danger] 🔴 Entrada superada e REVERTIDA em 19/09/2026 (ver a entrada "
          "\"a régua vai de 1 a 3\", no fim deste diário)\n"
          "> As 5 linhas movidas e a aba `4c Temporal-prazo` criada aqui foram **desfeitas**: "
          "a numeração usada (1 universal · 2 procedimento · 3 grupo social · 4a/4b temporal "
          "· 5 espacial) é a de 13/09/2026, e a regra em vigor desde **18/09/2026** é outra. "
          "A planilha voltou ao estado anterior pelo backup `…-BACKUP-20260919-2211-pre-mover.xlsx`. "
          "Os números canônicos desta entrada (camada 1 = 166) **não valem**.\n")

NOVA = """
### 19/09/2026 — 🔴 correção: a régua em uso vai de 1 a 3, e eu estava aplicando a numeração revogada

- **O que o autor apontou:** *"Vc ta pegando a classificação errada. A certa varia de 1 a 3."* Estava certo, e o erro é meu — foi a terceira vez nesta sessão que li a taxonomia pela fonte errada.
- **Onde está a regra viva:** [[Regras de classificacao das reguas]] §**A.1.4**, validada pelo autor em **18/09/2026** — um dia antes desta sessão. Ela substitui a renumeração de 13/09 e reorganiza a régua descritiva em **três camadas**:
  - **1 — Universal:** `1a` ausência de portão · `1b` procedimento (cadastro que qualquer usuário pode cumprir) · `1c` pessoa por **residência** · `1d` prazo declarado **ainda vigente**
  - **2 — Parcial:** `2a` identidade que **não** é residência (renda/CadÚnico, vínculo específico) · `2b` espacial/linha · `2c` dias da semana · `2d` eventos/eleitoral
  - **3 — Encerradas:** a política parou; descreve-se por início · fim · motivação (fim **por desenho**, quando o termo declarado foi atingido, ou **por trajetória**, quando houve revogação sem prazo prévio)
- **🚨 A consequência é o oposto do que eu tinha escrito.** A pergunta da régua continua sendo *há portão de acesso?*, mas a resposta *"sim, mas quase não pesa"* passou a ser tratada como **universal com nota**, não como rebaixamento. Procedimento, residência e prazo vigente **não tiram o caso da camada 1**. Só tiram os portões que de fato condicionam quem ou quando viaja: 2a, 2b, 2c e 2d.
- **Onde eu errei, em uma frase:** confundi o **nome das abas** da planilha com a **régua**. As abas ainda usam a numeração de 13/09 — e isso é correto e declarado, o próprio verbete registra em A.1.4 que *"esta renumeração está decidida no verbete, mas ainda não propagada à planilha nem às fichas"*. Tratei o estado pendente da planilha como se fosse o critério.
- **✅ Revertido:** as 5 linhas movidas voltaram para `1 Universal` e a aba `4c Temporal-prazo` deixou de existir — ela nasceu de uma pergunta que a regra já respondia na direção contrária. `Tipologias TZ - consolidado.xlsx` restaurada do backup `…-BACKUP-20260919-2211-pre-mover.xlsx`; a versão descartada ficou guardada como `…DESCARTADO-20260919-mover-camadas-esquema-errado.xlsx` (nada apagado). Abas de volta a: `1 Universal` **171** · 2 Procedimento 6 · 3 Grupo social 5 · 4a 26 · 4b 324 · 5 Espacial 8.
- **✅ As 8 "incoerências" reavaliadas pela regra em vigor — e nenhuma delas é incoerência:**

| caso | portão registrado | camada pela regra de 18/09 | fica na universal? |
|---|---|---|---|
| **Itapeva/SP** · **Vargem Grande Paulista/SP** | procedimento (cadastro) | **1b** | ✅ sim |
| **Aquiraz/CE** · **Eusébio/CE** | pessoa (residência **ou** vínculo laboral) | **1c** se residência · **2a** se vínculo | ⚠️ depende do dispositivo |
| **Cacoal/RO** · **Mariana/MG** · **Assis/SP** | prazo de vigência declarado, política **ativa** | **1d** | ✅ sim, com nota |
| **Palmas/TO** (2 episódios) | prazo declarado, política **encerrada** | **3** | 🔴 não — encerrada, fim **por desenho** |

- **⚠️ Aquiraz e Eusébio são a única decisão que sobra, e ela é substantiva.** A decisão de Tallinn (D.4, 18/09) fechou que **residência não tira a universalidade** — a tese segue Kębłowski (2020), não Huré, Passalacqua e Poinsot (2025). Mas a evidência dos dois casos diz *"residência **ou** vínculo laboral"*, e vínculo é 2a. **O campo `Portão` não registra qual dos dois portões está ativo**; separar exige o dispositivo. O bloco na ficha agora imprime a pergunta em vez de escolher por conta própria.
- **⚠️ Erro de dado achado no caminho:** o campo `Portão` de **Cacoal/RO, Mariana/MG e Assis/SP** diz `tempo`, mas a evidência escrita ao lado descreve **prazo de vigência** — que por A.1.4 não é portão de dias nem de eventos. O gerador passou a ler a evidência e tratar como prazo, imprimindo que **o campo da planilha precisa ser corrigido**. Não corrigi o campo: mexer no `Portão` é mexer na camada, e a regra do cofre é não alterar camada sem confirmação do autor.
- **✅ Gerador corrigido:** `_meta/scripts/enriquecer_regua_portao.py` reescrito. Passou a imprimir **duas coisas separadas e rotuladas** — a **aba** onde o caso está hoje (numeração de 13/09, estado da planilha) e a **camada pela regra em vigor** (1 a 3) —, com a conversão tirada da coluna *"era (numeração de 13/09)"* da própria tabela de A.1.4. Regerado em 272/272; idempotente conferido no arquivo.
- **Distribuição das 272 fichas pela régua em vigor, convertida da aba:** `1a` **170** · `1b` 6 · `1c` 1 · `2a` 4 · `2b` 8 · `2c` 26 · `2d` 53.
- **🔴 O que isto abre, e que é decisão do autor, não minha:** a regra de 18/09 **traz casos de volta** para a camada 1 que a numeração de 13/09 tinha tirado — os 6 de procedimento da aba `2` e São Caetano do Sul (residência, `1c`). Se a propagação for executada, o número canônico da camada 1 **sobe**, não desce. ⚠️ **Não executei:** propagar a renumeração à planilha e às fichas é reestruturação grande, o verbete a declara como pendente, e as distribuições por porte e região do [[Cap 5 - Panorama Nacional da Tarifa Zero]] teriam de ser refeitas **na mesma passada**.
- **Lição de método, e vale para além deste caso:** a fonte viva da taxonomia é o verbete em `05 - Referências/Conceitos/`, não as instruções do projeto nem o nome das abas. **Conferir a fonte viva antes de auditar contra uma regra** já estava escrito nas instruções — eu não segui.
- **Fonte:** [[Regras de classificacao das reguas]] §A.1.4 e §D.4; `_meta/scripts/enriquecer_regua_portao.py`; `Tipologias TZ - consolidado.xlsx`.
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gravar", action="store_true")
    a = ap.parse_args()
    if not os.path.exists(DIA):
        sys.exit(f"🔴 não achei {DIA}")
    t = open(DIA, encoding="utf-8").read()
    for nome, anc in (("entrada do portão", ANC1), ("entrada do mover", ANC2),
                      ("## Ligações", ANC3)):
        if t.count(anc) != 1:
            sys.exit(f"🔴 âncora não bateu ({nome}): {t.count(anc)} ocorrências. "
                     "Nada escrito.")
    if "a régua vai de 1 a 3" in t:
        print("já aplicado (entrada de correção presente). Nada a fazer.")
        return
    novo = t.replace(ANC1, ANC1 + AVISO1).replace(ANC2, ANC2 + AVISO2)
    novo = novo.replace(ANC3, NOVA + ANC3)
    print(f"{len(t)} → {len(novo)} caracteres (+{len(novo)-len(t)})")
    if not a.gravar:
        print("\nnada foi escrito. Para aplicar: --gravar")
        return
    bk = DIA + ".BACKUP-" + datetime.datetime.now().strftime("%Y%m%d-%H%M") \
        + "-pre-correcao-camadas-1a3.md"
    shutil.copy2(DIA, bk)
    open(DIA, "w", encoding="utf-8", newline="\n").write(novo)
    print(f"✅ gravado · backup {os.path.basename(bk)}")


if __name__ == "__main__":
    main()
