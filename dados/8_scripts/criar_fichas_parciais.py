#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""criar_fichas_parciais.py — cria as fichas que faltavam nas camadas parciais
(2a temporal-dias, 3 espacial, 4 grupo social) da régua descritiva.

Escopo declarado: a camada 2b (eventos/eleitoral, 324 casos) NÃO recebe ficha.
Gratuidade de um dia de eleição é evento, não caso municipal — fica na lista.

Só grava se o arquivo não existir ou estiver vazio. Nunca sobrescreve conteúdo.
USO: python3 _meta/scripts/criar_fichas_parciais.py
"""
import io, os, sys

R = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DIR = os.path.join(R, "04 - Análises", "Casos municipais", "Fichas por município")
LIG = ("## Ligações\n- [[Tabela consolidada - Municípios com Tarifa Zero]] · "
       "[[Tipologias de Tarifa Zero (4 camadas)]] · [[Fichas por município - MOC]]\n")

def montar(nome, uf, regiao, ibge, camada, tipol, briefing, dados, biblio, materias, legis):
    fm = (f'---\ntitle: "Ficha - {nome} ({uf})"\ntags:\n  - análise\n  - caso\n  - tarifa-zero\n'
          f'municipio: {nome}\nuf: {uf}\nregiao: {regiao}\ncodigo_ibge: {ibge}\n'
          f'camada: {camada}\ntipologia_analitica: {tipol}\npublish: false\ncreated: 2026-09-03\n---\n\n')
    return fm + (f"# 🏙️ {nome} — {uf} · Ficha de Tarifa Zero\n\n"
                 f"## 1. Briefing\n{briefing}\n\n"
                 f"## 2. Principais dados\n{dados}\n\n"
                 f"## 3. Bibliografia — em quais fontes o caso aparece\n{biblio}\n\n"
                 f"## 4. Matérias de jornais\n{materias}\n\n"
                 f"## 5. Legislação\n{legis}\n\n" + LIG)

NA = "não aplicável (TZ parcial — fora do escopo da régua analítica de TZ universal)"

FICHAS = [
 dict(nome="Duque de Caxias", uf="RJ", regiao="Sudeste", ibge=3301702,
   camada="espacial (periférico)", tipol=NA,
   briefing=(
    "Duque de Caxias (RJ) opera o **Programa Tarifa Zero** como gratuidade **espacialmente delimitada**: a "
    "**Lei nº 3.589/2026, art. 1º, §1º**, restringe expressamente o programa às áreas do município **não "
    "atendidas integralmente por linhas regulares de concessão pública**. ✅ **Coexiste com o sistema pago "
    "concessionado** — é a camada 3 da régua descritiva, não TZ universal.\n\n"
    "🚨 **Caso atípico de escala, e é por isso que ele importa** (decisão do autor, 21/08/2026): o escopo legal é "
    "**idêntico ao de Magé e Santo André** — gratuidade só fora da área concessionada —, mas em escala municipal "
    "muito maior: **20 linhas cobrindo os 4 distritos**, contra **1 linha** nos outros casos desta camada. "
    "➡️ **Considerar tratamento textual à parte no [[Cap 5 - Panorama Nacional da Tarifa Zero]] e no "
    "[[Cap 8 - Inovação e Resistência]].**\n\n"
    "⚠️ **E é o caso que expõe o limite da régua descritiva.** Um município de **808 mil habitantes** com 20 linhas "
    "gratuitas em 4 distritos é, em volume absoluto de oferta gratuita, maior que a maioria dos 176 universais — que "
    "são de pequeno e médio porte. 🔴 **A camada mede o *escopo jurídico* da gratuidade, não a sua magnitude.** "
    "Classificar Duque de Caxias na mesma célula de um caso de 1 linha é correto pela régua e enganoso pelo tamanho. "
    "**É um argumento a favor de a régua ganhar um eixo de magnitude** — sugestão a revisar, não decisão tomada.\n\n"
    "🔴 **Leitura a testar, não a afirmar:** a lei desenha a gratuidade como **complemento** da concessão, não como "
    "substituição. Se isso se confirmar, Duque de Caxias é o caso mais nítido de **convivência negociada** entre "
    "gratuidade pública e operação privada concedida — e um contraexemplo direto à leitura de que a TZ avança contra "
    "o operador. ⚠️ **Antes de usar: ler a lei inteira e o contrato de concessão vigente.**"),
   dados=("- **População (2022):** 808.161\n"
    "- **Situação / modelo / início:** Ativa / parcial (espacial) / **jul/2024** (1ª linha); Lei 3.589 sancionada em **10/06/2026**\n"
    "- **Operador:** — (a levantar; coexiste com consórcio concessionado)\n"
    "- **Motivações:** atender áreas sem cobertura integral de linha regular concedida\n"
    "- **Frota / linhas / demanda:** — / **20 linhas** (4 distritos) / **~442 mil passageiros em pouco mais de 1 ano** (dado oficial da prefeitura)\n"
    "- **% do orçamento:** — (a levantar no SICONFI)\n"
    "- **Site da prefeitura:** https://duquedecaxias.rj.gov.br/"),
   biblio=("- **Aparece em (levantamentos):** funil SICONFI (03/08/2026); incluído na camada 3 por decisão do autor em 21/08/2026 — ver [[Tipologias de Tarifa Zero (4 camadas)]]\n"
    "- ⚠️ **Confiança: alta** — lei confirmada em fonte primária (Câmara Municipal) e dados operacionais oficiais.\n"
    "- 🔴 **Nenhuma literatura acadêmica localizada trata deste caso** — ver a seção \"Literatura da RSL\" abaixo."),
   materias=("- **Prefeitura de Duque de Caxias** — lançamento da 20ª linha do Tarifa Zero: https://duquedecaxias.rj.gov.br/noticia/prefeitura-de-duque-de-caxias-lanca-20%C2%AA-linha-do-tarifa-zero,-ampliando-integracao-e-mobilidade-no-municipio/6452\n"
    "- ⚠️ **A fonte é a própria prefeitura** — números de linhas e de passageiros são autodeclarados. **Buscar cobertura independente antes de citar.**"),
   legis=("- **Norma:** **Lei nº 3.589/2026**, sancionada em 10/06/2026 · confiab.: **alta** (fonte primária)\n"
    "- **Dispositivo decisivo:** art. 1º, §1º — restringe o programa às áreas **não atendidas integralmente por linhas regulares de concessão pública**.\n"
    "- **Fonte primária:** Câmara Municipal de Duque de Caxias — https://www.cmdc.rj.gov.br/?p=32072\n"
    "- ⚠️ **A obter e ler por inteiro:** texto integral da lei e **contrato de concessão vigente**, para saber se a gratuidade foi negociada com o concessionário ou imposta a ele. 🔴 **É a diferença entre convivência e conflito, e a tese não pode supor qual dos dois.**\n"
    "- Análise: [[Análise - Legislação da Tarifa Zero]]")),

 dict(nome="Magé", uf="RJ", regiao="Sudeste", ibge=3302502,
   camada="espacial (periférico)", tipol=NA,
   briefing=(
    "Magé (RJ) opera o **\"Amarelinho\"** — **14 linhas fixas gratuitas diárias** que **não cobrem toda a área do "
    "município**: o consórcio pago segue operando no restante. ✅ **Camada 3 (espacial) da régua descritiva.**\n\n"
    "⚠️ **Reclassificação provisória, a confirmar com o autor** (03/08/2026, funil SICONFI) — **confiança média**. "
    "🔴 **Não usar como caso fechado até a confirmação.**\n\n"
    "🚨 **Por que este caso interessa mais do que o porte sugere:** 14 linhas gratuitas convivendo com um consórcio "
    "pago no mesmo município é a forma mais direta de observar **a fronteira entre o que o capital quer operar e o "
    "que ele deixa de fora**. ➡️ **Se a gratuidade ocupa exatamente as áreas que a concessão não atende, Magé é "
    "evidência espacial da hipótese da tese** — a política floresce onde o interesse comercial não chega, dentro de "
    "um mesmo município. ⚠️ **Isso é hipótese com desenho de teste, não achado:** exige o mapa das 14 linhas contra "
    "o mapa da área concessionada. **Sem os dois mapas, não afirmar.**"),
   dados=("- **População (2022):** 228.127\n"
    "- **Situação / modelo / início:** Ativa / parcial (espacial) / — (a levantar)\n"
    "- **Operador:** — (\"Amarelinho\"; consórcio pago no restante do município)\n"
    "- **Motivações:** — (a levantar)\n"
    "- **Frota / linhas / demanda:** — / **14 linhas fixas diárias** / —\n"
    "- **% do orçamento:** — (a levantar no SICONFI)\n"
    "- **Site da prefeitura:** —"),
   biblio=("- **Aparece em (levantamentos):** funil SICONFI (03/08/2026) — ver [[Tipologias de Tarifa Zero (4 camadas)]]\n"
    "- ⚠️ **Confiança: média** — reclassificação provisória, a confirmar.\n"
    "- 🔴 **Nenhuma literatura acadêmica localizada trata deste caso** — ver a seção \"Literatura da RSL\" abaixo."),
   materias="- ⚠️ **A levantar** — nenhuma matéria registrada nesta ficha.",
   legis=("- **Norma:** — ⚠️ **não localizada.** 🔴 **Enquanto não houver lei ou decreto em fonte primária, o caso segue com confiança média e não deve entrar em contagem apresentada como confirmada.**\n"
    "- Análise: [[Análise - Legislação da Tarifa Zero]]")),

 dict(nome="Parauapebas", uf="PA", regiao="Norte", ibge=1505536,
   camada="grupo social", tipol=NA,
   briefing=(
    "Parauapebas (PA) tem gratuidade **limitada por grupo social**: hoje **estudantes e candidatos de concurso**, pela "
    "**Lei 5.629/2026**. ✅ **Camada 4 da régua descritiva.**\n\n"
    "🚨🚨 **E é o caso mais interessante da camada, porque é o símile inverso de São Caetano do Sul.** A **Lei "
    "5.631/2026** institui universalização **\"gradual\"** — ainda **sem confirmação de vigência** para o público "
    "geral. 🔴 **São Caetano saiu de universal para grupo social; Parauapebas pode estar saindo de grupo social para "
    "universal.** ➡️ **Os dois juntos são o par que a régua descritiva precisa para deixar de ser uma fotografia e "
    "virar uma medida de trajetória** — a mesma célula pode ser ponto de partida ou de chegada.\n\n"
    "⚠️ **Estado provisório, e a ficha registra isso de propósito:** **confiança média, a confirmar**. 🔴 **Caso de "
    "transição legislativa — acompanhar, não tratar como definitivo.** Não contar entre os universais até que a "
    "vigência para o público geral seja confirmada em fonte primária.\n\n"
    "⚠️ **Contexto que a tese precisa registrar, sem transformar em explicação:** Parauapebas é município de mineração "
    "(Carajás), com receita atípica de royalties — o mesmo perfil de Maricá, Mariana e Paulínia. 🔴 **Entra na lista "
    "dos casos onde a rival \"base fiscal extraordinária\" segue aberta**, e não pode ser usado como evidência da "
    "hipótese sem esse controle."),
   dados=("- **População (2022):** 267.836\n"
    "- **Situação / modelo / início:** Ativa / parcial (grupo social) / **2026** (Lei 5.629/2026)\n"
    "- **Operador:** — (a levantar)\n"
    "- **Motivações:** — (a levantar)\n"
    "- **Frota / linhas / demanda:** — / — / —\n"
    "- **% do orçamento:** — (a levantar no SICONFI)\n"
    "- **Site da prefeitura:** —"),
   biblio=("- **Aparece em (levantamentos):** funil SICONFI (03/08/2026) — ver [[Tipologias de Tarifa Zero (4 camadas)]]\n"
    "- ⚠️ **Confiança: média (a confirmar)** — transição legislativa em curso.\n"
    "- 🔴 **Nenhuma literatura acadêmica localizada trata deste caso** — ver a seção \"Literatura da RSL\" abaixo."),
   materias="- ⚠️ **A levantar** — nenhuma matéria registrada nesta ficha.",
   legis=("- **Norma vigente:** **Lei 5.629/2026** — gratuidade para estudantes e candidatos de concurso · confiab.: **média**\n"
    "- **Norma a acompanhar:** **Lei 5.631/2026** — institui universalização **\"gradual\"**. 🔴 **Vigência para o público geral NÃO confirmada.**\n"
    "- ➡️ **Pendência:** obter o texto integral das duas leis em fonte primária (portal de legislação municipal ou Câmara) e datar o início da vigência. **É o que decide se Parauapebas migra para a camada 1.**\n"
    "- Análise: [[Análise - Legislação da Tarifa Zero]]")),

 dict(nome="Embu das Artes", uf="SP", regiao="Sudeste", ibge=3515004,
   camada="temporal (dias)", tipol=NA,
   briefing=(
    "Embu das Artes (SP) tem gratuidade **temporalmente limitada**: **fins de semana e feriados**. ✅ **Camada 2a da "
    "régua descritiva.** Município da **Região Metropolitana de São Paulo**.\n\n"
    "⚠️ **Registro novo e ainda magro** (funil SICONFI, 03/08/2026): **sem data de início, sem norma localizada, sem "
    "programa nomeado**. 🔴 **Confiança baixa — não citar como caso confirmado.**\n\n"
    "🚨 **Mas a localização é o que faz este caso valer o esforço de confirmar:** é um dos poucos registros de "
    "gratuidade, ainda que parcial, **dentro da RMSP** — a região onde a tese afirma que os grupos econômicos "
    "restringem a difusão da Tarifa Zero. ➡️ **Se confirmado, é um teste direto da hipótese na sua área mais "
    "sensível:** por que a gratuidade na RMSP aparece **só nos dias em que o sistema opera com menor demanda "
    "comercial**? ⚠️ **A pergunta é boa; a resposta exige o dado, e o dado ainda não existe nesta ficha.**\n\n"
    "⚠️ **Divergência de nome a resolver:** a Base Municipal v3 registra o município como **\"Embu\"** (grafia "
    "anterior a 2011); o nome oficial é **Embu das Artes**. 🔴 **Isso quebra o casamento automático dos scripts por "
    "nome — corrigir no dicionário de bridge, como já foi feito para \"Artur/Arthur Nogueira\".**"),
   dados=("- **População (2022):** 250.691\n"
    "- **Situação / modelo / início:** NOVO / parcial (temporal — fins de semana e feriados) / — ⚠️ **sem data**\n"
    "- **Operador:** — (a levantar)\n"
    "- **Motivações:** — (a levantar)\n"
    "- **Frota / linhas / demanda:** — / — / —\n"
    "- **% do orçamento:** — (a levantar no SICONFI)\n"
    "- **Site da prefeitura:** —"),
   biblio=("- **Aparece em (levantamentos):** funil SICONFI (03/08/2026) — ver [[Tipologias de Tarifa Zero (4 camadas)]]\n"
    "- ⚠️ **Confiança: baixa** — sem norma, sem data, sem programa nomeado.\n"
    "- 🔴 **Nenhuma literatura acadêmica localizada trata deste caso** — ver a seção \"Literatura da RSL\" abaixo."),
   materias="- ⚠️ **A levantar** — nenhuma matéria registrada nesta ficha.",
   legis=("- **Norma:** — ⚠️ **não localizada.** ➡️ **Buscar no portal de legislação municipal e na Câmara de Embu das Artes.** 🔴 **Sem norma, o caso não deve constar de contagem apresentada como confirmada.**\n"
    "- Análise: [[Análise - Legislação da Tarifa Zero]]")),

 dict(nome="Andrelândia", uf="MG", regiao="Sudeste", ibge=3102803,
   camada="temporal (dias)", tipol=NA,
   briefing=(
    "Andrelândia (MG) tem gratuidade **temporalmente limitada** a **um único dia da semana: terças-feiras**. ✅ "
    "**Camada 2a da régua descritiva.** Município de **11.927 habitantes**, não capital.\n\n"
    "⚠️ **Registro novo e magro** (funil SICONFI, 03/08/2026): **sem data de início, sem norma localizada, sem "
    "programa nomeado**. 🔴 **Confiança baixa — não citar como caso confirmado.**\n\n"
    "🚨 **O caso é o extremo inferior da régua, e serve de fronteira conceitual.** Gratuidade em **um dia por semana** "
    "está no limite do que a categoria \"Tarifa Zero\" comporta: ⚠️ **é a mesma família da gratuidade eleitoral de um "
    "dia (camada 2b), não a da gratuidade universal.** ➡️ **Vale como pergunta explícita ao critério: qual é o piso "
    "de cobertura temporal abaixo do qual a política deixa de ser Tarifa Zero e passa a ser desconto promocional?** "
    "🔴 **A régua descritiva ainda não responde a isso** — e Andrelândia é o caso que obriga a resposta, junto com a "
    "pendência de cobertura horária levantada em Monte Carmelo (universal quanto ao público, mas sem operação em "
    "domingos, feriados e de 20/12 a 05/02).\n\n"
    "⚠️ **A terça-feira também pede explicação:** não é dia de pico nem fim de semana. **Feira livre? Dia de "
    "atendimento em saúde? Não sei, e a ficha não deve fingir que sei.** ➡️ **Levantar antes de interpretar.**"),
   dados=("- **População (2022):** 11.927\n"
    "- **Situação / modelo / início:** NOVO / parcial (temporal — só terças-feiras) / — ⚠️ **sem data**\n"
    "- **Operador:** — (a levantar)\n"
    "- **Motivações:** — (a levantar) ⚠️ **a hipótese de dia de feira ou de atendimento em saúde é conjectura do assistente, não dado**\n"
    "- **Frota / linhas / demanda:** — / — / —\n"
    "- **% do orçamento:** — (a levantar no SICONFI)\n"
    "- **Site da prefeitura:** —"),
   biblio=("- **Aparece em (levantamentos):** funil SICONFI (03/08/2026) — ver [[Tipologias de Tarifa Zero (4 camadas)]]\n"
    "- ⚠️ **Confiança: baixa** — sem norma, sem data, sem programa nomeado.\n"
    "- 🔴 **Nenhuma literatura acadêmica localizada trata deste caso** — ver a seção \"Literatura da RSL\" abaixo."),
   materias="- ⚠️ **A levantar** — nenhuma matéria registrada nesta ficha.",
   legis=("- **Norma:** — ⚠️ **não localizada.** ➡️ **Buscar no portal de legislação municipal e na Câmara de Andrelândia.** 🔴 **Sem norma, o caso não deve constar de contagem apresentada como confirmada.**\n"
    "- Análise: [[Análise - Legislação da Tarifa Zero]]")),
]

def main():
    os.makedirs(DIR, exist_ok=True)
    for f in FICHAS:
        p = os.path.join(DIR, f"Ficha - {f['nome']} ({f['uf']}).md")
        if os.path.exists(p) and os.path.getsize(p) > 0:
            print("JA EXISTE com conteudo, nao sobrescrito:", os.path.basename(p)); continue
        io.open(p, "w", encoding="utf-8", newline="\n").write(montar(**f))
        print("criada:", os.path.basename(p))

if __name__ == "__main__":
    main()
