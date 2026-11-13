#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""enriquecer_contexto_mobilidade.py — gera, em cada ficha municipal, o bloco
"### Contexto de mobilidade (Base Municipal v3)" a partir de
`03 - Dados/_data/Base Municipal v3/base_municipal_v3.csv`.

======================================================================
POR QUE ESTE SCRIPT EXISTE
======================================================================
O bloco existia em 204 das 211 fichas e NAO TINHA GERADOR: foi escrito caso a
caso. Por isso as 6 fichas abertas em 03-09/09/2026 (Andrelandia, Duque de
Caxias, Embu das Artes, Mage, Parauapebas, Araraquara) ficaram sem ele, e por
isso toda ficha nova nasce sem ele. Os blocos COM gerador
(`enriquecer_fichas_municipais.py`, `enriquecer_fichas_rsl.py`) estao em 207 e
204 de 211; os SEM gerador sao exatamente onde estao as lacunas. Escrever o
gerador fecha a lacuna de agora e as futuras — e torna o bloco replicavel, que
e o padrao de reprodutibilidade adotado no cofre.

======================================================================
🔴 O OSM SAI, E ISSO E CORRECAO DE FATO, NAO PREFERENCIA
======================================================================
A linha "Infraestrutura (OSM)" reporta contagem de pontos, terminais e rotas
mapeados no OpenStreetMap como se fosse medida da infraestrutura existente.
Medido sobre as 210 fichas com codigo IBGE:

    134 de 210 declaram ZERO rotas de onibus
     63 de 210 declaram ZERO pontos de onibus
    126 de 210 declaram ZERO rotas TENDO frota de onibus registrada no
        SENATRAN — ex.: Abaete/MG com 206 onibus e "0 rotas"

Zero no OSM significa NAO MAPEADO, nao inexistente. A ficha de Ibate afirmava
"2 pontos de onibus; 0 terminais; 0,0 rotas" enquanto o municipio tem Tarifa
Zero ativa e 695 onibus registrados. E a mesma disciplina do NA != 0 que vale no
resto da pesquisa: ausencia de medida nao e medida de ausencia. Publicado no
Anexo I, isso vira afirmacao factual errada sobre 126 municipios.

ENTRA NO LUGAR (decisao do autor, 16/09/2026):
  * frota de onibus SENATRAN — registro administrativo, sem zeros espurios;
  * trajetoria institucional MUNIC 2012 -> 2017 -> 2020 — serie que esta na
    base e nao era usada em ficha nenhuma. Ela mostra ENTRADA e SAIDA do
    servico de onibus intramunicipal e mudanca da forma de contratacao, que e
    contexto direto do Cap 6.

======================================================================
⚠️ A VOZ DO AUTOR E PRESERVADA LINHA A LINHA
======================================================================
40 das 204 fichas tem INTERPRETACAO escrita a mao dentro do bloco — "a maior
frota absoluta do lote", "o menor volume do lote", "a maior proporcao vista em
qualquer ficha do cofre ate agora". Regenerar por cima apagaria isso.

Regra: uma linha que carrega comentario interpretativo e MANTIDA VERBATIM, no
lugar dela. So sao regeradas as linhas puramente factuais, e so sao acrescentadas
as que faltam. Se a linha do OSM carregava comentario, ela nao e descartada em
silencio: vira uma linha `⚠️ a revisar` com o texto original, para o autor
decidir. O script nunca apaga prosa do autor.

USO
  python enriquecer_contexto_mobilidade.py              # simula, nao escreve
  python enriquecer_contexto_mobilidade.py --gravar     # grava, com backup
  python enriquecer_contexto_mobilidade.py --so-faltantes   # so as 6 sem bloco
"""
import argparse
import csv
import datetime
import os
import re
import shutil
import sys
import unicodedata

RAIZ = os.environ.get("TZ_VAULT") or os.getcwd()
FDIR = os.path.join(RAIZ, "04 - Análises", "Casos municipais", "Fichas por município")
BASE = os.path.join(RAIZ, "03 - Dados", "_data", "Base Municipal v3", "base_municipal_v3.csv")

TITULO = "### Contexto de mobilidade (Base Municipal v3)"

# Marcadores de interpretacao do autor. Conservador de proposito: na duvida
# PRESERVA a linha em vez de regerar. Um falso positivo custa uma linha nao
# atualizada; um falso negativo apaga texto do autor.
INTERPRETA = re.compile(
    r"(maior|menor|lote|coerente|chama aten|destaca|acima d|abaixo d|"
    r"[úu]nico|at[íi]pic|contraste|apesar|chama a aten|surpreend|"
    r"em linha com|proporcionalmente|incomum|expressiv)", re.I)


def n(v):
    """Texto -> float, ou None. Vazio, '-' e lixo viram None, nunca 0."""
    if v is None:
        return None
    s = str(v).strip().replace(",", ".")
    if s in ("", "-", "—", "nan", "None"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def br(x, casas=0):
    """1234.5 -> '1.234' (separador de milhar brasileiro)."""
    if x is None:
        return "—"
    s = f"{x:,.{casas}f}"
    return s.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


def pct(x, casas=1):
    return "—" if x is None else f"{x:.{casas}f}".replace(".", ",") + "%"


# ---------------------------------------------------------------- as linhas
def linha_gestao(r):
    org = (r.get("munic_orgao_gestor_2020") or "").strip()
    if not org:
        return ("gestao", "- **Gestão do transporte (MUNIC 2020):** ⚠️ município não "
                          "respondeu ao bloco de transporte da MUNIC 2020.")
    tem = lambda c: n(r.get(c)) == 1
    partes = [org[0].lower() + org[1:]]
    inst = [nome for nome, col in
            (("plano de transporte", "munic_plano_transp_2020"),
             ("conselho", "munic_conselho_2020"),
             ("fundo", "munic_fundo_2020")) if tem(col)]
    if inst:
        s = "possui " + ", ".join(inst[:-1]) + (" e " if len(inst) > 1 else "") + inst[-1]
        if tem("munic_fundo_ativo_2020"):
            s += " (fundo **ativo**)"
        partes.append(s)
    else:
        partes.append("sem plano, conselho ou fundo")
    if n(r.get("munic_onibus_intramun_2020")) == 1:
        formas = [nome for nome, col in
                  (("concessão", "munic_concessao_2020"),
                   ("permissão", "munic_permissao_2020"),
                   ("autorização", "munic_autorizacao_2020"),
                   ("prestação direta", "munic_prestacao_direta_2020"),
                   ("não regulamentado", "munic_nao_regulamentado_2020")) if tem(col)]
        partes.append("forma de contratação: " + (" + ".join(formas) if formas
                                                  else "⚠️ não informada"))
    else:
        partes.append("**sem serviço de ônibus intramunicipal declarado** na MUNIC 2020")
    return ("gestao", "- **Gestão do transporte (MUNIC 2020):** " + "; ".join(partes) + ".")


def linha_trajetoria(r):
    """Serie MUNIC 2012 -> 2017 -> 2020. Substitui a linha do OSM.

    Le ENTRADA e SAIDA do servico de onibus intramunicipal e mudanca da forma
    de contratacao. E dado censitario administrativo, ao contrario da contagem
    de OSM, que media cobertura de mapeamento voluntario."""
    s = [n(r.get(f"munic_onibus_intramun_{a}")) for a in (2012, 2017, 2020)]
    if all(v is None for v in s):
        return None
    marca = {1.0: "sim", 0.0: "não", None: "—"}
    traj = " → ".join(marca.get(v, "—") for v in s)
    txt = f"- **Trajetória institucional (MUNIC 2012 → 2017 → 2020):** ônibus intramunicipal {traj}"
    if s[0] == 1 and s[2] == 0:
        txt += " — 🔴 **serviço declarado em 2012 e não declarado em 2020**"
    elif s[0] == 0 and s[2] == 1:
        txt += " — serviço passa a ser declarado no período"
    f17 = [nome for nome, c in (("concessão", "munic_concessao_2017"),
                                ("permissão", "munic_permissao_2017"),
                                ("autorização", "munic_autorizacao_2017"),
                                ("prestação direta", "munic_prestacao_direta_2017"),
                                ("não regulamentado", "munic_nao_regulamentado_2017"))
           if n(r.get(c)) == 1]
    f20 = [nome for nome, c in (("concessão", "munic_concessao_2020"),
                                ("permissão", "munic_permissao_2020"),
                                ("autorização", "munic_autorizacao_2020"),
                                ("prestação direta", "munic_prestacao_direta_2020"),
                                ("não regulamentado", "munic_nao_regulamentado_2020"))
           if n(r.get(c)) == 1]
    if f17 and f20:
        if set(f17) != set(f20):
            txt += (f"; forma de contratação **muda** de {' + '.join(f17)} (2017) "
                    f"para {' + '.join(f20)} (2020)")
        else:
            txt += f"; forma de contratação estável ({' + '.join(f20)}) em 2017 e 2020"
    return ("trajetoria", txt + ".")


def linha_frota(r):
    a, b = n(r.get("frota_onibus_2025")), n(r.get("frota_onibus_2013"))
    if a is None:
        return None
    t = f"- **Frota de ônibus (DENATRAN/SENATRAN):** {br(a)} veículos em 2025"
    if b:
        t += f" ({br(b)} em 2013, {'+' if a >= b else ''}{br((a-b)/b*100)}%)"
    return ("frota", t + ".")


def linha_modal(r):
    d = {k: n(r.get(f"censo22_modal_{k}_pct")) for k in
         ("onibus", "automovel", "a_pe", "motocicleta")}
    if all(v is None for v in d.values()):
        return None
    # ⚠️ "agregado" no rótulo NAO e detalhe: a base traz duas medidas do mesmo
    # %, a agregada (censo22_modal_*) e a tabulada dos microdados
    # (md22_modo_onibus_pct), e elas divergem em mediana 0,26 pp e ate 3,0 pp
    # (Sorocaba: 24,9% vs 27,9%). Sao a mesma grandeza medida por dois caminhos,
    # nao um erro — mas sem o rotulo a ficha se contradiz sozinha quando o §2
    # cita a dos microdados e este bloco cita a agregada.
    return ("modal", "- **Modal split (Censo 2022, agregado):** "
            f"ônibus {pct(d['onibus'])}; automóvel {pct(d['automovel'])}; "
            f"a pé {pct(d['a_pe'])}; motocicleta {pct(d['motocicleta'])}.")


def linha_despesa(r):
    p, v, c = (n(r.get("pct_transporte_desp_2022")), n(r.get("desp_transporte_2022")),
               n(r.get("transporte_cagr_2019_2022")))
    if p is None and v is None:
        return None
    t = f"- **Despesa com transporte:** {pct(p, 2)} do orçamento 2022"
    if v is not None:
        t += f" (R$ {br(v/1e6, 1)} mi)" if v >= 1e6 else f" (R$ {br(v)})"
    if c is not None:
        t += f"; variação 2019-2022: {'+' if c >= 0 else ''}{pct(c)}"
    return ("despesa", t + ".")


def linha_seguranca(r):
    o, f = n(r.get("obitos_ocup_onibus_2019")), n(r.get("feridos_ocup_onibus_2019"))
    if o is None and f is None:
        return None
    return ("seguranca", f"- **Segurança viária (2019):** {br(o)} óbito(s) e {br(f)} "
                         "ferido(s) registrados entre ocupantes de ônibus.")


def linha_emprego(r):
    a, b = n(r.get("vinculos_cnae_transporte_2022")), n(r.get("vinculos_cnae_transporte_2024"))
    if a is None and b is None:
        return None
    return ("emprego", f"- **Emprego no setor (CNAE transporte):** {br(a)} vínculos em "
                       f"2022 → {br(b)} em 2024.")


ORDEM = ["gestao", "trajetoria", "frota", "modal", "despesa", "seguranca", "emprego"]
GERADORES = [linha_gestao, linha_trajetoria, linha_frota, linha_modal,
             linha_despesa, linha_seguranca, linha_emprego]

# rotulo em negrito -> chave, para casar linha existente com linha gerada
ROTULO = {
    "gestão do transporte": "gestao",
    "trajetória institucional": "trajetoria",
    "frota de ônibus": "frota",
    "modal split": "modal",
    "despesa com transporte": "despesa",
    "segurança viária": "seguranca",
    "emprego no setor": "emprego",
    "infraestrutura (osm)": "osm",
    # ⚠️ A linha "a revisar" TEM de ser reconhecida aqui. Sem isto, a segunda
    # passada não a via como linha conhecida, não a recopiava, e o comentário do
    # autor que ela preservava era APAGADO — o script destruiria na 2ª execução
    # justamente o que a 1ª se deu ao trabalho de salvar. Pego rodando duas
    # vezes e comparando; é a razão de a idempotência ser testada, não suposta.
    "a revisar": "revisar",
}


def sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


def chave_da_linha(l):
    # ⚠️ O `[^*]*?` depois do hífen NAO e enfeite: a linha "a revisar" começa com
    # "- ⚠️ **a revisar**", e um padrão `-\s*\*\*` não casa, porque entre o hífen
    # e o `**` há um emoji, que não é espaço. Sem isto a linha ficava
    # irreconhecível na passada seguinte e o comentário do autor que ela
    # preservava era apagado — o script destruía na 2ª execução o que a 1ª
    # salvou. Pego rodando duas vezes e conferindo o arquivo, não o relatório.
    m = re.match(r"\s*-\s*[^*]*?\*\*(.+?)\*\*", l)
    if not m:
        return None
    r = m.group(1).strip().rstrip(":").lower()
    for rot, k in ROTULO.items():
        if r.startswith(rot):
            return k
    return None


def montar(r, bloco_antigo):
    """Novo bloco, preservando verbatim toda linha com interpretação do autor."""
    antigas, preservadas, revisar = {}, set(), []
    for l in (bloco_antigo or "").split("\n"):
        if not l.strip().startswith("-"):
            continue
        k = chave_da_linha(l)
        if k:
            antigas[k] = l.rstrip()
            if INTERPRETA.search(l):
                preservadas.add(k)
    saida = []
    for k, gen in zip(ORDEM, GERADORES):
        if k in preservadas:
            saida.append(antigas[k])          # voz do autor: intocada
            continue
        nova = gen(r)
        if nova:
            saida.append(nova[1])
        elif k in antigas:
            saida.append(antigas[k])          # sem dado novo: não apaga o antigo
    # a linha de OSM sai; se carregava interpretação, não some em silêncio
    if "revisar" in antigas:
        saida.append(antigas["revisar"])       # já criada numa passada anterior
    elif "osm" in antigas and INTERPRETA.search(antigas["osm"]):
        revisar.append(antigas["osm"])
        saida.append("- ⚠️ **a revisar** — linha de infraestrutura OSM retirada do bloco "
                     "(zero no OSM = não mapeado, não inexistente), mas ela carregava "
                     "comentário seu, preservado aqui: " +
                     antigas["osm"].lstrip("- ").strip())
    return TITULO + "\n" + "\n".join(saida), preservadas, revisar


# ---------------------------------------------------------------- aplicação
def bloco_atual(txt):
    m = re.search(r"^### Contexto de mobilidade.*?(?=\n^#{2,3} |\Z)", txt, re.S | re.M)
    return m


def inserir(txt, novo):
    """Substitui o bloco, ou insere ao fim da seção '## 1. Briefing'."""
    m = bloco_atual(txt)
    if m:
        # o match pode arrastar a linha em branco que separa do próximo
        # cabeçalho; sem reconstituí-la, cada passada come um '\n' e a
        # comparação "mudou?" acusa diferença que é só espaço em branco.
        cauda = "\n" if m.group(0).endswith("\n") else ""
        return txt[:m.start()] + novo + cauda + txt[m.end():], "substituído"
    m1 = re.search(r"^## 1\.[^\n]*\n", txt, re.M)
    if not m1:
        return txt, "🔴 sem '## 1.' para ancorar"
    prox = re.search(r"^## ", txt[m1.end():], re.M)
    corte = m1.end() + (prox.start() if prox else len(txt) - m1.end())
    return txt[:corte].rstrip() + "\n\n" + novo + "\n\n" + txt[corte:], "inserido"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gravar", action="store_true", help="grava (padrão: simula)")
    ap.add_argument("--so-faltantes", action="store_true",
                    help="só as fichas que hoje não têm o bloco")
    a = ap.parse_args()

    if not os.path.isdir(FDIR):
        sys.exit(f"🔴 não achei a pasta das fichas em {FDIR}\n"
                 f"   rode a partir da raiz do cofre, ou defina TZ_VAULT.")
    base = {}
    with open(BASE, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            base[(r.get("cod_ibge") or "").strip()] = r

    fichas = sorted(x for x in os.listdir(FDIR)
                    if x.startswith("Ficha") and x.endswith(".md") and "MOC" not in x)
    plano, sem_match, tot_preserv, tot_revisar = [], [], 0, 0
    for nome in fichas:
        p = os.path.join(FDIR, nome)
        txt = open(p, encoding="utf-8").read()
        m = re.search(r"^codigo_ibge:\s*(\d+)", txt, re.M)
        if not m or m.group(1) not in base:
            sem_match.append(nome)
            continue
        tinha = bloco_atual(txt)
        if a.so_faltantes and tinha:
            continue
        novo, preserv, revisar = montar(base[m.group(1)],
                                        tinha.group(0) if tinha else "")
        novo_txt, acao = inserir(txt, novo)
        if novo_txt != txt:
            plano.append((nome, p, novo_txt, acao, preserv, revisar))
            tot_preserv += len(preserv)
            tot_revisar += len(revisar)

    print(f"{len(fichas)} fichas · {len(plano)} a alterar · {len(sem_match)} sem match na base")
    ins = [x for x in plano if x[3] == "inserido"]
    print(f"   bloco inserido (não existia): {len(ins)}")
    print(f"   bloco substituído:            {len(plano)-len(ins)}")
    print(f"   linhas do autor preservadas:  {tot_preserv}")
    print(f"   linhas OSM com comentário mantidas como 'a revisar': {tot_revisar}")
    if ins:
        print("\nfichas que GANHAM o bloco:")
        for x in ins:
            print("   +", x[0])
    if sem_match:
        print("\n⚠️ sem código IBGE ou sem linha na base (não tocadas):")
        for x in sem_match:
            print("   ", x)
    if not a.gravar:
        print("\nnada foi escrito. Para aplicar: --gravar")
        return
    bk = os.path.join(RAIZ, "_meta", "_backups", "_backup-contexto-" +
                      datetime.datetime.now().strftime("%Y-%m-%d_%H%M"))
    os.makedirs(bk, exist_ok=True)
    for nome, p, novo_txt, _, _, _ in plano:
        shutil.copy2(p, os.path.join(bk, nome))
        with open(p, "w", encoding="utf-8", newline="\n") as f:
            f.write(novo_txt)
    print(f"\n✅ {len(plano)} fichas gravadas · backup dos originais em {os.path.basename(bk)}")


if __name__ == "__main__":
    main()
