#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""gerar_registro_fontes.py — gera `03 - Dados/Registro de fontes de dados.md`,
o apêndice metodológico que identifica cada base usada em tabela ou modelo da
tese pelos seis campos que permitem reproduzir a consulta.

======================================================================
O PROBLEMA QUE ISTO RESOLVE (crítica externa, item 8)
======================================================================
"Para dados que sustentam tabelas e modelos, a página inicial raramente permite
reproduzir a consulta." A crítica está certa quanto ao TEXTO da tese — mas o
cofre já sabe quase tudo o que falta; o que não existe é o caminho entre os dois.
Medido em 17/10/2026:

  * `biblioteca.bib` tem **783 @article, 456 @misc, 173 @techreport e ZERO
    @dataset**. Nenhuma entrada para Siconfi, ANP, DENATRAN/Senatran ou FINBRA.
    Os relatórios SIMOB/ANTP estão citados (são @techreport); as **séries** que
    alimentam as figuras, não.
  * `05 - Referências/_zotero/Bases de dados.ris` — as "13 entradas" que o
    [[Mapa de Dados]] anuncia — **não existe mais**. A referência está morta.
  * "Siconfi" aparece **0 vez** no texto dos capítulos, embora o FINBRA (que é
    Siconfi) alimente o Cap. 8.
  * `Base Municipal v3/metadados.csv` já nomeia a tabela exata de várias fontes
    ("ANP, Série Histórica de Levantamento de Preços de Combustíveis";
    "Siconfi/FINBRA Anexo I-D"), e os scripts `baixar_*.py` já carregam o
    endpoint (ex.: `https://apidatalake.tesouro.gov.br/ords/siconfi/tt`).

➡️ **Logo, isto não é coleta nova: é tornar citável o que já está documentado.**
O script lê as três evidências que já existem — o `metadados.csv`, os scripts de
coleta e os próprios arquivos — e as junta à ficha curada de cada base.

======================================================================
POR QUE GERADO, E NÃO ESCRITO À MÃO
======================================================================
Um registro de proveniência escrito à mão envelhece no dia seguinte. Este lê, a
cada execução: **nome do arquivo, tamanho, data de modificação e SHA-256** de
cada objeto, e o cabeçalho e a URL do script que o coletou. A data de extração
declarada é, portanto, verificável — e a mudança silenciosa de um arquivo
aparece como mudança de hash.

⚠️ **O que o mtime é e o que não é.** É a data em que o arquivo chegou ao cofre,
não necessariamente a data do recorte da fonte. Onde as duas diferem, a ficha
curada declara as duas em separado — é exatamente a distinção que a crítica pede
para o CNPJ (data dos dados ≠ data de processamento ≠ versão da tabela
produzida).

🔴 **Campo sem confirmação sai como `[A CONFIRMAR]`, nunca preenchido por
plausibilidade.** NA ≠ 0 vale para metadado como vale para dado.

USO  python gerar_registro_fontes.py [--gravar]
"""
import argparse
import csv
import datetime
import glob
import hashlib
import os
import re
import shutil
import sys

RAIZ = os.environ.get("TZ_VAULT") or os.getcwd()
DATA = os.path.join(RAIZ, "03 - Dados", "_data")
SCRIPTS = os.path.join(RAIZ, "_meta", "scripts")
META = os.path.join(DATA, "Base Municipal v3", "metadados.csv")
SAIDA = os.path.join(RAIZ, "03 - Dados", "Registro de fontes de dados.md")
AC = "[A CONFIRMAR]"

# ---------------------------------------------------------------------------
# Ficha curada por base. Só entra base que sustenta tabela, figura ou modelo.
# Campos: os seis pedidos pela crítica + o script de coleta e os arquivos.
#   nome      nome exato da base/tabela, como a fonte a chama
#   edicao    edição ou versão (não o ano do dado)
#   periodo   período coberto pelos dados
#   filtros   recorte aplicado na extração
#   endereco  endpoint, DOI ou procedimento de obtenção
#   script    script do cofre que coleta ou processa
#   arquivos  globs, relativos a 03 - Dados/_data (ou ao cofre, se começarem por /)
#   obs       ressalva de uso
# ---------------------------------------------------------------------------
FONTES = [
 dict(bloco="Casos de Tarifa Zero",
      nome="Brazilian Municipalities with Full Fare-Free Public Transport Policies",
      autor="SANTINI, Daniel", edicao="v8 (abril de 2026)",
      periodo="situação em abr/2026; política desde 1990",
      filtros="nenhum — base recebida integral (154 municípios: 145 vigentes + encerradas)",
      endereco="Harvard Dataverse, DOI 10.7910/DVN/Z927PD (DOI estável entre versões; "
               "a versão é que identifica o objeto)",
      script="", arquivos=["casos por fonte/Santini - Dataverse Z927PD (abril 2026).xlsx",
                           "casos por fonte/Santini - Brazilian municipalities with full FFPT (abril 2026, enviado 24-09-2026).xlsx",
                           "casos por fonte/Dataverse Santini/Brazilian municipalities with full Fare-Free Public Transport - April 2026-1.xlsx"],
      obs="🚨 **Os três arquivos acima são o MESMO objeto** — SHA-256 idêntico, verificado "
          "em 17/10/2026. Os nomes diferentes (um 'Dataverse', outro 'enviado 24-09-2026', "
          "outro dentro de `Dataverse Santini/`) sugerem três fontes e não são. "
          "**Citar sempre pelo DOI e pela versão, nunca pelo nome do arquivo.** "
          "É a espinha dorsal da base-mestre."),
 dict(bloco="Casos de Tarifa Zero",
      nome="Cidades com Tarifa Zero universal no Brasil (levantamento avulso)",
      autor="SANTINI, Daniel", edicao="levantamento de 28/09/2026 — não é versão do Dataverse",
      periodo="situação em set/2026", filtros="152 cidades; inclui metrô/VLT",
      endereco=AC + " — recebido do autor da lista; não há depósito com DOI para este objeto",
      script="", arquivos=["casos por fonte/Santini (levantamento)/Santini_2026-09-28_cidades_TZ_universal_152.csv"],
      obs="🔴 **Objeto distinto do Dataverse v8, e é esta a confusão que a crítica aponta.** "
          "Esquema diferente (traz `População (2024)` e `Tipo`: Ônibus, Metrô/VLT), contagem "
          "diferente (152) e critério diferente — inclui Teresina/PI, que **esta pesquisa "
          "exclui do escopo**. Não é atualização da v8: é outra lista. Nunca escrever "
          "'Santini (2026)' sem dizer qual dos dois."),
 dict(bloco="Casos de Tarifa Zero",
      nome="Municípios TZ - consolidado (base-mestre da pesquisa)",
      autor="elaboração do autor", edicao="congelamento de 11/10/2026",
      periodo="políticas vigentes e encerradas até 11/10/2026",
      filtros="192 linhas; 186 em escopo (180 ativas + 6 encerradas)",
      endereco="produto da pesquisa; cópia congelada com SHA-256 em "
               "`03 - Dados/_data/congelamento-2026-10-11/`",
      script="consolidar_mestre.py", arquivos=["casos por fonte/Municípios TZ - consolidado.xlsx"],
      obs="Dado da pesquisa, não de fonte citada. Alterações posteriores ao congelamento "
          "entram no [[Registro de alterações pós-congelamento]]; citar como "
          "'base de 11/10/2026, com N alterações registradas até DD/MM'."),
 dict(bloco="Casos de Tarifa Zero",
      nome="Tipologias TZ - consolidado (régua descritiva)",
      autor="elaboração do autor", edicao="congelamento de 11/10/2026",
      periodo="classificação do desenho vigente em 11/10/2026",
      filtros="abas por camada; contar nas abas, nunca na RESUMO",
      endereco="produto da pesquisa; regras em [[Regras de classificacao das reguas]]",
      script="gerar_indice_camadas.py · enriquecer_regua_portao.py",
      arquivos=["casos por fonte/Tipologias TZ - consolidado.xlsx"],
      obs="A taxonomia mudou três vezes (4 camadas até 13/09; 5 camadas 13–18/09; "
          "1 a 3 desde 18/09). **Número de camada só é interpretável com a data da regra.**"),

 dict(bloco="Grupos econômicos",
      nome="Cadastro Nacional da Pessoa Jurídica — Dados Abertos (Estabelecimentos, Sócios, Empresas)",
      autor="BRASIL. Receita Federal", edicao="recorte de maio de 2024",
      periodo="situação cadastral em mai/2024",
      filtros="CNAE 4921-3/01 e 4921-3/02 (núcleo); recorte experimental de 6 CNAEs "
              "(4922-1, 4929-9) em pasta própria, não somado ao núcleo",
      endereco="https://dadosabertos.rfb.gov.br/CNPJ/ (arquivos particionados por lote)",
      script="CNPJ/ETL/ETL-CNPJ.sql · limpeza.R · carregamento.R",
      arquivos=["CNPJ/Receita Federal - dados brutos/ESTABELECIMENTOS0.csv",
                "CNPJ/Receita Federal - dados brutos/SOCIO0.csv"],
      obs="🔴 **As três datas que a crítica pede separadas:** (1) **dado** — recorte da "
          "Receita de **mai/2024**; (2) **processamento** — filtragem por CNAE em "
          "**13/07/2026** (núcleo) e **24/07/2026** (6 CNAEs); (3) **tabela produzida** — "
          "ver a entrada seguinte. Confundi-las faz parecer que a rede societária é de 2026."),
 dict(bloco="Grupos econômicos",
      nome="Tabela mestre — Empresas, Grupos e Clusters (produto da pesquisa)",
      autor="elaboração do autor", edicao=AC + " — ver ressalva",
      periodo="derivada do recorte CNPJ de mai/2024",
      filtros="327 grupos · 7.681 empresas · 207 clusters (edição de ago/2026); "
              "consórcio (natureza 2151) não é vínculo de controle",
      endereco="produto da pesquisa",
      script="identificacao_componentes_medios_grandes_v4 · cruzar_operador_grupo.py",
      arquivos=["/03 - Dados/Tabela mestre - Empresas, Grupos e Clusters (ago-2026).xlsx",
                "/03 - Dados/Tabela mestre - Empresas, Grupos e Clusters (v5, 17-10-2026).xlsx"],
      obs="🚨 **Há duas edições no cofre e as instruções do projeto declaram vigente a de "
          "ago/2026 (12/08/2026), enquanto existe uma v5 de 17/10/2026.** Decidir qual é a "
          "canônica antes de citar número de grupo, e registrar a decisão no "
          "[[Registro de alterações pós-congelamento]]. Enquanto isso, a edição citada no "
          "texto tem de vir com data. ⚠️ Pendência aberta nas instruções: 13.570 × 13.569 "
          "sócios distintos (recontagem da r38) — resolver antes de citar."),

 dict(bloco="Finanças municipais",
      nome="FINBRA — Finanças do Brasil, Declaração de Contas Anuais (DCA), anexos I-D e I-E",
      autor="BRASIL. Tesouro Nacional (Siconfi)", edicao="DCA, consulta de 18/07/2026",
      periodo="2019–2023 (receitas e despesas)",
      filtros="todos os municípios declarantes (~5.555 de 5.570, 26 UFs); anexos I-D "
              "(despesa por função) e I-E (despesa por natureza)",
      endereco="API Siconfi — https://apidatalake.tesouro.gov.br/ords/siconfi/tt "
               "(docs em /docs/siconfi/)",
      script="baixar_finbra_siconfi.py",
      arquivos=["FINBRA_nacional/finbra_receitas_2019.csv",
                "FINBRA_nacional/finbra_receitas_2023.csv"],
      obs="🔴 **'Siconfi' aparece 0 vez no texto dos capítulos** e não tem entrada na "
          "bibliografia, embora o FINBRA alimente o Cap. 8. ⚠️ Lacuna declarada no "
          "`metadados.csv`: o anexo de **Despesas por Função 2019–2023 NÃO foi coletado**. "
          "⚠️ Substitui o recorte SP+PA truncado do banco da POLO, que é superado."),
 dict(bloco="Finanças municipais",
      nome="Cota-Parte do Fundo de Participação dos Municípios (FPM) — contas do Siconfi",
      autor="BRASIL. Tesouro Nacional (Siconfi)", edicao=AC + " — data da consulta",
      periodo="2019–2025",
      filtros="contas 1.7.1.1.51.0.0 (2022–2025, total) e 1.7.1.8.01.2/3/4 (2019–2021, "
              "somadas); líquido = bruto − dedução do FUNDEB",
      endereco="API Siconfi (mesma da entrada acima)", script="enriquecer_base_fpm.py",
      arquivos=["Base Municipal v3/contas_alvo_siconfi_v2_2019_2025.csv"],
      obs="A dedução do FUNDEB tem mediana 0,183 do bruto (p5–p95 0,178–0,185) — é a regra "
          "constitucional aparecendo no dado, e por isso é a única subtraída. 23 "
          "município-ano com declaração inconsistente ficam **vazios**, não zero."),

 dict(bloco="Mobilidade e transporte",
      nome="PEMOB — Pesquisa Nacional de Mobilidade Urbana (bases municipais)",
      autor="BRASIL. Ministério das Cidades / SIMU", edicao="edições 2018 a 2024",
      periodo="2016–2024 (tarifa) · 2018–2024 (painel)",
      filtros="tabulação própria por edição", endereco=AC, script="baixar_simu.py",
      arquivos=["PEMOB/Pemob2019_Municipal.xlsx", "PEMOB/BancodeDados_PemobMunicipal_2020.xlsx"],
      obs="⚠️ **Correção registrada em 22/07/2026:** `serie_tarifa.csv` e `serie_pemob.csv` "
          "são PEMOB/Ministério das Cidades, **não ANTP** — atribuí-los à ANTP era erro, "
          "já corrigido no `metadados.csv`."),
 dict(bloco="Mobilidade e transporte",
      nome="SIMOB/ANTP — Sistema de Informações da Mobilidade Urbana, série histórica de tarifas",
      autor="ANTP — Associação Nacional de Transportes Públicos",
      edicao="relatórios gerais 2018, 2023 e 2024 + planilha de tarifas 2005–atual",
      periodo="2005–2017 (tarifa, única fonte anterior a 2016)",
      filtros="extração de PDF", endereco=AC + " — página da ANTP; o PDF não traz URL estável",
      script="baixar_pdfs_antp_por_csv.py",
      arquivos=["SIMOB-ANTP/copia-de-tarifas_2005-a-atual-1.pdf",
                "SIMOB-ANTP/simob-2023-final.pdf", "SIMOB-ANTP/simob-2024-final.pdf"],
      obs="Os **relatórios** já estão citados na bibliografia como @techreport "
          "(`antp-associacaonacionaldetransportespublicos2018/2026/2026a`); a **série de "
          "tarifas extraída do PDF**, não. No painel reconciliado a prioridade é "
          "PEMOB > SIMU > ANTP quando o mesmo município-ano aparece em mais de uma."),
 dict(bloco="Mobilidade e transporte",
      nome="SIMU — Acidentes de Transportes (óbitos e feridos por modo)",
      autor="BRASIL. Ministério das Cidades / SIMU", edicao=AC,
      periodo="2010–2019", filtros="9 categorias de vítima; integrado o corte de 2019",
      endereco=AC, script="baixar_sinistralidade_datasus.py · enriquecer_base_sinistralidade_modo.py",
      arquivos=["SIMU/feridos/simu-feridos-mun-T.csv", "SIMU/mortes/simu-mortes-mun-T.csv"],
      obs="A soma dos 9 modos fecha com o total da fonte em 5.570/5.570 (resíduo zero). "
          "Zero ocupante de ônibus ferido é **medida apurada**, não lacuna."),
 dict(bloco="Mobilidade e transporte",
      nome="Frota de veículos por município e tipo",
      autor="BRASIL. Senatran (ex-DENATRAN)", edicao=AC + " — mês de referência",
      periodo="2013–2025", filtros="frota total, automóvel, motocicleta, ônibus",
      endereco=AC, script="", arquivos=["DENATRAN/serie_taxa_motorizacao_brasil_2013-2025.csv"],
      obs="Parte da série veio do banco da POLO como repositório intermediário — "
          "**citar pela fonte original (Senatran), não pela POLO**. ⚠️ Validar contra a "
          "fonte oficial antes de citar: a cópia da POLO tem truncamento documentado."),
 dict(bloco="Mobilidade e transporte",
      nome="Série Histórica de Levantamento de Preços de Combustíveis",
      autor="BRASIL. ANP — Agência Nacional do Petróleo, Gás Natural e Biocombustíveis",
      edicao=AC + " — data da consulta", periodo="2004–2024 (anual, Brasil)",
      filtros="óleo diesel; preço nominal e deflacionado para 2024",
      endereco=AC + " — a série tem página própria na ANP; registrar a URL do arquivo",
      script="extrair_diesel_anp.py",
      arquivos=["Base Municipal v3/diesel_anp_real_2004_2024.csv"],
      obs="É uma das três que a crítica nomeia como citadas só pelo portal. O "
          "`metadados.csv` **já nomeia a série exata**; falta a entrada bibliográfica e a "
          "URL do arquivo."),

 dict(bloco="IBGE",
      nome="Censo Demográfico 2022 — Microdados da Amostra (acesso controlado)",
      autor="IBGE", edicao="divulgação de set/2026 (download de 08/09/2026)",
      periodo="2022",
      filtros="tabela Domicílios (D0080 município, D0111 peso, D0150 moradores, "
              "D0360 rendimento domiciliar per capita) e tabela Pessoas",
      endereco="acesso controlado mediante termo de compromisso assinado; não redistribuível",
      script="calcular_gini_censo2022.py · agregar_microdados_censo2022.py",
      arquivos=[],
      obs="🔴 **Restrição de replicação:** os arquivos de acesso controlado **não entram no "
          "pacote de replicação**. O que se deposita é o script e o agregado municipal. "
          "Declarar isso no apêndice de reprodutibilidade."),
 dict(bloco="IBGE",
      nome="MUNIC — Pesquisa de Informações Básicas Municipais, bloco Transporte",
      autor="IBGE", edicao="edições 2012, 2017 e 2020",
      periodo="2012 · 2017 · 2020", filtros="bloco Transporte (MTRA1911-1915)",
      endereco=AC, script="", arquivos=["MUNIC/Base_MUNIC_2017_xls.zip", "MUNIC/base_MUNIC_xls_2012.zip"],
      obs="MUNIC é **autodeclarada** pela prefeitura. Nunca misturar as colunas MUNIC com as "
          "colunas documentais da base-mestre — ver [[MUNIC x levantamento documental (24-09-2026)]]."),
 dict(bloco="IBGE",
      nome="REGIC 2018 — Regiões de Influência das Cidades",
      autor="IBGE", edicao="2018 (download de 20/07/2026)", periodo="2018",
      filtros="hierarquia urbana e arranjos populacionais", endereco=AC,
      script="baixar_regic_2018.py",
      arquivos=["REGIC/REGIC2018_Municipios_Hierarquia_e_regiao.xlsx",
                "REGIC/REGIC2018_Arranjos_Populacionais_v2.xlsx"],
      obs=""),

 dict(bloco="Trabalho e empresas",
      nome="RAIS — Relação Anual de Informações Sociais, arquivo de Estabelecimentos",
      autor="BRASIL. Ministério do Trabalho e Emprego (PDET)",
      edicao="anos-base 2022 e 2024 (download de 24–25/07/2026)",
      periodo="2022 e 2024",
      filtros="agregação por município × CNAE × porte; núcleo 4921-3/01 e /02 separado "
              "da expansão 4922/4929",
      endereco="FTP público ftp.mtps.gov.br/pdet/microdados/RAIS/<ano>/",
      script="agregar_rais_estabelecimentos.py",
      arquivos=["RAIS/dados brutos/RAIS_ESTAB_PUB.7z",
                "RAIS/rais_estabelecimentos_por_municipio.csv"],
      obs="🔴 **Os microdados públicos de RAIS e Novo CAGED não trazem CNPJ** — é política "
          "declarada (Comunicado MTPS 192/12, Nota Técnica 088/12), não lacuna acidental. "
          "Servem para agregado municipal, **nunca** para amarrar estabelecimento a empresa "
          "nomeada; para isso só a base de CNPJ. ⚠️ A RAIS tradicional terminou no ano-base "
          "2021; a série 2022+ vem do eSocial, metodologia diferente — não comparar os dois "
          "lados sem nota."),
 dict(bloco="Trabalho e empresas",
      nome="Cadastro Único — agregados municipais",
      autor="BRASIL. MDS / SAGI", edicao="extrações 202209 e 202508",
      periodo="set/2022 e ago/2025", filtros="faixas de pobreza e extrema pobreza, famílias e pessoas",
      endereco="API MI Social (SAGI)", script="",
      arquivos=["Base Municipal v3/cadunico_202209.csv", "Base Municipal v3/cadunico_202508.csv"],
      obs="⚠️ As faixas de pobreza e extrema pobreza são **disjuntas** na fonte "
          "(extrema > pobreza em 4.773 de 5.570 municípios) — somá-las duplica."),

 dict(bloco="Outras",
      nome="Malha municipal digital do Brasil",
      autor="IBGE", edicao="2022", periodo="2022",
      filtros="BR_Municipios_2022 e BR_UF_2022; SIRGAS 2000 / EPSG:4674",
      endereco=AC, script="", arquivos=[],
      obs="Base cartográfica do Cap. 8."),
 dict(bloco="Outras",
      nome="Resultados eleitorais municipais",
      autor="BRASIL. TSE", edicao="eleição de 2024", periodo="2024",
      filtros="candidatos a prefeito; incumbência", endereco=AC, script="baixar_tse_2024.py",
      arquivos=["Base Municipal v3/candidatos_prefeito_tse_2024.csv"],
      obs="Série 2000–2020 veio do banco da POLO como repositório intermediário — citar TSE."),
 dict(bloco="Outras",
      nome="OpenStreetMap — malha viária e rede de ônibus",
      autor="OpenStreetMap contributors (extrato Geofabrik)",
      edicao="extrato de 2026", periodo="mapeamento corrente em 2026",
      filtros="vias motorizadas, ciclovia, pedestre; relações de rota de ônibus",
      endereco=AC + " — registrar a data do extrato Geofabrik",
      script="calcular_osm_viario_onibus_ciclo.py", arquivos=["Base Municipal v3/osm_viario_onibus_ciclo.csv"],
      obs="🔴 **Não usar a contagem de rotas do OSM como número de linhas do sistema.** "
          "Teste de 21/09/2026 em 35 municípios com os dois valores: r = 0,117, e o OSM dá "
          "**zero em 89% deles**; 3.036 municípios do país têm mais de 20 ônibus "
          "registrados e nenhuma rota mapeada. Onde é mapeado, o OSM conta `route` "
          "(variantes de itinerário), não `route_master` (a linha). Foi por medida parecida "
          "que as variáveis de OSM saíram das fichas em 16/09/2026."),
 dict(bloco="Outras",
      nome="Tarifa zero nas cidades do Brasil",
      autor="NTU — Associação Nacional das Empresas de Transportes Urbanos",
      edicao="3ª edição, 10/06/2026", periodo="levantamento até jun/2026",
      filtros="143 municípios e 8 reversões, no critério da própria NTU",
      endereco=AC, script="", arquivos=[],
      obs="**Dado de fonte citada, não da pesquisa.** Preservar os números da NTU (143 e 8) "
          "e nunca misturá-los com os 186/180/174 da base própria. ⚠️ O relatório diário "
          "interno da NTU (168) **não é citável**."),
]

CAB_TABELA = ("| base | edição/versão | período | extração | endereço |\n"
              "|---|---|---|---|---|")


def hum(n):
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024 or u == "GB":
            return f"{n:.0f} {u}" if u == "B" else f"{n:,.1f} {u}".replace(",", ".")
        n /= 1024.0


LIMITE_HASH = 200 * 1024 ** 2   # 200 MB


def evidencia(padrao):
    """Nome, tamanho, mtime e SHA-256 curto de cada arquivo que o glob encontrar.

    ⚠️ Acima de 200 MB o hash é **parcial** — primeiros e últimos 8 MB mais o
    tamanho — e sai rotulado como tal. Os brutos do CNPJ somam ~1,6 GB, e hashear
    tudo a cada execução transformaria um registro de conferência rotineira em
    algo que ninguém roda. Hash parcial detecta substituição e truncamento, não
    adulteração no miolo: por isso é declarado, e não disfarçado de integral."""
    base = RAIZ if padrao.startswith("/") else DATA
    alvo = os.path.join(base, padrao.lstrip("/"))
    out = []
    for p in sorted(glob.glob(alvo)):
        if not os.path.isfile(p):
            continue
        tam = os.path.getsize(p)
        h = hashlib.sha256()
        parcial = tam > LIMITE_HASH
        with open(p, "rb") as f:
            if parcial:
                h.update(f.read(8 << 20))
                f.seek(-(8 << 20), os.SEEK_END)
                h.update(f.read())
                h.update(str(tam).encode())
            else:
                for bloco in iter(lambda: f.read(1 << 20), b""):
                    h.update(bloco)
        out.append({"arquivo": os.path.relpath(p, base), "tamanho": tam,
                    "mtime": datetime.date.fromtimestamp(os.path.getmtime(p)),
                    "sha": h.hexdigest()[:16], "parcial": parcial})
    return out


def url_do_script(nome):
    """Extrai do script de coleta a primeira URL do cabeçalho — é o 'procedimento
    de obtenção' que a crítica pede, e ele já está escrito ali."""
    for parte in re.split(r"[·\n]", nome or ""):
        parte = parte.strip()
        if not parte.endswith(".py"):
            continue
        p = os.path.join(SCRIPTS, parte)
        if not os.path.exists(p):
            continue
        txt = open(p, encoding="utf-8", errors="replace").read(4000)
        m = re.search(r"https?://[^\s'\")]+", txt)
        if m:
            return parte, m.group(0)
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gravar", action="store_true")
    a = ap.parse_args()
    if not os.path.isdir(DATA):
        sys.exit(f"🔴 não achei {DATA}")
    hoje = datetime.date.today().strftime("%d/%m/%Y")

    fichas, faltas, sem_arquivo = [], 0, []
    for f in FONTES:
        ev = []
        for g in f["arquivos"]:
            ev += evidencia(g)
        if f["arquivos"] and not ev:
            sem_arquivo.append(f["nome"])
        f["_ev"] = ev
        f["_script_url"] = url_do_script(f.get("script", ""))
        # 🪤 Armadilha real: download por FTP ou cópia com `-p` PRESERVA o mtime da
        # origem, e aí o arquivo mais parece ter entrado no acervo na data em que a
        # fonte o publicou. A RAIS é o caso: o .7z tem mtime de 13/05/2026, mas o
        # download foi em 24-25/07/2026. Onde a ficha declara a data de consulta,
        # ela prevalece sobre o mtime — e a divergência fica impressa, não some.
        campo = f"{f.get('edicao','')} {f.get('endereco','')}"
        # Procura a data só quando o texto diz que ela É de consulta/download; dentro
        # disso pega a ÚLTIMA (em "download de 24–25/07/2026" a data completa é a
        # segunda). Sem a palavra-chave, não se adivinha: fica o mtime.
        decl = (re.findall(r"\d{2}[/-]\d{2}[/-]\d{4}", campo)
                if re.search(r"download|consulta|extra[çc][ãa]o", campo, re.I) else [])
        mt = min((e["mtime"] for e in ev), default=None)
        if decl:
            f["_extracao"] = decl[-1].replace("-", "/")
            f["_divergencia"] = (mt.strftime("%d/%m/%Y")
                                 if mt and mt.strftime("%d/%m/%Y") != f["_extracao"]
                                 else None)
        else:
            f["_extracao"] = mt.strftime("%d/%m/%Y") if mt else AC
            f["_divergencia"] = None
        faltas += sum(1 for c in ("edicao", "periodo", "filtros", "endereco")
                      if AC in (f.get(c) or ""))
        fichas.append(f)

    L = ["---", 'title: "Registro de fontes de dados"', "tags:", "  - dados", "  - metodo",
         "  - fontes", "publish: true", f"created: {datetime.date.today():%Y-%m-%d}", "---", "",
         "# Registro de fontes de dados", "",
         "> [!info] O que é, e por que existe",
         "> Identificação de cada base que sustenta **tabela, figura ou modelo** da tese "
         "pelos seis campos que permitem reproduzir a consulta: **nome exato da base ou "
         "tabela · edição ou versão · período dos dados · data de extração · filtros "
         "aplicados · endereço ou procedimento de obtenção**. Responde ao item 8 da crítica "
         "externa: para dado que sustenta modelo, a página inicial da instituição não "
         "permite refazer a consulta.", "",
         "> [!warning] Como ler a data de extração",
         "> A data e o SHA-256 de cada arquivo são **lidos do próprio arquivo a cada "
         "execução deste registro**, não digitados. A data é a de entrada do arquivo no "
         "acervo, que **não é necessariamente a data do recorte da fonte** — onde as duas "
         "diferem, a ficha declara as duas. Um arquivo que mude sem aviso aparece como "
         "mudança de hash.", "",
         f"> [!note] Campos ainda sem confirmação: **{faltas}**",
         f"> Marcados `{AC}`. São, na maioria, a URL exata do arquivo e a data da consulta — "
         "o que o cofre não registrou na coleta. Preencher exige voltar à fonte, não inferir. "
         "**NA ≠ 0 vale para metadado como vale para dado.**", "",
         f"_Gerado por `_meta/scripts/gerar_registro_fontes.py` em {hoje}._", "",
         "## Quadro-resumo", "", CAB_TABELA]

    for f in fichas:
        ext = f["_extracao"]
        end = f["endereco"].split(" (")[0].split(" — ")[0]
        L.append(f"| {f['nome'][:58]} | {f['edicao'][:30]} | {f['periodo'][:24]} | "
                 f"{ext} | {end[:52]} |")

    blocos = []
    for f in fichas:
        if f["bloco"] not in blocos:
            blocos.append(f["bloco"])
    for b in blocos:
        L += ["", f"## {b}", ""]
        for f in [x for x in fichas if x["bloco"] == b]:
            L += [f"### {f['nome']}", ""]
            L.append(f"- **Autoria / instituição:** {f['autor']}")
            L.append(f"- **Edição ou versão:** {f['edicao']}")
            L.append(f"- **Período dos dados:** {f['periodo']}")
            L.append(f"- **Data de extração:** {f['_extracao']}"
                     + (f" ⚠️ — o arquivo no acervo tem data de modificação "
                        f"**{f['_divergencia']}**, anterior à consulta: o download "
                        "preservou o carimbo da origem. **Vale a data da consulta.**"
                        if f["_divergencia"] else ""))
            L.append(f"- **Filtros aplicados:** {f['filtros']}")
            L.append(f"- **Endereço ou procedimento:** {f['endereco']}")
            s, u = f["_script_url"]
            if f.get("script"):
                L.append(f"- **Script de coleta/processamento:** `{f['script']}`"
                         + (f" — endpoint declarado no próprio script: {u}" if u else ""))
            if f["_ev"]:
                L.append("- **Arquivos no acervo** (data de entrada e SHA-256 lidos na "
                         "geração deste registro):")
                for e in f["_ev"]:
                    L.append(f"    - `{e['arquivo']}` · {hum(e['tamanho'])} · "
                             f"{e['mtime']:%d/%m/%Y} · `{e['sha']}`"
                             + (" ⚠️ hash **parcial** (arquivo acima de 200 MB: "
                                "início + fim + tamanho)" if e["parcial"] else ""))
                shas = {e["sha"] for e in f["_ev"]}
                if len(f["_ev"]) > 1 and len(shas) == 1:
                    L.append("    - ✅ **Todos os arquivos acima têm o mesmo SHA-256: é um "
                             "objeto só, com nomes diferentes.**")
            elif f["arquivos"]:
                L.append("- **Arquivos no acervo:** ⚠️ os caminhos declarados não foram "
                         "encontrados nesta execução — conferir antes de citar.")
            if f["obs"]:
                L.append(f"- **Ressalva de uso:** {f['obs']}")
            L.append("")

    L += ["## O que este registro não resolve", "",
          "- **Entrada bibliográfica.** Nenhuma destas bases tem entrada `@dataset` em "
          "`biblioteca.bib` (783 `@article`, 456 `@misc`, 173 `@techreport`, **0 "
          "`@dataset`**). O arquivo `Bases de dados.ris` que o [[Mapa de Dados]] anuncia "
          "**não existe mais** no cofre — a referência está morta e precisa ser refeita ou "
          "retirada.",
          "- **Siconfi não aparece no texto.** Zero menção nos capítulos, embora o FINBRA "
          "alimente o Cap. 8.",
          "- **Despesas por Função (Siconfi, 2019–2023)** segue **não coletada**, conforme "
          "declarado no `metadados.csv`.",
          "- **Duas edições vivas da Tabela mestre de grupos** (ago/2026 e v5 de 17/10/2026) "
          "— decidir a canônica antes de citar número de grupo.", "",
          "## Ligações",
          "- [[Mapa de Dados]] · [[Congelamento da base — 11-10-2026]] · "
          "[[Registro de alterações pós-congelamento]] · [[Metodologia]] · "
          "[[Banco Municipal v3 — arquitetura, fontes e metadados]]", "",
          "---", "", "**Autor:** Thiago Von Zeidler Gomes  ",
          "**Orientadora:** Prof.ª Dra. Silvana Zioni", ""]

    novo = "\n".join(L)
    print(f"{len(fichas)} bases · {sum(len(f['_ev']) for f in fichas)} arquivos com hash "
          f"· {faltas} campos {AC}")
    if sem_arquivo:
        print("⚠️ bases cujos caminhos declarados não existem:")
        for n in sem_arquivo:
            print(f"   {n}")
    antigo = open(SAIDA, encoding="utf-8").read() if os.path.exists(SAIDA) else ""
    if novo == antigo:
        print("sem alteração (idempotente).")
        return
    if not a.gravar:
        print(f"\n{len(antigo)} → {len(novo)} caracteres. Nada escrito. Para aplicar: --gravar")
        return
    if antigo:
        bk = SAIDA + ".BACKUP-" + datetime.datetime.now().strftime("%Y%m%d-%H%M") + ".md"
        shutil.copy2(SAIDA, bk)
        print(f"backup: {os.path.basename(bk)}")
    open(SAIDA, "w", encoding="utf-8").write(novo)
    print(f"✅ {SAIDA}")


if __name__ == "__main__":
    main()
