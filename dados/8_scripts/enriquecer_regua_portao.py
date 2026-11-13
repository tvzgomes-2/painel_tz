#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""enriquecer_regua_portao.py — leva para a ficha o PORTÃO DE ACESSO e a camada
que ele gera pela régua descritiva.

======================================================================
🔴 CORREÇÃO DE 19/09/2026 — A NUMERAÇÃO DE CAMADAS ESTAVA ERRADA AQUI
======================================================================
A versão anterior deste script lia a camada pela numeração de **13/09/2026**
(1 universal · 2 procedimento · 3 grupo social · 4a/4b temporal · 5 espacial) —
a mesma que nomeia as abas de `Tipologias TZ - consolidado.xlsx`.

Essa numeração **foi substituida em 18/09/2026** pela regra A.1.4 de
[[Regras de classificacao das reguas]], validada pelo autor. A régua agora vai
**de 1 a 3**:

  1 — Universal  1a ausência · 1b procedimento · 1c residência · 1d prazo vigente
  2 — Parcial    2a grupo social residual · 2b espacial · 2c dias · 2d eventos
  3 — Encerradas (a política parou; descreve-se por início · fim · motivação)

➡️ A consequência é grande e é o oposto do que o script dizia antes: **portão de
procedimento, de residência e de prazo ainda vigente NÃO tiram o caso da camada
universal** — são 1b, 1c e 1d, "universal com nota". Só tiram da universal os
portões que condicionam de fato quem ou quando viaja: identidade que não é
residência (2a), espaço/linha (2b), dias da semana (2c) e eventos (2d).

======================================================================
🔴 CORREÇÃO DE 20/09/2026 (1/2) — a planilha JÁ propagou, este script não
tinha percebido
======================================================================
A seção acima ("a planilha ainda está na numeração antiga") ficou errada em
20/09/2026: `Tipologias TZ - consolidado.xlsx` foi consolidada nesse mesmo dia
de 5 sub-abas (numeração de 13/09) para **4 abas** — `1 Universal` ·
`2 Parcial` · `3 Encerradas` · `Não TZ` — cada uma com uma coluna **Subtipo**
que já traz a numeração de 18/09 **diretamente** (`1a`…`1d`, `2a`…`2d`), sem
precisar de conversão por nome de aba. `camada_por_aba()` lê essa coluna; o
antigo dicionário `ABA_CAMADA` (nomes de aba de 13/09) foi rebaixado a rede de
segurança, só usado se alguma aba antiga ainda aparecer.

Isso NÃO elimina o "NA != 0" do parágrafo seguinte: em 20/09/2026 a coluna
Subtipo de `1 Universal` só está preenchida em 30 das 166 linhas (as outras
136 são exatamente os casos cujo `Portão` ainda é "a verificar"/"não
determinável" — o Subtipo só é atribuído depois do portão confirmado). Para
essas, `camada_por_aba()` devolve candidato **None**, não "1a" por padrão.

======================================================================
🔴 CORREÇÃO DE 20/09/2026 (2/2) — evidência de portão verificada sempre vence
a aba
======================================================================
Até esta correção, a linha "Camada correspondente" do bloco vinha só da aba —
inclusive quando o campo `Portão`, lido no mesmo bloco, já dizia o contrário
com evidência. Em **Ilha Comprida/SP** e **Sorriso/MT** isso produzia o pior
caso: `Portão de acesso: ✅ ausência de portão confirmada` e mesmo assim a
"Camada correspondente" afirmava **2d**, porque a aba antiga dizia isso.
`resolve_destino_portao()` agora lê o `Portão` primeiro; só quando a evidência
decide (não para "a verificar"/"não determinável"/vazio/?pessoa/?tempo ainda
ambíguos) ela vira a "Camada correspondente" — e, se a aba discordar, o bloco
registra a divergência e explica por que o portão verificado prevalece. Sem
portão confirmado, o Subtipo da aba vira candidato explicitamente marcado como
não verificado, nunca uma afirmação.

======================================================================
O QUE O BLOCO SE RECUSA A DIZER
======================================================================
Promove-se à camada 1 quem tem ausência de portão CONFIRMADA, não quem tem
ausência de evidência. O bloco distingue `nenhum` · `a verificar` · `não
determinável` · portão identificado, e NA != 0: "a verificar" nunca é escrito
como se fosse "sem portão".

E onde o valor do campo `Portão` é só "pessoa", o bloco **não decide 1c vs 2a** —
diz que a decisão depende de o portão ser residência ou não, porque é isso que
separa universal de parcial desde 18/09.

COBERTURA DA REDE (critério proporcional de Kębłowski): o insumo — nº de linhas —
está na base-mestre, preenchido em 47 de 180 casos. O bloco traz quando existe e
diz que falta quando não existe.

IDEMPOTENTE. Simula por padrão. Backup antes de gravar.

USO  python enriquecer_regua_portao.py [--gravar]
"""
import argparse
import datetime
import os
import re
import shutil
import sys
import unicodedata

RAIZ = os.environ.get("TZ_VAULT") or os.getcwd()
FDIR = os.path.join(RAIZ, "04 - Análises", "Casos municipais", "Fichas por município")
TIP = os.path.join(RAIZ, "03 - Dados", "_data", "casos por fonte",
                   "Tipologias TZ - consolidado.xlsx")
MESTRE = os.path.join(RAIZ, "03 - Dados", "_data", "casos por fonte",
                      "Municípios TZ - consolidado.xlsx")
TITULO = "### Portão de acesso — critério da régua descritiva"

# 🔴 Correção de 20/09/2026: a planilha foi consolidada de 5 sub-abas (numeração
# de 13/09) para 4 abas (1 Universal · 2 Parcial · 3 Encerradas · Não TZ) mais
# cedo neste mesmo dia. Este dicionário antigo, mantido só como rede de segurança
# para o caso de alguma aba de 13/09 ainda aparecer num estado intermediário, NÃO
# é mais a fonte principal — ver `camada_por_aba()`, que lê a coluna "Subtipo" de
# cada uma das 4 abas novas (já na numeração de 18/09 diretamente, sem conversão).
ABA_CAMADA = {
    "1 Universal":          ("1 Universal (aba)",          "1a"),
    "2 Procedimento":       ("2 Procedimento (aba)",       "1b"),
    "3 Grupo social":       ("3 Grupo social (aba)",       "1c/2a"),
    "4a Temporal-dias":     ("4a Temporal-dias (aba)",     "2c"),
    "4b Temporal-eventos":  ("4b Temporal-eventos (aba)",  "2d"),
    "5 Espacial-periferico": ("5 Espacial-periférico (aba)", "2b"),
}

# camada de 18/09 -> (rótulo, se é universal)
CAMADA = {
    "1a": ("**1a — universal**, ausência de portão", True),
    "1b": ("**1b — universal**, portão de procedimento (cadastro que qualquer "
           "usuário pode cumprir)", True),
    "1c": ("**1c — universal**, portão de pessoa por *residência* — a decisão de "
           "18/09/2026 (Tallinn, D.4) mantém a universalidade, seguindo Kębłowski "
           "(2020)", True),
    "1d": ("**1d — universal**, prazo declarado na norma que **ainda não chegou** — "
           "só vira camada 3 quando o termo é atingido", True),
    "2a": ("**2a — parcial**, portão de identidade que **não** é residência "
           "(renda/CadÚnico ou vínculo específico)", False),
    "2b": ("**2b — parcial**, portão de espaço/linha", False),
    "2c": ("**2c — parcial**, portão de tempo recorrente (dias da semana)", False),
    "2d": ("**2d — parcial**, portão de tempo pontual (eventos; o eleitoral fica fora desde 06/10/2026, A.1.7)", False),
    "3":  ("**3 — encerrada**, a política parou (descreve-se por início · fim · "
           "motivação: fim por desenho ou por trajetória)", False),
}

# valor do campo `Portão` na planilha -> (rótulo do estado, camada de 18/09 ou None)
LEITURA = {
    "nenhum": ("✅ **ausência de portão confirmada**", "1a"),
    "a verificar": ("⚠️ **não verificado** — ausência de evidência não é evidência "
                    "de ausência", None),
    "a verificar — prazo?": ("⚠️ **não verificado** (suspeita de prazo declarado)", None),
    "não determinável": ("⚠️ **verificado, sem conclusão** — a fonte disponível não "
                         "permite decidir", None),
    "procedimento": ("🟡 **portão de procedimento**", "1b"),
    "pessoa": ("🟡 **portão de pessoa**", "?pessoa"),
    "pessoa + procedimento": ("🟡 **portão de pessoa + procedimento** — pelo "
                              "desempate de A.1.3 o cadastro é atributo, não camada",
                              "?pessoa"),
    "prazo": ("🟡 **prazo de vigência declarado na norma**", "?prazo"),
    "tempo": ("🔴 **portão de tempo**", "?tempo"),
    "espaço": ("🔴 **portão de espaço/linha**", "2b"),
}

PRAZO_NA_EV = re.compile(r"praz\w|vig[êe]ncia|enquanto durar|renova\w+ at[ée]|"
                         r"v[áa]lid\w+ (?:por|at[ée])", re.I)

NOTA_FONTE = ("_Camadas pela regra em vigor (A.1.4 de [[Regras de classificacao das "
              "reguas]], validada em 18/09/2026 — a régua vai de 1 a 3). A planilha foi "
              "consolidada em 4 abas em 20/09/2026 (`1 Universal` · `2 Parcial` · "
              "`3 Encerradas` · `Não TZ`); a coluna Subtipo de cada aba já usa a "
              "numeração de 18/09 diretamente. Evidência de portão VERIFICADA sempre "
              "tem prioridade sobre o Subtipo da aba; sem portão confirmado, o Subtipo "
              "é candidato, nunca afirmação. Fonte dos campos: `Tipologias TZ - "
              "consolidado.xlsx` (Subtipo, Portão e Portão — evidência) e `Municípios "
              "TZ - consolidado.xlsx` (Nº linhas)._")


def n(s):
    s = "".join(c for c in unicodedata.normalize("NFD", str(s or ""))
                if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s).strip().lower()


def carregar():
    import openpyxl
    portao, aba_de, subtipo_por_aba = {}, {}, {}
    wb = openpyxl.load_workbook(TIP, read_only=True, data_only=True)
    for aba in wb.sheetnames:
        if aba == "RESUMO":
            continue
        ws = wb[aba]
        rr = list(ws.iter_rows(values_only=True))
        if not rr:
            continue
        h = [str(x).strip() for x in rr[0]]
        if "Município" not in h:
            continue
        im, iu = h.index("Município"), h.index("UF")
        ip = h.index("Portão") if "Portão" in h else None
        ie = h.index("Portão — evidência") if "Portão — evidência" in h else None
        # "Subtipo" (1 Universal, 2 Parcial, Não TZ) ou "Subtipo (antes de
        # encerrar)" (3 Encerradas) — já na numeração de 18/09 diretamente.
        isub = next((i for i, c in enumerate(h) if c.startswith("Subtipo")), None)
        for r in rr[1:]:
            if not r or im >= len(r) or not r[im]:
                continue
            k = (n(r[im]), str(r[iu] or "").strip().upper())
            aba_de.setdefault(k, []).append(aba)
            if isub is not None and isub < len(r) and r[isub]:
                subtipo_por_aba.setdefault((k, aba), set()).add(str(r[isub]).strip())
            if ip is not None and ip < len(r) and r[ip]:
                portao[k] = (str(r[ip]).strip(),
                             str(r[ie]).strip() if ie is not None and ie < len(r)
                             and r[ie] else "")
    linhas, situacao = {}, {}
    ws = openpyxl.load_workbook(MESTRE, read_only=True, data_only=True)["consolidado"]
    rr = list(ws.iter_rows(values_only=True))
    h = [str(x).strip() for x in rr[0]]
    ci = {k: i for i, k in enumerate(h)}
    for r in rr[1:]:
        if r[ci['Município']]:
            k = (n(r[ci['Município']]), str(r[ci['UF']] or "").strip().upper())
            v = r[ci['Nº linhas']]
            if v not in (None, "", "—") and "não mencionado" not in n(v):
                linhas[k] = str(v).strip()
            situacao[k] = str(r[ci['Situação']] or "").strip()
    return portao, aba_de, subtipo_por_aba, linhas, situacao


def camada_por_aba(aba, k, subtipo_por_aba):
    """Converte a aba pós-consolidação de 20/09 (1 Universal · 2 Parcial ·
    3 Encerradas · Não TZ) na camada candidata, lendo a coluna Subtipo de cada
    aba — que já traz a numeração de 18/09 diretamente, sem conversão por nome
    de aba. Sem Subtipo preenchido (comum em '1 Universal': 136 de 166 linhas em
    20/09/2026, porque o Subtipo só é atribuído depois do portão confirmado),
    devolve camada None — não adivinha 1a/2a por membership de aba sozinha, é
    exatamente o "NA != 0" que este script promete no cabeçalho.

    Achado de 20/09/2026: 14 municípios têm mais de um Subtipo distinto dentro
    da MESMA aba (`2 Parcial`, sempre) — ex.: Curitiba tem linhas 2a (programa
    para desempregados) e 2d (evento/eleitoral). Isso é plausível como programas
    de TZ distintos coexistindo, não necessariamente erro de planilha. Aplica-se
    o mesmo desempate de A.1.3 já usado entre abas: o mais restritivo prevalece,
    e a multiplicidade é sinalizada no rótulo em vez de escolhida em silêncio."""
    subs = subtipo_por_aba.get((k, aba)) or set()
    nota_multi = (f" ⚠️ **{len(subs)} subtipos distintos na mesma aba** "
                  f"({'/'.join(sorted(subs))}) — programas de TZ possivelmente "
                  f"distintos; mais restritivo prevalece por A.1.3."
                  if len(subs) > 1 else "")
    sub = sorted(subs)[-1] if subs else None
    if aba == "1 Universal":
        if sub in ("1a", "1b", "1c", "1d"):
            return f"1 Universal (aba, subtipo {sub}{nota_multi})", sub
        return "1 Universal (aba, subtipo ainda não preenchido)", None
    if aba == "2 Parcial":
        if sub in ("2a", "2b", "2c", "2d"):
            return f"2 Parcial (aba, subtipo {sub}{nota_multi})", sub
        return "2 Parcial (aba, subtipo ainda não preenchido)", None
    if aba == "3 Encerradas":
        return "3 Encerradas (aba)", "3"
    if aba == "Não TZ":
        return "Não TZ (aba) — fora do escopo canônico", None
    if aba == "Regulamentada não implantada":
        return "Regulamentada não implantada (aba, regra A.1.6) — fora da contagem", None
    if aba == "Eleitoral — piso e trajetória":  # A.1.7 item 5 (decisão do autor, 06/10/2026)
        return "Eleitoral — piso e trajetória (aba, regra A.1.7, item 5) — gratuidade em dia de eleição: piso desde 2024, trajetória antes; fora das camadas e da contagem", None
    # rede de segurança: abas antigas de 13/09, se alguma ainda existir
    return ABA_CAMADA.get(aba, (aba, None))


def resolve_destino_portao(k, portao, situacao):
    """Lê o campo `Portão` e resolve, quando possível, a camada de 18/09 que ele
    aponta sozinho — sem olhar a aba. Devolve `destino_confirmado` só quando a
    evidência realmente decide (não para os casos ainda ambíguos ?pessoa/?tempo,
    nem para 'a verificar'/'não determinável'/campo vazio, que ficam None).

    🔴 Correção de 20/09/2026 (3): o portão lido descreve a política ENQUANTO
    ATIVA — não decide sozinho a camada quando a Situação já é Encerrada. Achado
    em Monte Mor/SP: Portão = procedimento (evidência: cadastro prévio exigido,
    lido do PDF oficial), mas a Situação da base já registra 'Encerrada'
    (revogada por Lei 3.379/2025). Antes desta correção o bloco afirmava
    "1b — universal" para um caso que já não existe mais — só o ramo ?prazo
    checava `situacao`; os ramos 1a/1b/2b não checavam. Por A.1.4: "política sem
    prazo depois revogada foi universal [ou parcial] e encerrada, porque o fim é
    trajetória e não desenho" — a camada 3 vale independente do portão que a
    política tinha enquanto ativa."""
    p = portao.get(k)
    if not p:
        return None
    val, ev = p
    rot, destino = LEITURA.get(n(val), (f"**{val}**", None))
    if destino == "?tempo" and PRAZO_NA_EV.search(ev or ""):
        destino = "?prazo"
    if destino == "?prazo":
        enc = "encerrada" in n(situacao.get(k, ""))
        return "3" if enc else "1d"
    if destino in ("1a", "1b", "2b"):
        if "encerrada" in n(situacao.get(k, "")):
            return "3"
        return destino
    return None  # nenhum (0 evidência), ?pessoa, ?tempo, ou vazio: não decide sozinho


def bloco(k, portao, aba_de, subtipo_por_aba, linhas, situacao):
    L = [TITULO]
    abas = aba_de.get(k, [])
    destino_confirmado = resolve_destino_portao(k, portao, situacao)

    # --- 1. onde o caso está na planilha hoje, e que camada isso dá pela regra nova
    cam_aba = None
    if abas:
        pares = [camada_por_aba(a, k, subtipo_por_aba) for a in dict.fromkeys(abas)]
        L.append("- **Onde o caso está na planilha:** "
                 + " · ".join(p[0] for p in pares)
                 + (" ⚠️ **Consta em mais de uma aba** — pelo desempate de A.1.3 o "
                    "portão mais restritivo prevalece." if len([a for a in dict.fromkeys(abas) if a != "Eleitoral — piso e trajetória"]) > 1 else ""))
        cams = [p[1] for p in pares if p[1]]
        if cams:
            cam_aba = sorted(cams)[-1]  # o mais restritivo, só por membership de aba
    else:
        L.append("- **Onde o caso está na planilha:** ⚠️ município não consta de "
                 "nenhuma aba de `Tipologias TZ - consolidado.xlsx`.")

    # --- 1b. a camada que vale, decidindo entre o portão VERIFICADO e a aba
    # 🔴 Correção de 20/09/2026: antes, esta linha vinha só da aba — inclusive
    # quando o portão já dizia, com evidência, o contrário (ex.: Ilha Comprida e
    # Sorriso têm "ausência de portão confirmada" — 1a — mas a aba `4b Temporal-
    # eventos` (numeração velha, pré-consolidação) fazia o bloco escrever "2d".
    # Regra: evidência de portão VERIFICADA sempre vence a aba. Sem verificação,
    # a aba vira só "candidato", nunca afirmação — é o "NA != 0" que o próprio
    # cabeçalho deste script promete.
    if destino_confirmado:
        rot, _ = CAMADA[destino_confirmado]
        L.append(f"- **Camada correspondente na régua em vigor (1 a 3):** {rot}.")
        if cam_aba and cam_aba != destino_confirmado:
            rot_aba, _ = CAMADA[cam_aba]
            L.append(f"  - 🚨 **Divergência com a aba, resolvida a favor do portão "
                     f"verificado:** o Subtipo da planilha indicaria {rot_aba}, mas o "
                     f"portão lido abaixo — com evidência registrada — confirma "
                     f"{rot.split(',')[0]}. Evidência de portão VERIFICADA tem "
                     f"prioridade sobre o Subtipo da aba, que pode estar desatualizado "
                     f"ou ter sido preenchido antes da checagem do portão.")
    elif cam_aba:
        rot_aba, _ = CAMADA[cam_aba]
        L.append(f"- **Camada correspondente na régua em vigor (1 a 3):** ⚠️ "
                 f"**candidato pela aba, portão não verificado:** {rot_aba} — "
                 f"não é afirmação; ver \"Portão de acesso\" abaixo. Ausência de "
                 f"evidência de portão não é evidência de ausência.")
    else:
        L.append("- **Camada correspondente na régua em vigor:** ⚠️ a aba de "
                 "origem não tem conversão mecânica — decidir caso a caso.")

    # --- 2. o portão lido, e a camada que ele próprio aponta
    p = portao.get(k)
    if p:
        val, ev = p
        rot, destino = LEITURA.get(n(val), (f"**{val}**", None))
        # O campo `Portão` de alguns casos diz "tempo" onde a própria evidência
        # descreve PRAZO DE VIGÊNCIA — que por A.1.4 não é 2c nem 2d, é 1d
        # enquanto vigente. Lê-se a evidência que o autor escreveu; não se
        # reescreve a planilha por conta própria.
        reclassifica_prazo = destino == "?tempo" and PRAZO_NA_EV.search(ev or "")
        if reclassifica_prazo:
            destino = "?prazo"
        L.append(f"- **Portão de acesso:** {rot}.")
        if reclassifica_prazo:
            L.append("  - ⚠️ **O campo `Portão` da planilha diz `tempo`, mas a "
                     "evidência registrada descreve um prazo de vigência** — que "
                     "por A.1.4 não é portão de dias nem de eventos. Tratado aqui "
                     "como prazo; **o campo da planilha precisa ser corrigido pelo "
                     "autor**.")
        if destino == "?pessoa":
            L.append("  - ⚠️ **1c ou 2a, a decidir:** desde 18/09/2026 o portão de "
                     "pessoa só mantém a universalidade quando é **residência** "
                     "(camada 1c). Renda/CadÚnico ou vínculo com grupo específico "
                     "são camada **2a — parcial**. O campo `Portão` não registra "
                     "qual dos dois é; a decisão exige o dispositivo.")
        elif destino == "?prazo":
            enc = "encerrada" in n(situacao.get(k, ""))
            L.append("  - " + ("🔴 **camada 3 — encerrada:** a política parou, e o "
                               "fim foi **por desenho** (o termo declarado na norma "
                               "foi atingido)." if enc else
                               "✅ **camada 1d — universal com nota:** o prazo está "
                               "declarado mas a política segue ativa. Só vira camada "
                               "3 quando o termo for de fato atingido (A.1.4). "
                               "⚠️ Se a data declarada já passou e a política segue "
                               "ativa, há contradição a resolver — ou houve renovação "
                               "não registrada, ou o termo não vale."))
        elif destino == "?tempo":
            L.append("  - ⚠️ **2c ou 2d, a decidir:** tempo recorrente (dias da "
                     "semana) é camada 2c; tempo pontual (evento/eleitoral) é 2d. "
                     "Prazo de vigência **não** é nenhum dos dois — é 1d enquanto "
                     "vigente, 3 quando atingido.")
        elif destino and destino in CAMADA:
            rotc, _ = CAMADA[destino]
            L.append(f"  - Pelo portão lido, a camada é {rotc}.")
        if ev:
            L.append(f"- **Evidência do portão:** {ev}")
        else:
            L.append("- **Evidência do portão:** ⚠️ campo vazio na planilha — a "
                     "classificação ainda não tem lastro documental registrado.")
        # divergência real: o portão aponta camada 2 e o caso está na aba universal
        if destino in ("2b",) or (destino == "?tempo"):
            if cam_aba == "1a":
                L.append("- 🚨 **Divergência a resolver:** o portão lido aponta "
                         "camada **2 (parcial)**, mas o caso está na aba "
                         "`1 Universal`. Diferente de procedimento, residência e "
                         "prazo vigente, este portão **tira** o caso da universal.")
    else:
        L.append("- **Portão de acesso:** ⚠️ **não registrado** na planilha da régua "
                 "— não confundir com ausência de portão.")

    # --- 3. cobertura
    nl = linhas.get(k)
    if nl:
        L.append(f"- **Cobertura da rede (critério proporcional de Kębłowski):** o "
                 f"sistema tem **{nl}** linha(s) registradas; comparar com as linhas "
                 "alcançadas pela gratuidade para aferir a proporção — é o limiar do "
                 "portão de espaço (2b).")
    else:
        L.append("- **Cobertura da rede (critério proporcional de Kębłowski):** ⚠️ "
                 "**número de linhas do sistema não registrado** na base-mestre — sem "
                 "ele a proporção da rede não pode ser aferida nem refutada.")
    L.append(NOTA_FONTE)
    return "\n".join(L) + "\n"


def aplicar(txt, novo):
    # 25/09/2026: fichas antigas têm o bloco em nível ####; reconhecer 3 ou 4 e manter o nível
    # existente (antes, o bloco #### não era reconhecido e o script inseria um segundo).
    # o bloco termina na linha da nota de fonte ("_Camadas pela regra..."); sem isso a busca
    # avançava até o próximo título e engolia blocos gerados por outros scripts (<!-- prosa:... -->).
    m = (re.search(r"^(#{3,4}) Portão de acesso — critério.*?^_Camadas pela regra[^\n]*\n?", txt, re.S | re.M)
         or re.search(r"^(#{3,4}) Portão de acesso.*?(?=\n^#{2,4} |\n<!-- |\Z)", txt, re.S | re.M))
    if m:
        if m.group(1) == "####" and novo.startswith("### "):
            novo = "#" + novo
        if m.group(0).strip() == novo.strip():
            return txt, "igual"
        cauda = "\n" if m.group(0).endswith("\n") else ""
        return txt[:m.start()] + novo.rstrip("\n") + "\n" + cauda + txt[m.end():], "substituído"
    anc = re.search(r"^##+\s*R[ée]gua descritiva[^\n]*\n", txt, re.M)
    if anc:
        prox = re.search(r"^#{2,3} ", txt[anc.end():], re.M)
        corte = anc.end() + (prox.start() if prox else len(txt) - anc.end())
        return txt[:corte].rstrip() + "\n\n" + novo + "\n" + txt[corte:], "inserido"
    anc = re.search(r"^### Perfil socioeconômico.*?(?=\n^#{2,3} |\Z)", txt, re.S | re.M)
    if anc:
        return txt[:anc.end()] + "\n\n" + novo + txt[anc.end():], "inserido"
    return txt, "🔴 sem âncora"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gravar", action="store_true")
    a = ap.parse_args()
    if not os.path.isdir(FDIR):
        sys.exit(f"🔴 não achei as fichas em {FDIR}")
    portao, aba_de, subtipo_por_aba, linhas, situacao = carregar()
    print(f"planilha: {len(portao)} municípios com portão · {len(aba_de)} em alguma "
          f"aba · {len(linhas)} com nº de linhas")
    fichas = sorted(x for x in os.listdir(FDIR)
                    if x.startswith("Ficha") and x.endswith(".md") and "MOC" not in x)
    plano, est, porcam = [], {}, {}
    for nome in fichas:
        p = os.path.join(FDIR, nome)
        t = open(p, encoding="utf-8").read()
        mm = re.search(r"^municipio:\s*(.+)$", t, re.M)
        uu = re.search(r"^uf:\s*(.+)$", t, re.M)
        if not (mm and uu):
            continue
        k = (n(mm.group(1)), uu.group(1).strip().upper())
        v = portao.get(k, (None, None))[0]
        est[v or "(sem registro)"] = est.get(v or "(sem registro)", 0) + 1
        for aba in dict.fromkeys(aba_de.get(k, [])):
            _, c = camada_por_aba(aba, k, subtipo_por_aba)
            porcam[c or "(sem conversão)"] = porcam.get(c or "(sem conversão)", 0) + 1
        novo_t, ac = aplicar(t, bloco(k, portao, aba_de, subtipo_por_aba, linhas, situacao))
        if novo_t != t:
            plano.append((nome, p, novo_t, ac))
    ins = sum(1 for x in plano if x[3] == "inserido")
    print(f"\n{len(fichas)} fichas · {len(plano)} a alterar (inserido {ins}, "
          f"substituído {len(plano)-ins})")
    print("\nestado do portão nas fichas:")
    for k2, v2 in sorted(est.items(), key=lambda x: -x[1]):
        print(f"   {v2:>4}  {k2}")
    print("\ncamada pela régua em vigor (1 a 3), convertida da aba:")
    for k2, v2 in sorted(porcam.items()):
        print(f"   {v2:>4}  {k2}")
    if not a.gravar:
        print("\nnada foi escrito. Para aplicar: --gravar")
        if plano:
            print("\n--- prévia:\n" + re.search(
                r"^#{3,4} Portão de acesso.*?(?=\n^#{2,4} |\Z)",  # 28/09/2026: aceita bloco ####
                plano[0][2], re.S | re.M).group(0))
        return
    bk = os.path.join(RAIZ, "_meta", "_backups",
                      "portao-" + datetime.datetime.now().strftime("%Y-%m-%d_%H%M"))
    os.makedirs(bk, exist_ok=True)
    for nome, p, novo_t, _ in plano:
        shutil.copy2(p, os.path.join(bk, nome))
        open(p, "w", encoding="utf-8", newline="\n").write(novo_t)
    print(f"\n✅ {len(plano)} fichas · backup em {os.path.basename(bk)}")


if __name__ == "__main__":
    main()
