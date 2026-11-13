# -*- coding: utf-8 -*-
"""
Cria as 5 fichas municipais que faltavam no cofre — Quaraí/RS, Colina/SP,
Coromandel/MG, Pescaria Brava/SC e Ivoti/RS — identificadas como "sem ficha
localizada" na Tabela consolidada de 18/09/2026.

Conteúdo vem inteiramente do que já está apurado na base-mestre
(Municípios TZ - consolidado.xlsx) e na aba "1 Universal" de
Tipologias TZ - consolidado.xlsx — nenhuma pesquisa nova, nenhuma inferência
além do que essas duas fontes já registram. Onde a base-mestre já sinaliza
lacuna (confiab. baixa/média, portão "a verificar"/"não determinável"), a
ficha herda esse sinal, não o resolve.

Só grava se o arquivo não existir. Não sobrescreve.
"""
import os, sys

ROOT = os.path.expanduser("~/mnt/doutorado")
DIR = os.path.join(ROOT, "04 - Análises/Casos municipais/Fichas por município")

LIG = ("## Ligações\n- [[Tabela consolidada - Municípios com Tarifa Zero]] · "
       "[[Tipologias de Tarifa Zero (4 camadas)]] · [[Fichas por município - MOC]]\n")

def montar(nome, uf, regiao, ibge, camada, briefing, dados, biblio, materias, legis, regua_desc, regua_analit):
    fm = (f'---\ntitle: "Ficha - {nome} ({uf})"\ntags:\n  - análise\n  - caso\n  - tarifa-zero\n'
          f'municipio: {nome}\nuf: {uf}\nregiao: {regiao}\ncodigo_ibge: {ibge}\n'
          f'camada: {camada}\ntipologia_analitica: a classificar\npublish: false\ncreated: 2026-09-18\n---\n\n')
    return fm + (
        f"# 🏙️ {nome} — {uf} · Ficha de Tarifa Zero\n\n"
        f"## 1. Briefing\n{briefing}\n\n"
        f"## 2. Principais dados\n{dados}\n\n"
        f"## 3. Bibliografia — em quais fontes o caso aparece\n{biblio}\n\n"
        f"## 4. Matérias de jornais\n{materias}\n\n"
        f"## 5. Legislação\n{legis}\n\n"
        f"## Régua descritiva — trajetória (Cap 5)\n{regua_desc}\n\n"
        f"## Régua analítica (Cap 6)\n{regua_analit}\n\n"
        + LIG
    )

FICHAS = [
  dict(nome="Quaraí", uf="RS", regiao="Sul", ibge=4315305, camada="universal",
    briefing=(
      "Quaraí (RS) tem Tarifa Zero ativa, registrada no cofre a partir do funil orçamentário SICONFI "
      "(03/08/2026) e de nota oficial da prefeitura, que descreve uma \"**LINHA URBANA GRATUITA**\", operada "
      "sob contrato com a empresa **Planalto**. 🔴 **Não confirmado nesta rodada se é linha única ou todo o "
      "sistema municipal** — a base-mestre já registra essa dúvida como aberta; esta ficha não a resolve, "
      "apenas herda o mesmo sinal de incerteza. Ano de início, legislação instituidora e demanda **não "
      "localizados** até aqui."),
    dados=(
      "- **População (2022):** não localizada nesta rodada\n"
      "- **Situação / modelo / início:** Ativa / a confirmar (1 linha? ou sistema completo?) / ano não localizado\n"
      "- **Operador:** Planalto (privada)\n"
      "- **Motivações:** não localizada nesta rodada\n"
      "- **Frota / linhas / demanda:** — / 1 linha (linha única, a confirmar se é todo o sistema) / —\n"
      "- **% do orçamento:** não localizado nesta rodada\n"
      "- **Site da prefeitura:** não levantado nesta rodada"),
    biblio=(
      "- **Aparece em (levantamentos):** funil orçamentário SICONFI (03/08/2026) — ver "
      "[[Tipologias de Tarifa Zero (4 camadas)]]\n"
      "- Confiab. registrada na base-mestre: **média**.\n"
      "- 🔴 Nenhuma literatura acadêmica localizada nesta rodada — não pesquisado."),
    materias="- (nenhuma matéria coletada ainda — apenas nota oficial da prefeitura, sem link registrado na base-mestre)",
    legis=(
      "- **Norma:** não localizada · confiab.: média\n"
      "- **Observação:** nota oficial da prefeitura menciona \"LINHA URBANA GRATUITA\", com contrato com a "
      "empresa Planalto — não é, por si, evidência de norma instituidora. 🔴 A confirmar se há lei/decreto, e "
      "se a gratuidade cobre 1 linha ou todo o sistema, antes de tratar o caso como fechado.\n"
      "- Análise: [[Analise Legislacao Tarifa Zero]] · [[Analise das Legislacoes de Tarifa Zero]]"),
    regua_desc=(
      "_Camada atual: universal (Ativa / universal / ano não localizado), classificação herdada da aba "
      "\"1 Universal\" de Tipologias TZ - consolidado.xlsx, portão marcado **\"a verificar\"** — não confirmada "
      "ausência de portão. Sem registro de mudança de camada/situação nesta rodada._"),
    regua_analit=(
      "- **Tipologia:** a classificar — dado insuficiente\n"
      "- **Justificativa:** sem norma localizada, sem confirmação se a gratuidade cobre 1 linha ou o sistema "
      "inteiro, não há base para classificar nesta rodada.\n"
      "- **Mecanismo de custeio:** não verificado.\n"
      "- **Remuneração do operador:** não verificado.\n"
      "- **Contrapartida de transparência/controle social:** não verificado.")),

  dict(nome="Colina", uf="SP", regiao="Sudeste", ibge=3512001, camada="universal",
    briefing=(
      "Colina (SP) consta como Tarifa Zero universal ativa, achado do funil orçamentário SICONFI "
      "(03/08/2026), marcado **\"a confirmar\"** no próprio registro original da base-mestre. 🔴 **Sem "
      "verificação de fonte primária adicional até aqui** — nem norma, nem operador, nem ano de início, nem "
      "qualquer outro dado operacional foram localizados. Esta é, das 5 fichas novas, a de cobertura mais "
      "fraca."),
    dados=(
      "- **População (2022):** não localizada nesta rodada\n"
      "- **Situação / modelo / início:** Ativa / universal (a confirmar) / ano não localizado\n"
      "- **Operador:** não localizado\n"
      "- **Motivações:** não localizada\n"
      "- **Frota / linhas / demanda:** — / — / —\n"
      "- **% do orçamento:** não localizado nesta rodada\n"
      "- **Site da prefeitura:** não levantado nesta rodada"),
    biblio=(
      "- **Aparece em (levantamentos):** funil orçamentário SICONFI (03/08/2026, achado marcado \"a confirmar\" "
      "no registro original) — ver [[Tipologias de Tarifa Zero (4 camadas)]]\n"
      "- Confiab. registrada na base-mestre: **baixa**.\n"
      "- 🔴 Nenhuma literatura acadêmica localizada nesta rodada — não pesquisado."),
    materias="- (nenhuma matéria coletada ainda)",
    legis=(
      "- **Norma:** não localizada · confiab.: baixa\n"
      "- **Observação:** caso ainda não confirmado por fonte primária — entrou no cofre só pelo funil "
      "orçamentário SICONFI. 🔴 Não usar como caso fechado sem antes buscar confirmação (portal de legislação "
      "municipal, Câmara, ou imprensa local).\n"
      "- Análise: [[Analise Legislacao Tarifa Zero]] · [[Analise das Legislacoes de Tarifa Zero]]"),
    regua_desc=(
      "_Camada atual: universal (Ativa / universal / ano não localizado), classificação herdada da aba "
      "\"1 Universal\" de Tipologias TZ - consolidado.xlsx, portão marcado **\"a verificar\"**. Confiança geral "
      "do caso é baixa — a própria classificação de camada é provisória. Sem registro de mudança nesta rodada._"),
    regua_analit=(
      "- **Tipologia:** a classificar — dado insuficiente\n"
      "- **Justificativa:** caso não confirmado por fonte primária; não há base para classificar.\n"
      "- **Mecanismo de custeio:** não verificado.\n"
      "- **Remuneração do operador:** não verificado.\n"
      "- **Contrapartida de transparência/controle social:** não verificado.")),

  dict(nome="Coromandel", uf="MG", regiao="Sudeste", ibge=3119302, camada="universal",
    briefing=(
      "Coromandel (MG) tem Tarifa Zero universal ativa desde **2023**, por isenção instituída sobre a base "
      "tarifária da **Lei nº 3.607/2014** — alterada pela **Lei nº 4.826/2022** (isenção universal "
      "01/01/2023–31/12/2024) e prorrogada pela **Lei nº 5.072/2025** (01/01/2025–31/12/2028). Confirmado por "
      "fonte primária em 16/08/2026 (confiab. alta). Incluído no canônico a partir de indício de pesquisa "
      "concorrente (operadores × grupos econômicos).\n\n"
      "🔴 **Ressalva relevante para a régua descritiva, já registrada na aba \"1 Universal\" e não resolvida "
      "aqui:** a gratuidade tem **cláusula de vigência determinada (sunset)** — o período atual vai até "
      "31/12/2028, já renovado uma vez (2023-2024 → 2025-2028). Se o dispositivo legal declarar esse prazo "
      "explicitamente (não apenas a prática administrativa), isso é **portão de tempo (camada 2)**, não camada "
      "1 — mesma regra já aplicada a outros casos com prazo declarado na norma. O texto da Lei 3.607/2014 e "
      "das alterações está bloqueado (HTTP 403) para conferência direta do dispositivo. **Padrão análogo a "
      "Primavera do Leste/MT** (trajetória programada). Reavaliar continuidade após 2028."),
    dados=(
      "- **População (2022):** 28.894\n"
      "- **Situação / modelo / início:** Ativa / universal (sunset até 31/12/2028) / 2023\n"
      "- **Operador:** não localizado nesta rodada\n"
      "- **Motivações:** não localizada nesta rodada\n"
      "- **Frota / linhas / demanda:** — / — / —\n"
      "- **% do orçamento:** não localizado nesta rodada\n"
      "- **Site da prefeitura:** não levantado nesta rodada"),
    biblio=(
      "- **Aparece em (levantamentos):** pesquisa de operadores × grupos econômicos (ago/2026), confirmado por "
      "fonte primária em 16/08/2026 — ver [[Tipologias de Tarifa Zero (4 camadas)]]\n"
      "- Confiab. registrada na base-mestre: **alta** (fonte primária confirmada, leis.org/leismunicipais.com.br).\n"
      "- 🔴 Nenhuma literatura acadêmica localizada nesta rodada — não pesquisado."),
    materias="- (nenhuma matéria coletada ainda)",
    legis=(
      "- **Norma:** Lei nº 3.607/2014 (base tarifária do serviço de transporte coletivo urbano), alterada pelo "
      "art. 14 §2º pela Lei nº 4.826/2022 (isenção universal 01/01/2023–31/12/2024) e pela Lei nº 5.072/2025 "
      "(prorrogação da isenção universal para 01/01/2025–31/12/2028) · confiab.: alta\n"
      "- **Link:** https://leis.org/municipais/mg/coromandel/lei/lei-ordinaria/2014/3607/"
      "lei-ordinaria-n-3607-2014-dispoe-sobre-o-servico-de-transporte-coletivo-urbano-de-passageiros-no-municipio-de-coromandel-e-da-outras\n"
      "- **Observação:** incluído no canônico em 16/08/2026. Gratuidade tem cláusula de vigência determinada — "
      "período atual autorizado até 31/12/2028, já renovado uma vez. 🔴 **Não li o texto integral das leis "
      "3.607/2014, 4.826/2022 e 5.072/2025** (bloqueio HTTP 403 na fonte) — não confirmei se o §2º do art. 14 "
      "declara o prazo explicitamente no dispositivo (o que mudaria a camada) ou se o prazo é só de gestão "
      "administrativa. Fica para o autor decidir a leitura, com o texto em mãos.\n"
      "- Análise: [[Analise Legislacao Tarifa Zero]] · [[Analise das Legislacoes de Tarifa Zero]]"),
    regua_desc=(
      "_Camada atual: universal (Ativa / universal / 2023), classificação herdada da aba \"1 Universal\" de "
      "Tipologias TZ - consolidado.xlsx, portão marcado **\"não determinável\"** — a própria aba já sinaliza "
      "que, se o §2º do art. 14 declarar o prazo até 2028 no dispositivo, o caso deveria migrar para camada 2 "
      "(temporal, dias/prazo declarado). Não decido essa migração aqui, só registro que ela está em aberto. "
      "Sem registro de mudança de camada/situação nesta rodada além dessa ressalva._"),
    regua_analit=(
      "- **Tipologia:** a classificar — dado insuficiente (falta o texto integral da norma e dados de operador/custeio)\n"
      "- **Justificativa:** a classificação analítica depende de confirmar remuneração do operador e mecanismo "
      "de custeio, nenhum dos dois levantado nesta rodada.\n"
      "- **Mecanismo de custeio:** não verificado.\n"
      "- **Remuneração do operador:** não verificado.\n"
      "- **Contrapartida de transparência/controle social:** não verificado.")),

  dict(nome="Pescaria Brava", uf="SC", regiao="Sul", ibge=4212650, camada="universal",
    briefing=(
      "Pescaria Brava (SC) opera o **\"Bravinha\"** — transporte público coletivo gratuito municipal, "
      "instituído pela **Lei Ordinária nº 551/2025** (15/05/2025), serviço iniciado em **09/08/2025**. "
      "Confiab. alta: 8+ fontes de imprensa local independentes (Agora Laguna, Portal a Hora, HC Notícias, "
      "Folha Regional) mais o site oficial da prefeitura, com confirmação de continuidade após 1 ano de "
      "operação (completou 1 ano em ago/2026, renovado por +12 meses com recursos próprios do município). "
      "Aparenta cobrir o sistema municipal por completo, sem indício de linhas pagas paralelas — mas isso não "
      "está confirmado por leitura direta da lei (bloqueada, HTTP 403 na fonte oficial). Incluído no canônico "
      "em 21/08/2026."),
    dados=(
      "- **População (2022):** 10.190\n"
      "- **Situação / modelo / início:** Ativa / universal (a confirmar cobertura completa do sistema) / 2025\n"
      "- **Operador:** Beto Viagens e Turismo (Imbituba/SC)\n"
      "- **Motivações:** não localizada nesta rodada\n"
      "- **Frota / linhas / demanda:** 2 micro-ônibus / 2 rotas, 14 comunidades atendidas / —\n"
      "- **% do orçamento:** não localizado nesta rodada\n"
      "- **Site da prefeitura:** https://pescariabrava.sc.gov.br/"),
    biblio=(
      "- **Aparece em (levantamentos):** rodada de revisão da série de 85 blocos (pesquisa operadores × grupos "
      "econômicos), aprofundado e confirmado por múltiplas fontes de imprensa independentes e pelo site oficial "
      "da prefeitura — ver [[Tipologias de Tarifa Zero (4 camadas)]]\n"
      "- Confiab. registrada na base-mestre: **alta** (8+ fontes de imprensa local independentes + site oficial).\n"
      "- Fontes nomeadas na base-mestre, sem link individual coletado nesta rodada: Agora Laguna; Portal a Hora; "
      "HC Notícias; Folha Regional; pescariabrava.sc.gov.br\n"
      "- 🔴 Nenhuma literatura acadêmica localizada nesta rodada — não pesquisado."),
    materias=(
      "- Nomes de fonte registrados na base-mestre (Agora Laguna; Portal a Hora; HC Notícias; Folha Regional), "
      "**sem URL individual coletada nesta rodada** — apenas o link do site oficial da prefeitura está "
      "registrado (ver §5). 🔴 Buscar e registrar os links individuais das matérias antes de citá-las "
      "formalmente."),
    legis=(
      "- **Norma:** Lei Ordinária nº 551/2025 (15/05/2025) — institui o transporte público coletivo gratuito "
      "municipal, batizado \"Bravinha\" · confiab.: alta\n"
      "- **Link:** https://pescariabrava.sc.gov.br/bravinha-transporte-gratuito-para-atender-14-comunidades/\n"
      "- **Observação:** serviço iniciado 09/08/2025, atende 14 comunidades do município; completou 1 ano de "
      "operação em ago/2026, renovado por +12 meses com recursos próprios. 🔴 **Não li o texto integral da Lei "
      "551/2025** (bloqueio HTTP 403 na fonte) — a cobertura \"sistema completo, sem linhas pagas paralelas\" é "
      "leitura da notícia (2 rotas/14 comunidades, seg-sex), não confirmação pelo dispositivo legal.\n"
      "- Análise: [[Analise Legislacao Tarifa Zero]] · [[Analise das Legislacoes de Tarifa Zero]]"),
    regua_desc=(
      "_Camada atual: universal (Ativa / universal / 2025), classificação herdada da aba \"1 Universal\" de "
      "Tipologias TZ - consolidado.xlsx, portão marcado **\"não determinável\"** — a própria aba já aponta "
      "possível portão espacial não verificado (2 rotas cobrindo 14 comunidades nomeadas, não necessariamente "
      "todo o território municipal). Não decido essa classificação aqui. Sem registro de mudança de "
      "camada/situação nesta rodada além dessa ressalva._"),
    regua_analit=(
      "- **Tipologia:** a classificar — dado insuficiente\n"
      "- **Justificativa:** falta confirmar mecanismo de custeio e remuneração do operador para classificar.\n"
      "- **Mecanismo de custeio:** não verificado (obs.legal da base-mestre indica \"recursos próprios do "
      "município\" na renovação de 2026, mas não especifica o mecanismo orçamentário).\n"
      "- **Remuneração do operador:** não verificado.\n"
      "- **Contrapartida de transparência/controle social:** não verificado.")),

  dict(nome="Ivoti", uf="RS", regiao="Sul", ibge=4310801, camada="universal",
    briefing=(
      "Ivoti (RS) tem Tarifa Zero ativa desde **11/05/2026**, custeio 100% municipal, confirmado com "
      "confiança alta (site oficial + 5 veículos de imprensa). Operação sob contratação emergencial com "
      "**Socaltur/Capivarense** (3 editais de contratação emergencial nº 80/2026, 83/2026 e 87/2026, "
      "mar-abr/2026) — evidência administrativa, não legislativa; **nenhuma lei ou decreto instituidor "
      "localizado até aqui** (Diário Oficial \"Mentor\" exige login, ilegível sem navegador; busca em "
      "leis.org, 54 leis no corpus, sem resultado para \"transporte gratuito\"/\"passe livre\"/\"tarifa zero\"). "
      "Incluído no canônico em 03/09/2026 por decisão do autor (\"entram com seus diferentes graus de "
      "maturidade\") — o critério de inclusão aqui é confirmação de operação por outras fontes, não base legal.\n\n"
      "🔴 **Ressalva importante já registrada na base-mestre, preservada aqui:** circula uma narrativa de que a "
      "Tarifa Zero teria vindo de \"recuperação judicial da operadora\" — **essa narrativa NÃO é sustentada "
      "pelas fontes primárias**. A Socaltur/Capivarense teve recuperação judicial real em 2019, mas ligada ao "
      "serviço **intermunicipal**, não ao municipal. A mudança de 2026 foi motivada por o operador anterior "
      "cobrar informalmente (sem contrato) ~R$150 mil/mês por baixa demanda — não por falência. **Não repetir "
      "a narrativa de causalidade sem essa ressalva.** Ver evidência completa em "
      "[[Monitoramento - Candidatos indeterminados (TZ não mapeada)]]."),
    dados=(
      "- **População:** a confirmar (Censo 2010: 19.874; agregador secundário recente, sem atribuição clara ao "
      "Censo 2022, indica ~23.566 — cidades.ibge.gov.br bloqueou o fetch direto na rodada original)\n"
      "- **Situação / modelo / início:** Ativa / universal (contratação emergencial, sem base legal localizada) / 11/05/2026\n"
      "- **Operador:** Socaltur/Capivarense (contratação emergencial)\n"
      "- **Motivações:** operador anterior cobrava informalmente (sem contrato) ~R$150 mil/mês por baixa "
      "demanda — não recuperação judicial/falência (ver ressalva no Briefing)\n"
      "- **Frota / linhas / demanda:** — / — / —\n"
      "- **% do orçamento:** não localizado nesta rodada (custeio descrito como 100% municipal)\n"
      "- **Site da prefeitura:** não levantado nesta rodada"),
    biblio=(
      "- **Aparece em (levantamentos):** monitoramento de candidatos indeterminados, incluído no canônico em "
      "03/09/2026 — ver [[Monitoramento - Candidatos indeterminados (TZ não mapeada)]] e "
      "[[Tipologias de Tarifa Zero (4 camadas)]]\n"
      "- Confiab. registrada na base-mestre: alta para a confirmação de **operação** (site oficial + 5 veículos "
      "de imprensa); **sem confiab. atribuída à legislação**, porque nenhuma foi localizada.\n"
      "- 🔴 Nenhuma literatura acadêmica localizada nesta rodada — não pesquisado."),
    materias="- (nenhuma matéria coletada ainda — a base-mestre registra \"5 veículos de imprensa\" sem nomear ou linkar individualmente; a levantar)",
    legis=(
      "- **Norma:** não localizada (3 editais de contratação emergencial nº 80/2026, 83/2026 e 87/2026, "
      "mar-abr/2026 — evidência administrativa, não legislativa) · confiab.: — (sem norma, sem confiab. "
      "atribuída)\n"
      "- **Observação:** Diário Oficial \"Mentor\" exige login, ilegível sem navegador nesta rodada; busca em "
      "leis.org (54 leis no corpus do município) sem resultado para \"transporte gratuito\"/\"passe "
      "livre\"/\"tarifa zero\". 🔴 Critério de inclusão no cofre é confirmação de **operação** por múltiplas "
      "fontes de imprensa e site oficial, não base legal — registrar isso sempre que este caso for citado como "
      "\"TZ ativa\", para não implicar existência de lei que não foi encontrada.\n"
      "- Análise: [[Analise Legislacao Tarifa Zero]] · [[Analise das Legislacoes de Tarifa Zero]]"),
    regua_desc=(
      "_Camada atual: universal (Ativa / universal / 2026), classificação herdada da aba \"1 Universal\" de "
      "Tipologias TZ - consolidado.xlsx, portão marcado **\"a verificar\"**. Sem base legal localizada, a "
      "própria noção de \"portão\" (que normalmente se lê no dispositivo da norma) fica sem onde ser lida — "
      "verificação depende de acessar o Diário Oficial \"Mentor\" (exige login) ou os editais de contratação "
      "emergencial diretamente. Sem registro de mudança de camada/situação nesta rodada._"),
    regua_analit=(
      "- **Tipologia:** a classificar — dado insuficiente\n"
      "- **Justificativa:** sem base legal localizada e sem dados de custeio/remuneração do operador, não há "
      "base para classificar.\n"
      "- **Mecanismo de custeio:** parcialmente conhecido — custeio descrito como 100% municipal na fonte, mas "
      "sem detalhamento do mecanismo orçamentário; tratar como não verificado para fins de classificação.\n"
      "- **Remuneração do operador:** não verificado.\n"
      "- **Contrapartida de transparência/controle social:** não verificado.")),
]

def main():
    os.makedirs(DIR, exist_ok=True)
    criadas = []
    for f in FICHAS:
        p = os.path.join(DIR, f"Ficha - {f['nome']} ({f['uf']}).md")
        if os.path.exists(p) and os.path.getsize(p) > 0:
            print("JA EXISTE, nao sobrescrito:", os.path.basename(p))
            continue
        content = montar(**f)
        with open(p, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(content)
        print("criada:", os.path.basename(p))
        criadas.append(os.path.basename(p))
    print(f"\nTotal criadas: {len(criadas)}")

if __name__ == "__main__":
    main()
