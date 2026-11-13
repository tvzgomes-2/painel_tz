#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
classificar_rodada.py — aplica o critério de inclusão da RSL às
referências externas mapeadas pela rede bibliométrica.

CRITÉRIO (declarado):
  Entra no corpus a referência que (1) trata de Tarifa Zero / transporte
  público sem cobrança E (2) carrega informação sobre EXPERIÊNCIAS concretas
  (avaliação, medição, descrição de caso, modelagem aplicada a caso, análise
  jurídica ou financeira de arranjo existente).
  NÃO entra: teoria e contexto sem experiência de TZ (vão para a Biblioteca)
  nem imprensa, sites, entrevistas e documentos avulsos (vão para as fichas
  municipais e o clipping, como fonte documental).

SAÍDA: 05 - Referências/Rede bibliométrica/Rodada — triagem (gerado).md
"""
import csv, io, os, re, sys, unicodedata, collections

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DIR  = os.path.join(RAIZ, "05 - Referências", "Rede bibliométrica")

def norm(s):
    s = unicodedata.normalize("NFD", s or "")
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()

TEMATICA = (r"tarifa zero|tarifa-zero|tarifazero|fare[- ]free|free[- ]fare|"
            r"free public transport|free transit|zero[- ]fare|fare abolition|"
            r"abolish fares|gratuidade|gratuite|gratuito|gratuita|passe livre|"
            r"sem catraca|catraca livre|tarifa cero|desatarifac|destarifac|"
            r"nulltarif|kostenlos")

# 1) marcador FORTE de veículo acadêmico/técnico — tem precedência sobre imprensa,
#    porque DOI e link de repositório não fazem de um artigo uma notícia.
FORTE_ACAD = (r"\bdissertac|\btese\b|\bteses\b|\btcc\b|monografia|doutorado|mestrado|"
              r"master|phd|journal|\brevista\b|anais|congresso|working paper|"
              r"transportation|transport policy|transport research|transport review|"
              r"rel\.?\s?tec|relatorio tecnico|synthesis|policy brief|sustainability|"
              r"cadernos|texto para discuss|\bipea\b|\bcutr\b|\btcrp\b|\bnctr\b|predit|liepp|"
              r"enanpur|anpet|anpad|editora|\bisbn\b|universidade|university|"
              r"routledge|elsevier|springer|blucher|boitempo|doi:|10\.\d{4}/|"
              r"frontiers|research in transport|regional science|economics|geograph")
# 2) marcador de imprensa / site / documento avulso — só decide se (1) não bateu
IMPRENSA = (r"folha de s|folha de sao|o globo|estadao|estado de s|carta capital|"
            r"exame|\bveja\b|agencia brasil|\bbbc\b|reuters|politico|\bdw\b|published\s|"
            r"\burl:|blog|podcast|noticias|camara notic|jornal do comercio|"
            r"rede brasil atual|piaui|jacobin|outraspalavras|metropolitiques|"
            r"citiestoday|carfree|le monde|diario de|globustrotter|err news|"
            r"ruhrnachrichten|cnbc|iclei|prefeitura de|ouvidoria|indicacao n|"
            r"entrevista|tarifazero\.org|site do|\bwww\.")

# 3) ajustes manuais declarados — a regra erra, e o erro fica registrado, não escondido
OVERRIDES = {
    # tirados de A: não tratam de EXPERIÊNCIAS de TZ
    "johnson1973":   ("B", "ruído de extração: referências coladas, sem obra identificável"),
    "conforto2011":  ("B", "método de revisão sistemática, não experiência de TZ"),
    "kalil2020":     ("B", "regulação do trabalho em plataformas; a menção a TZ é referência colada"),
    "gama2011":      ("B", "juventude e cidade; trata do MPL, não de experiência de TZ"),
    "inacio2008":    ("B", "estudo sobre o MPL de Florianópolis, não sobre experiência de TZ"),
    "anon2005":      ("B", "relato militante da guerra da tarifa; fonte documental"),
    "duvauroux2016": ("B", "ensaio normativo francês pró-gratuidade, sem experiência avaliada"),
    "camarano1966":  ("A", "IPEA, efeitos das gratuidades sobre a tarifa na RMSP — ano do citekey está errado"),
    # trazidos para A: a regra os jogou em B por causa de DOI/URL
    "cats2017":      ("A", "Tallinn antes/depois; DOI confundido com marcador de imprensa"),
    "hess2017":      ("A", "Decrypting FFPT in Tallinn, Case Studies on Transport Policy"),
    "bull2021":      ("A", "ensaio aleatorizado em Santiago — único RCT do campo"),
    "bull2020":      ("A", "mesma pesquisa, versão anterior"),
    "vermander2021": ("A", "FFPT em pequenos municípios brasileiros — o objeto exato da tese"),
    "goldberg2021":  ("A", "suspensão de tarifas nos EUA durante a COVID — o caso que reverteu"),
    "guelton2020":   ("A", "modelo de financiamento da gratuidade, Transports Urbains"),
    "loder2022":     ("A", "experimento nacional alemão do bilhete de 9 euros"),
    "keblowski2019": ("A", "Why (not) abolish fares — a definição canônica"),
    "humbertosd":    ("A", "Libreville (Gabão), a maior experiência do mundo em população"),
    "oliveirasd":    ("A", "formação da agenda do transporte gratuito em Maricá"),
    "pintosd":       ("A", "estudo de caso do transporte de Eusébio (CE)"),
    "briche2018":    ("A", "Dunkerque como laboratório da gratuidade"),
    "giovannangeli2012": ("A", "Aubagne, experiência social documentada"),
    "hure2021":      ("A", "conversão dos atores à gratuidade"),
    "basnak2023":    ("A", "modelos de otimização aplicados a cidades chilenas"),
    "david2022":     ("A", "gratuidade e congestionamento, revisão e implicações para Paris"),
    "grzelec2020":   ("A", "efeitos do alargamento seletivo da gratuidade"),
    "brie2020":      ("A", "Nulltarif — coletânea de casos europeus"),
    "ntoutoume2024": ("A", "orçamento da gratuidade no Gabão em 2024"),
    "andres2024":    ("A", "resultados da maior experiência brasileira (Maricá), com dado"),
    "brinco2017":    ("A", "tarifação e gratuidade, Indicadores Econômicos FEE"),
    "scolari2014":   ("A", "direito social ao transporte à tarifa zero"),
    "cordier2007":   ("A", "efeitos da gratuidade total sobre a frequentação, relatório final"),
    "cordier2008":   ("A", "mesma pesquisa, versão publicada"),
    "volinski2019":  ("A", "TCRP Synthesis 101, mesma obra de volinski2012"),
    "stochmann2003": ("A", "duplicata de storchmann2003 — grafia divergente"),
    "lopessd":       ("A", "duplicata de lopes2017 (Viçosa/MG)"),
    "catssd":        ("A", "duplicata de cats2014"),
    "caribesd":      ("A", "tese de Caribé — conferir se é o item 9 do corpus"),
    "landinsd":      ("A", "duplicata do item 11 (Landin) — conferir"),
    "peschanski2013":("B", "capítulo de Cidades rebeldes — o volume é o item 1 do corpus"),
    "maricatosd":    ("B", "Cidades rebeldes — é o item 1 do corpus"),
    "rolnik2013":    ("B", "Cidades rebeldes — é o item 1 do corpus"),
}

OVERRIDES.update({
    "villaca2015":   ("B", "teoria urbana; a mencao a TZ vem de referencia colada"),
    "harvey2013":    ("B", "capitulo de Cidades rebeldes, que e o item 1 do corpus"),
    "milne2009":     ("B", "mobilidade infantil; sem experiencia de TZ"),
    "souza2005":     ("B", "cartografia geoambiental; ruido de extracao"),
    "martins2013":   ("B", "epistemologia da pesquisa; nao trata de TZ"),
    "kresnanto2022": ("B", "gestao da demanda por julgamento de especialistas; nao e TZ"),
    "hess2020":      ("B", "materia da CNBC sobre custo de transporte nos EUA"),
    "kobie2022":     ("B", "materia de divulgacao"),
    "intelligent2021":("B", "materia de revista setorial"),
    "zhen2021":      ("B", "post institucional do ICLEI"),
    "souza2024":     ("B", "materia do Estadao sobre a frota de Sao Caetano"),
    "troi2023":      ("B", "entrevista com Lucio Gregori; fonte documental"),
    "ntoutoume2024": ("B", "referencia corrompida na extracao; virou o Observatoire"),
})

# obras identicas com chaves diferentes: alias -> canonica (contam uma vez so)
DUPLICATAS = {
    "volinski2019": "volinski2012", "catssd": "cats2014", "cordier2008": "cordier2007",
    "bull2020": "bull2021", "stochmann2003": "storchmann2003", "lopessd": "lopes2017",
    "baum1973": "baum1972", "passante2018": "konishi2018", "peronesd": "perone2002",
}
# chaves que sao, na verdade, itens JA no corpus (grafia divergente)
ALIAS_CORPUS = {"caribesd": "9", "landinsd": "11", "humbertosd": None,
                "muniz2021": "10",   # Lopes e Muniz, Monte Carmelo/MG = item 10
                "lopessd": None}     # Vicosa/MG e obra distinta, nao e o item 10



# ------------------------------------------------------------------
# 4) ESCOPO BRASILEIRO — terceira dimensão do critério (03/09/2026)
#    A revisão trata de EXPERIÊNCIAS BRASILEIRAS de Tarifa Zero.
#    Obra sobre caso estrangeiro vira referência comparativa, não item.
#    Classificação por pontuação declarada (BR se soma >= 2):
#      +2  menção explícita a Brasil / brasileiro / Brazil
#      +2  sigla de UF entre parênteses ou após barra  (MG) /SP
#      +2  veículo ou instituição brasileira
#      +1  por município da base-mestre citado nominalmente
#           (excluídos os nomes ambíguos: Arcos, Assis, Cacoal, Cantagalo, Carmo, Cianorte, Dourado, Faxinal, Formosa, Goiás, Holambra, Ibaté, Itararé, Jales, Lins, Machado, Matinhos, Morretes, Palmas, Parobé, Piedade, Pitanga, Portão, Sarzedo, Tambaú, Tietê, Vitória)
# ------------------------------------------------------------------
BR_PAIS = r"brasil|brasileir|brazil"
UFS = ("ac|al|ap|am|ba|ce|df|es|go|ma|mt|ms|mg|pa|pb|pr|pe|pi|rj|rn|rs|ro|rr|sc|sp|se|to")
BR_UF = r"\((?:" + UFS + r")\)|/(?:" + UFS + r")\b|-\s?(?:" + UFS + r")\b"
BR_VEICULO = (r"anpet|enanpur|\banpad\b|\bipea\b|\bantp\b|\bntu\b|revista dos transportes"
              r"|folha de s|folha de sao|estadao|estado de s|o globo|carta capital|agencia brasil"
              r"|jornal do comercio|rede brasil atual|\bpiaui\b|outraspalavras|jacobin\.com\.br"
              r"|\buf[a-z]{2}\b|\busp\b|unicamp|\bfgv\b|\bfee\b|labcidade|tarifazero\.org"
              r"|autonomia literaria|boitempo|rosa luxemburgo|cebrap|camara municipal|prefeitura")
BR_MUN = r"|".join(re.escape(norm(m)) for m in ['Alumínio', 'Anicuns', 'Antonina', 'Aquiraz', 'Araranguá', 'Araçariguama', 'Arceburgo', 'Artur Nogueira', 'Balneário Arroio Do Silva', 'Balneário Camboriú', 'Balneário Piçarras', 'Batatais', 'Bela Vista Do Toldo', 'Belo Vale', 'Bombinhas', 'Brumadinho', 'Campo Belo', 'Capão Bonito', 'Carambeí', 'Casimiro De Abreu', 'Caucaia', 'Cerquilho', 'Clevelândia', 'Cláudio', 'Comendador Levy Gasparian', 'Conceição De Macabu', 'Conchal', 'Conchas', 'Costa Rica', 'Dois Córregos', 'Dom Silvério', 'Dores Do Indaiá', 'Eusébio', 'Forquilhinha', 'Garopaba', 'Governador Celso Ramos', 'Guapimirim', 'Guararema', 'Ibirité', 'Igaratá', 'Ilha Comprida', 'Ilha Solteira', 'Itaboraí', 'Itaperuçu', 'Itapetininga', 'Itapeva', 'Itaporanga', 'Itatiaiuçu', 'Ituiutaba', 'Ivaiporã', 'Jeceaba', 'Lagoa Da Prata', 'Lauro Muller', 'Leopoldina', 'Luziânia', 'Macatuba', 'Mariana', 'Mata De São João', 'Monte Carmelo', 'Morungaba', 'Muzambinho', 'Mário Campos', 'Natividade', 'Nazaré Paulista', 'Ouro Branco', 'Paracambi', 'Paranaguá', 'Pedro De Toledo', 'Pedro Osório', 'Penápolis', 'Pirapora', 'Porto Belo', 'Porto Feliz', 'Potirendaba', 'Presidente Kennedy', 'Quatro Barras', 'Ribas Do Rio Pardo', 'Rio Branco Do Sul', 'Santa Cruz Do Rio Pardo', 'Santa Isabel', 'Santa Rita Do Passa Quatro', 'Santana Do Deserto', 'Santo Antônio De Posse', 'Silva Jardim', 'Sorriso', 'São Caetano Do Sul', 'São Fidélis', 'São Joaquim De Bicas', 'São José Da Barra', 'São José Da Lapa', 'São João Da Barra', 'São João Del Rei', 'São Lourenço', 'São Lourenço Da Serra', 'São Sebastião Do Alto', 'Taquarituba', 'Três Barras', 'Vargem Grande Paulista', 'Vilhena', 'Wenceslau Braz'])
BR_CAPITAIS = (r"sao paulo|rio de janeiro|belo horizonte|curitiba|salvador|fortaleza|recife"
               r"|porto alegre|brasilia|goiania|manaus|belem|florianopolis|natal|campo grande"
               r"|teresina|niteroi|maceio|aracaju|joao pessoa|cuiaba|porto velho|sao luis")

def escopo_br(s):
    p = 0
    if re.search(BR_PAIS, s):     p += 2
    if re.search(BR_UF, s):       p += 2
    if re.search(BR_VEICULO, s):  p += 2
    p += len(re.findall(BR_MUN, s))
    p += 2 * (1 if re.search(BR_CAPITAIS, s) else 0)
    return p


# 5) ajustes de ESCOPO declarados — a pontuação não vê o que a string não diz
ESCOPO_OVERRIDE = {
    "rodrigues2024": (True,  "Brasil: 57 municipios tratados e 2.731 controles, 1990-2022, DiD escalonado"),
    "santarem2023":  (True,  "ciclo tarifario brasileiro; autor e objeto nacionais"),
    "pintosd":       (True,  "estudo de caso de Eusebio (CE)"),
    "piazza2017":    (True,  "monografia UFSC sobre gratuidade no transporte coletivo brasileiro"),
    "cirillosd":     (False, "Alexandria, Estados Unidos"),
}


def n_citantes(r):
    return len([x for x in (r.get("citada_por") or "").split(",") if x.strip()])

def _created_preservado(caminho, hoje=None):
    """Devolve o `created` que a nota ja tem; se ela ainda nao existe, a data de hoje.
    Sem isso, cada rodada reescreveria a data de criacao — e o campo perderia sentido."""
    import datetime
    if caminho and os.path.exists(caminho):
        try:
            cab = io.open(caminho, encoding="utf-8").read(800)
            m = re.search(r"^created:\s*([0-9]{4}-[0-9]{2}-[0-9]{2})\s*$", cab, re.M)
            if m:
                return m.group(1)
        except Exception:
            pass
    return (hoje or datetime.date.today()).isoformat()

def main():
    p = os.path.join(DIR, "referencias_distintas.csv")
    rows = list(csv.DictReader(io.open(p, encoding="utf-8"), delimiter=";"))
    tema, fora_tema = [], []
    for r in rows:
        (tema if re.search(TEMATICA, norm(r["referencia"])) else fora_tema).append(r)

    dentro = [r for r in tema if (r.get("no_corpus") or "").strip()]
    ausent = [r for r in tema if not (r.get("no_corpus") or "").strip()]

    acad, docum, ajustes = [], [], []
    for r in ausent:
        s = norm(r["referencia"])
        if re.search(FORTE_ACAD, s):      dest = "A"
        elif re.search(IMPRENSA, s):      dest = "B"
        else:                              dest = "B"
        ov = OVERRIDES.get(r["chave"])
        if ov and ov[0] != dest:
            ajustes.append((r["chave"], dest, ov[0], ov[1])); dest = ov[0]
        elif ov:
            dest = ov[0]
        if r["chave"] in ALIAS_CORPUS and ALIAS_CORPUS[r["chave"]]:
            r["no_corpus"] = ALIAS_CORPUS[r["chave"]]
            dentro.append(r); continue
        (acad if dest == "A" else docum).append(r)

    for lst in (acad, docum, dentro):
        lst.sort(key=lambda r: (-n_citantes(r), r["chave"]))

    dups = [r for r in acad if r["chave"] in DUPLICATAS]
    acad = [r for r in acad if r["chave"] not in DUPLICATAS]
    def eh_br(r):
        ov = ESCOPO_OVERRIDE.get(r["chave"])
        return ov[0] if ov else (escopo_br(norm(r["referencia"])) >= 2)
    acad_br  = [r for r in acad if eh_br(r)]
    acad_int = [r for r in acad if not eh_br(r)]
    dentro_br = [r for r in dentro if escopo_br(norm(r["referencia"])) >= 2]
    tot_cand = len(dentro_br) + len(acad_br)
    taxa = 100.0 * len(dentro_br) / tot_cand if tot_cand else 0.0

    A = []
    w = A.append
    w("---"); w('title: "Rodada — triagem (gerado)"')
    w("tags: [dados, rsl-tz, bibliometria, corpus]"); w("publish: false")
    # created preservado entre rodadas: se a nota ja existe, mantem a data original
    w("created: %s" % _created_preservado(os.path.join(DIR, "Rodada — triagem (gerado).md"))); w("---"); w("")
    w("# Rodada — triagem das referências externas")
    w("")
    w("> Gerado por `_meta/scripts/classificar_rodada.py`. **Classificação automática por regra declarada —")
    w("> é uma triagem, não um julgamento.** A coluna final de cada item continua sendo do autor.")
    w("")
    w("**Critério de inclusão no corpus:** a referência (1) trata de Tarifa Zero / transporte sem cobrança")
    w("**e** (2) carrega informação sobre **experiências concretas**. Teoria e contexto sem experiência vão")
    w("para a Biblioteca; imprensa, sites e documentos avulsos vão para as fichas municipais e o clipping.")
    w("")
    w("## Medida de incorporação")
    w("")
    w("| indicador | valor |")
    w("|---|---:|")
    w(f"| referências distintas citadas pelos itens fichados | **{len(rows)}** |")
    w(f"| — temáticas (passam no filtro de TZ) | **{len(tema)}** ({100.0*len(tema)/len(rows):.1f}%) |")
    w(f"| — não temáticas (teoria, contexto, método) | {len(fora_tema)} |")
    w("")
    w("| das temáticas | valor |")
    w("|---|---:|")
    w(f"| já no corpus | **{len(dentro)}** |")
    w(f"| ausentes, com veículo acadêmico/técnico | **{len(acad)}** |")
    w(f"| — dessas, sobre **casos brasileiros** → **candidatas** | **{len(acad_br)}** |")
    w(f"| — dessas, sobre casos estrangeiros → referência comparativa | {len(acad_int)} |")
    w(f"| — descontadas como duplicata de outra chave | {len(dups)} |")
    w(f"| ausentes, imprensa/site/documento → **fonte documental** | {len(docum)} |")
    w("")
    w(f"### 🎯 Taxa de incorporação = **{taxa:.1f}%**")
    w("")
    w(f"Isto é: das **{tot_cand}** referências que passam nos **três** critérios — temática, com experiência,")
    w(f"e sobre caso brasileiro —, o corpus já contém **{len(dentro_br)}**.")
    w("")
    w("**Como usar como critério de parada:** repetir esta medida ao fim de cada rodada. A rodada seguinte")
    w("se justifica enquanto a taxa subir de forma relevante. **Encerra-se quando uma rodada não produzir")
    w("candidatas novas** — ou seja, quando as referências citadas pelos itens recém-incorporados já")
    w("estiverem todas dentro do corpus. Isso é saturação, e é o que Xiao e Watson pedem que se declare.")
    w("")
    w("## A — Candidatas ao corpus (temáticas · acadêmicas · CASOS BRASILEIROS)")
    w("")
    w("| citada por | chave | referência |")
    w("|---:|---|---|")
    for r in acad_br:
        ref = " ".join((r["referencia"] or "").split())[:210]
        w(f"| {n_citantes(r)} ({r['citada_por']}) | `{r['chave']}` | {ref} |")
    w("")
    w("## A-INT — Temáticas e acadêmicas, mas sobre casos ESTRANGEIROS")
    w("")
    w("**Não entram no corpus** — a revisão trata de experiências brasileiras. ✅ **Entram como")
    w("referência comparativa na [[Biblioteca Zotero (índice)]]**, e várias são indispensáveis à tese")
    w("(Tallinn, Dunquerque, o RCT de Santiago, a reversão dos EUA pós-COVID).")
    w("")
    w("| citada por | chave | referência |")
    w("|---:|---|---|")
    for r in acad_int:
        ref = " ".join((r["referencia"] or "").split())[:210]
        w(f"| {n_citantes(r)} ({r['citada_por']}) | `{r['chave']}` | {ref} |")
    w("")
    if ajustes:
        w("## Ajustes manuais declarados")
        w("")
        w("A regra automática erra; o erro fica registrado, não escondido.")
        w("")
        w("| chave | regra dizia | ficou | motivo |")
        w("|---|---|---|---|")
        for ch, de, para, motivo in sorted(ajustes):
            w(f"| `{ch}` | {de} | **{para}** | {motivo} |")
        w("")
    w("## B — Fonte documental (temáticas, mas imprensa/site/documento)")
    w("")
    w("Não entram no corpus. **Destino: fichas municipais, [[Reportagens por cidade]] e [[Clipping TZ 2026 — a processar]].**")
    w("")
    w("| citada por | chave | referência |")
    w("|---:|---|---|")
    for r in docum:
        ref = " ".join((r["referencia"] or "").split())[:210]
        w(f"| {n_citantes(r)} ({r['citada_por']}) | `{r['chave']}` | {ref} |")
    w("")
    w("## C — Já no corpus (controle)")
    w("")
    w("| citada por | chave | item | referência |")
    w("|---:|---|---|---|")
    for r in dentro:
        ref = " ".join((r["referencia"] or "").split())[:150]
        w(f"| {n_citantes(r)} | `{r['chave']}` | {r['no_corpus']} | {ref} |")
    w("")
    w("⚠️ **As 616 referências não temáticas não aparecem aqui de propósito:** são o referencial teórico e")
    w("metodológico dos itens, e **não são candidatas ao corpus por definição do critério**. Isso não as torna")
    w("irrelevantes para a tese — várias são centrais ao [[Cap 7 - A estrutura de poder no transporte coletivo]] —,")
    w("apenas as coloca na [[Biblioteca Zotero (índice)]] e não na revisão.")

    out = os.path.join(DIR, "Rodada — triagem (gerado).md")
    io.open(out, "w", encoding="utf-8", newline="\n").write("\n".join(A) + "\n")
    print(f"temáticas {len(tema)}/{len(rows)} · no corpus {len(dentro)} · candidatas {len(acad)} · documentais {len(docum)}")
    print(f"TAXA DE INCORPORAÇÃO: {taxa:.1f}%")
    print("gravado em", out)

if __name__ == "__main__":
    main()
