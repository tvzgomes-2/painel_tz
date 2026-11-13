# -*- coding: utf-8 -*-
r"""
padronizar_fichas.py — inventaria e (na 2a etapa) padroniza as fichas municipais.

Contexto: as fichas foram crescendo conforme a informacao aparecia, sem esqueleto
declarado. Hoje sao ~208 arquivos com titulos de secao divergentes, numeracao
que derivou em algumas fichas e frontmatter desigual. Este script existe para
corrigir isso sem adivinhar nada.

======================================================================
DUAS ETAPAS, DE PROPOSITO
======================================================================
  1) python padronizar_fichas.py                 # INVENTARIA. Nao escreve nada.
  2) preencher MAPA_SECOES/MAPA_FRONTMATTER com o que a etapa 1 imprimiu
  3) python padronizar_fichas.py --aplicar       # padroniza, com backup

A etapa 1 existe porque programar contra nome de secao adivinhado ja custou tres
rodadas perdidas neste cofre (ver 13a e 14a rodada do LEIA-ME dos scripts de
dados). O script se RECUSA a aplicar sem mapeamento explicito.

======================================================================
O QUE ELE NUNCA FAZ
======================================================================
- Nunca apaga conteudo. Secao que ele nao reconhece e PRESERVADA como esta,
  na posicao em que esta, e listada no relatorio como "nao classificada".
- Nunca sobrescreve valor de frontmatter que ja existe. So acrescenta chave
  ausente.
- Nunca mexe em ficha marcada como sob medida (ver DETECCAO DE FICHA SOB MEDIDA).
- Nunca escreve sem `--aplicar`, e mesmo com `--aplicar` grava backup antes.
- E idempotente: rodar duas vezes tem o mesmo efeito de rodar uma.

======================================================================
DUAS SEVERIDADES, E A DISTINCAO IMPORTA
======================================================================
GRAVE -- `## N.` com titulo trocado. O `exportar_anexo.py` le a secao pelo
NUMERO e imprime o conteudo sob o titulo que ele espera naquele numero. Duas
fichas estao assim: Vicosa/MG (a secao 5 e grupos economicos) e Fortaleza/CE (a
secao 5 e a regua analitica) -- nas duas, o Anexo I vai imprimir esse conteudo
sob o titulo "Legislacao". E bug com efeito hoje. Fichas assim entram em
QUARENTENA: reportadas, nunca reescritas, conserto a mao com o autor decidindo.

LEVE -- sub-secao `## Na.` (5a, 5b, 2a) e numero fora do esqueleto (6, 7). A
regex do exportador e `^##\s*5\.`, que casa `## 5.` e NAO casa `## 5a.`, porque
depois do 5 vem a letra e nao o ponto. Conferido rodando a regex do proprio
exportador. Logo esse conteudo e simplesmente DESCARTADO do anexo, em silencio.
Pode ser intencional -- mas nao esta decidido em lugar nenhum.

⚠️ A primeira versao deste script tratou sufixo como numero puro e por isso
juntou as duas coisas, inflando a quarentena de 2 para 6 fichas. Numero e sufixo
sao lidos separadamente desde entao.

======================================================================
ESQUELETO-ALVO PROPOSTO (a confirmar pelo autor antes da etapa 2)
======================================================================
Regra que o `exportar_anexo.py` implementa hoje, sem estar declarada em lugar
nenhum: **secao NUMERADA vai ao Anexo I, secao SEM numero fica no cofre.** O
esqueleto abaixo usa isso de proposito.

  ## 1. Briefing                      -> anexo
  ## 2. Principais dados              -> anexo
  ## 3. O caso na regua               -> anexo  (descritiva + analitica, Cap 4 e 5)
  ## 4. Quem opera                    -> anexo  (operador + grupo economico, Cap 6)
  ## 5. Legislacao                    -> anexo
  ## 6. Bibliografia                  -> anexo  (em quais fontes o caso aparece)
  ## 7. Materias de jornais           -> anexo
  ## Perfil comparado                 -> cofre  (indicadores com mediana do estrato)
  ## Antes e depois da adocao         -> cofre
  ## Deslocamento para trabalho       -> cofre
  ## Dados quantitativos              -> cofre
  ## Dados NTU                        -> cofre
  ## Literatura da RSL                -> cofre
  ## Fatores impulsionadores/limitantes -> cofre
  ## Lacunas                          -> cofre  (cada ausencia com o motivo)
  ## Ligacoes                         -> cofre

⚠️ Numerar "O caso na regua" e "Quem opera" e mudanca de conteudo do Anexo I: hoje
o anexo NAO leva a tipologia da regua analitica (presente em 50 de 52 fichas da
amostra, sem numero) nem o grupo economico do caso. Ou seja, o anexo nao carrega
justamente o que os capitulos 5 e 6 defendem. Numerar as duas corrige isso -- mas
e decisao do autor, nao do script, e exige mexer no `exportar_anexo.py` na mesma
rodada (ver § 8.4 da proposta de 10/09/2026).
"""
import os
import re
import sys
import glob
import json
import unicodedata
import collections
from datetime import datetime

# Caminhos sobreponiveis por variavel de ambiente, para rodar fora da maquina do
# autor sem editar codigo.
COFRE = os.environ.get("TZ_COFRE", r"C:\Users\HOME\OneDrive\doutorado")
FDIR = os.path.join(COFRE, "04 - Análises", "Casos municipais", "Fichas por município")
RELDIR = os.path.join(COFRE, "_meta")

APLICAR = "--aplicar" in sys.argv

# Numeros de secao e o titulo que se espera neles HOJE (o exportador depende
# disso). Serve para detectar ficha sob medida, nao para reescrever titulo.
ESPERADO_HOJE = {
    1: "briefing",
    2: "principais dados",
    3: "bibliografia",
    4: "materias",
    5: "legislacao",
}

# ---------------------------------------------------------------------
# ETAPA 2 -- preenchido em 10/09/2026 contra o inventario real das 208 fichas.
#
# ESCOPO DESTA ETAPA, DE PROPOSITO ESTREITO: alinhar as fichas divergentes ao
# padrao que 202 das 208 JA seguem. Nao muda o esqueleto, nao renomeia secao,
# nao mexe no exportador. Isso fica para a etapa 3, junto com a decisao do autor
# sobre o que passa a entrar no Anexo I.
#
# O inventario mostrou que a divergencia grave nao e caotica -- e mecanica:
#   * 3 fichas (Aparecida, Jardinopolis, Sao Joaquim da Barra) tem um DESLOCAMENTO
#     DE +3: regua descritiva/analitica/fatores foram numeradas 3/4/5, e
#     bibliografia/materias/legislacao empurradas para 6/7/8. Alguem quis levar as
#     reguas ao anexo -- intencao legitima, execucao que corrompe o anexo hoje.
#   * 1 ficha (Araraquara) numerou de 3 a 8 secoes que sao de dossie. Erro do
#     Claude em 09/09/2026, ao escrever a ficha sem conferir a convencao.
#   * 2 fichas (Fortaleza, Vicosa) sao SOB MEDIDA de verdade: o conteudo de §3/§4/§5
#     nao corresponde a nenhuma secao do padrao. Vao para quarentena.
#
# Chave = titulo normalizado (como `norm()` devolve). Valor = numero de destino,
# ou None para "tirar o numero e deixar sem numeracao".
MAPA_SECOES = {
    "briefing": 1,
    "principais dados": 2,
    "bibliografia em quais fontes o caso aparece": 3,
    "materias de jornais": 4,
    "legislacao": 5,
    # as tres abaixo voltam a ficar sem numero, como nas outras 202 fichas
    "regua descritiva trajetoria cap 4": None,
    "regua analitica cap 5": None,
    "fatores impulsionadores/limitantes": None,
    # conteudo de dossie que eu numerei por engano na ficha de Araraquara
    "entorno urbanistico censo 2022 por setor censitario": None,
    "o contraste de corredor o mesmo grupo dois regimes tarifarios": None,
    "deslocamento para trabalho censo 2022 microdados da amostra": None,
    "grupos economicos cap 6 e uma critica a variavel": None,
    "onde araraquara esta no seu estrato": None,
    "lacunas de dado a fechar": None,
}

# Fichas sob medida: nunca reescritas, mesmo com --aplicar. O conteudo numerado
# delas nao corresponde a secao nenhuma do padrao, entao renumerar seria decidir
# no lugar do autor o que vai ao anexo.
QUARENTENA_MANUAL = {
    "Ficha - Fortaleza (CE).md",
    "Ficha - Viçosa (MG).md",
}

# Chaves de frontmatter que toda ficha deve ter, com o valor a usar quando a
# chave estiver AUSENTE. `None` = precisa vir de fonte externa (base municipal),
# entao o script apenas reporta a falta em vez de inventar valor.
MAPA_FRONTMATTER = {
    # "escopo": None,   # canonico | camada-parcial | controle | fora-de-escopo
    # "cod_ibge": None,
    # "atualizado_em": "hoje",
}


def sem_acento(s):
    return unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()


def norm(s):
    """Normaliza titulo de secao para comparacao: sem acento, minusculo, sem
    emoji, sem numeracao, sem parenteses de contexto, espacos colapsados."""
    s = sem_acento(s).lower()
    s = re.sub(r"^\s*\d+[a-z]?\.\s*", "", s)          # "3. " / "5a. "
    s = re.sub(r"[^a-z0-9\s/\-—]", " ", s)             # tira emoji e pontuacao
    s = re.sub(r"\s*[\(\[].*$", "", s)                 # tira "(Cap 6) — ..."
    s = re.sub(r"\s*[—-]{1,2}\s.*$", "", s)            # tira o subtitulo depois do travessao
    return re.sub(r"\s+", " ", s).strip()


def ler(path):
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.read()


def frontmatter(txt):
    m = re.match(r"^---\n(.*?)\n---\n", txt, re.S)
    if not m:
        return {}, 0
    d = {}
    for ln in m.group(1).split("\n"):
        mm = re.match(r"^([A-Za-z_][\w\-]*):\s*(.*)$", ln)
        if mm:
            d[mm.group(1)] = mm.group(2).strip()
    return d, m.end()


def secoes(txt):
    r"""[(numero, sufixo, titulo_bruto, linha)] das secoes de nivel 2.

    O sufixo importa e a primeira versao deste script errou nisso. O
    `exportar_anexo.py` busca `^##\s*5\.` -- casa `## 5.` e NAO casa `## 5a.`,
    porque depois do 5 vem a letra e nao o ponto. Conferido rodando a regex do
    proprio exportador. Logo:
      - `## 5.`  com titulo trocado  -> conteudo sai no anexo SOB O TITULO ERRADO
      - `## 5a.` qualquer que seja    -> conteudo e DESCARTADO do anexo, em silencio
    Sao dois problemas de gravidade diferente e o relatorio tem de separa-los.
    Tratar sufixo como se fosse o numero puro, como eu fiz na primeira versao,
    inflou a quarentena de 2 para 6 fichas e misturou as duas coisas."""
    out = []
    for m in re.finditer(r"^##\s+(.+)$", txt, re.M):
        bruto = m.group(1).strip()
        n = re.match(r"^(\d+)([a-z]?)\.", bruto)
        num = int(n.group(1)) if n else None
        suf = n.group(2) if n else ""
        out.append((num, suf, bruto, txt[:m.start()].count("\n") + 1))
    return out


def diagnosticar(secs):
    """Devolve (graves, leves). Grave = conteudo vai ao anexo sob titulo errado.
    Leve = conteudo e descartado do anexo em silencio, ou numero fora do
    esqueleto. Ver a nota em `secoes()` para por que a distincao existe."""
    graves, leves = [], []
    puras = collections.Counter(n for n, suf, _, _ in secs if n is not None and not suf)
    for n, suf, bruto, _ in secs:
        if n is None:
            continue
        if suf:
            leves.append(f"§{n}{suf} «{bruto[:52]}» — descartada do anexo "
                         f"(o exportador só lê «{n}.»)")
            continue
        if puras[n] > 1:
            graves.append(f"§{n}. aparece {puras[n]}x — o exportador leva só a primeira")
        if n in ESPERADO_HOJE and ESPERADO_HOJE[n] not in norm(bruto):
            graves.append(f"§{n}. = «{bruto[:58]}» → sairá no anexo sob o título "
                          f"«{ESPERADO_HOJE[n]}»")
        if n > max(ESPERADO_HOJE):
            leves.append(f"§{n}. fora do esqueleto: «{bruto[:48]}» — não exportada")
    return sorted(set(graves)), sorted(set(leves))


def inventariar():
    arqs = [p for p in sorted(glob.glob(os.path.join(FDIR, "*.md")))
            if "MOC" not in os.path.basename(p)]
    if not arqs:
        sys.exit(f"nenhuma ficha encontrada em {FDIR} — conferir TZ_COFRE")
    print(f"{len(arqs)} fichas em {FDIR}\n")

    cont_sec = collections.Counter()          # titulo normalizado -> nº de fichas
    graf = collections.defaultdict(collections.Counter)   # normalizado -> grafias
    numerada = collections.defaultdict(collections.Counter)  # normalizado -> nº/sem
    ordem = collections.Counter()             # sequencia de secoes (assinatura)
    fm_chaves = collections.Counter()
    quarentena = []
    avisos = []
    sem_fm = []

    for p in arqs:
        t = ler(p)
        nome = os.path.basename(p)
        fm, _ = frontmatter(t)
        if not fm:
            sem_fm.append(nome)
        for k in fm:
            fm_chaves[k] += 1
        secs = secoes(t)
        for n, suf, bruto, _ in secs:
            k = norm(bruto)
            cont_sec[k] += 1
            graf[k][bruto] += 1
            numerada[k][f"§{n}{suf}" if n is not None else "sem número"] += 1
        ordem[" > ".join(norm(b) for _, _, b, _ in secs)] += 1
        g, l = diagnosticar(secs)
        if g:
            quarentena.append((nome, g))
        if l:
            avisos.append((nome, l))

    L = []
    def p_(s=""):
        print(s); L.append(s)

    p_(f"# Inventário das fichas municipais — {datetime.now():%d/%m/%Y %H:%M}")
    p_(f"\n{len(arqs)} fichas · {len(cont_sec)} títulos de seção distintos após normalização\n")

    p_("## Seções, por frequência")
    p_("")
    p_("| seção (normalizada) | em quantas fichas | numerada? | grafias distintas |")
    p_("|---|---|---|---|")
    for k, n in cont_sec.most_common():
        nums = ", ".join(f"{a} ({b})" for a, b in numerada[k].most_common())
        p_(f"| {k or '(vazio)'} | {n}/{len(arqs)} | {nums} | {len(graf[k])} |")

    p_("\n## Grafias divergentes — o que a etapa 2 tem de unificar")
    p_("")
    for k, n in cont_sec.most_common():
        if len(graf[k]) > 1:
            p_(f"- **{k}** ({n} fichas):")
            for g, c in graf[k].most_common():
                p_(f"    - `{g}` ×{c}")

    p_(f"\n## 🚨 GRAVE — conteúdo sairá no Anexo I sob o título errado: {len(quarentena)} ficha(s)")
    p_("")
    p_("São as fichas em quarentena: o script NUNCA as reescreve. Conserto a mão, "
       "com o autor decidindo o que vai ao anexo.")
    p_("")
    if quarentena:
        for nome, d in quarentena:
            p_(f"- **{nome}**")
            for x in d:
                p_(f"    - 🚨 {x}")
    else:
        p_("_nenhuma_")

    p_(f"\n## ⚠️ Leve — conteúdo descartado do anexo em silêncio: {len(avisos)} ficha(s)")
    p_("")
    p_("Sub-seções `## Na.` e números fora do esqueleto. O exportador não os lê — "
       "pode ser intencional, mas não está decidido em lugar nenhum.")
    p_("")
    if avisos:
        for nome, d in avisos:
            p_(f"- **{nome}**")
            for x in d:
                p_(f"    - {x}")
    else:
        p_("_nenhuma_")

    p_("\n## Frontmatter — chaves e cobertura")
    p_("")
    p_("| chave | fichas |")
    p_("|---|---|")
    for k, n in fm_chaves.most_common():
        p_(f"| `{k}` | {n}/{len(arqs)} |")
    if sem_fm:
        p_(f"\n⚠️ **{len(sem_fm)} fichas SEM frontmatter:** " + ", ".join(sem_fm[:15]))

    p_(f"\n## Ordem das seções — {len(ordem)} sequências distintas em {len(arqs)} fichas")
    p_("")
    p_("As 6 mais comuns (o resto é cauda; a padronização vai reduzir isto a 1):")
    p_("")
    for seq, n in ordem.most_common(6):
        p_(f"- ×{n} — {seq[:300]}")

    os.makedirs(RELDIR, exist_ok=True)
    rel = os.path.join(RELDIR, f"Inventário das fichas — {datetime.now():%Y-%m-%d}.md")
    with open(rel, "w", encoding="utf-8", newline="\n") as f:
        f.write("---\ntitle: \"Inventário das fichas municipais\"\ntags: [inventario, fichas]\n"
                f"publish: false\ncreated: {datetime.now():%Y-%m-%d}\n---\n\n")
        f.write("\n".join(L) + "\n")
    print(f"\nrelatório gravado: {rel}")
    print("\nPRÓXIMO PASSO: colar este relatório para eu preencher MAPA_SECOES e "
          "MAPA_FRONTMATTER. Sem isso, `--aplicar` se recusa a rodar.")
    return arqs


def renumerar(txt):
    """Aplica MAPA_SECOES aos cabecalhos de nivel 2. Devolve (novo_texto, mudancas).

    Toca APENAS a linha do cabecalho: o numero e trocado ou retirado, o titulo
    fica identico. Nenhuma linha de corpo e lida, movida ou reescrita -- e por
    isso que o texto do autor nao corre risco. Secao cujo titulo normalizado nao
    esta no mapa e deixada exatamente como esta."""
    mudancas = []

    def sub(m):
        bruto = m.group(1).strip()
        mm = re.match(r"^(\d+)([a-z]?)\.\s*(.*)$", bruto)
        num_atual = int(mm.group(1)) if mm else None
        sufixo = mm.group(2) if mm else ""
        titulo = mm.group(3) if mm else bruto
        if sufixo:                      # sub-secao (5a, 2a): decisao separada, nao mexer
            return m.group(0)
        k = norm(bruto)
        if k not in MAPA_SECOES:
            return m.group(0)
        alvo = MAPA_SECOES[k]
        novo = f"## {alvo}. {titulo}" if alvo is not None else f"## {titulo}"
        if novo != m.group(0):
            de = f"§{num_atual}." if num_atual is not None else "sem número"
            para = f"§{alvo}." if alvo is not None else "sem número"
            mudancas.append(f"{de} → {para}  «{titulo[:56]}»")
        return novo

    # ⚠️ O grupo 1 tem de conter APENAS o título, sem o "## ". A primeira versão
    # usava `^(##\s+.+)$`, que jogava o "##" dentro do grupo: `norm()` recebia
    # "## 3. Entorno…", a limpeza do número não casava (a string começa com "#",
    # não com dígito) e a chave saía como "3 entorno…", que não existe no mapa.
    # Resultado: nenhuma ficha era de fato corrigida e o relatório listava 50
    # alterações "sem número → sem número", todas vazias. A simulação pegou.
    novo_txt = re.sub(r"^##[ \t]+(.+?)[ \t]*$", sub, txt, flags=re.M)
    return novo_txt, mudancas


def aplicar():
    if not MAPA_SECOES:
        sys.exit("MAPA_SECOES está vazio — rodar sem --aplicar primeiro e preencher "
                 "com o que o inventário imprimir. O script não adivinha título de seção.")
    arqs = [p for p in sorted(glob.glob(os.path.join(FDIR, "*.md")))
            if "MOC" not in os.path.basename(p)]
    escrever = "--gravar" in sys.argv
    if not escrever:
        print("=== SIMULAÇÃO (nada será escrito) — acrescente --gravar para aplicar ===\n")

    bkdir = os.path.join(FDIR, "_backup-padronizacao-" + datetime.now().strftime("%Y-%m-%d_%H%M"))
    alterados, pulados, intactos = [], [], 0
    for p in arqs:
        nome = os.path.basename(p)
        t = ler(p)
        if nome in QUARENTENA_MANUAL:
            pulados.append(nome); continue
        g, _ = diagnosticar(secoes(t))
        novo, mud = renumerar(t)
        if not mud:
            intactos += 1; continue
        alterados.append((nome, mud, g))
        if escrever:
            os.makedirs(bkdir, exist_ok=True)
            with open(os.path.join(bkdir, nome), "w", encoding="utf-8", newline="\n") as f:
                f.write(t)                      # backup do original, antes de tocar
            with open(p, "w", encoding="utf-8", newline="\n") as f:
                f.write(novo)

    print(f"{len(arqs)} fichas · {intactos} já no padrão · {len(alterados)} a alterar · "
          f"{len(pulados)} em quarentena\n")
    for nome, mud, g in alterados:
        print(f"  {nome}")
        for x in mud:
            print(f"      {x}")
        if g:
            print(f"      (motivo: {g[0]})")
    if pulados:
        print(f"\nem quarentena, NÃO tocadas — conserto a mão:")
        for n in pulados:
            print(f"  {n}")
    if escrever and alterados:
        print(f"\nbackup dos originais: {bkdir}")
        print("rodar de novo sem --gravar deve reportar 0 a alterar (idempotência).")
    elif not escrever:
        print("\nnada foi escrito. Para aplicar:  python padronizar_fichas.py --aplicar --gravar")


if __name__ == "__main__":
    if APLICAR:
        aplicar()
    else:
        inventariar()
