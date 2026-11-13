# -*- coding: utf-8 -*-
"""codificar_contrapartida.py — contrapartida em três estados (com · sem · não apurado), regra B.1.3 (decisão do autor, 17/10/2026).
Gera três colunas DERIVADAS na base-mestre a partir da coluna 'Contrapartida' (texto da leitura):
  'Contrapartida — estado'  : com | sem | não apurado
  'Contrapartida — itens'   : C (instância de controle social) · T (transparência de custos ou de dados de operação do programa)
                              · D (exigência de desempenho ou monitoramento) — só quando estado = com
  'Contrapartida — leitura' : por que o caso caiu ali; 'fronteira (a revisar)' marca os casos que pedem decisão do autor
Regra: 'com' = pelo menos um item C, T ou D escrito na norma, no contrato, no termo de referência ou no decreto da política;
'sem' = documento da política lido e nenhum dos três (transparência genérica — Portal, e-SIC, publicação da licitação — não conta);
'não apurado' = documento da política não lido, ou só a estrutura do município na MUNIC (conselho, fundo, plano), que não é a política.
NA ≠ 0: proporções só sobre 'com' + 'sem'. Texto da leitura novo e fora da tabela → 'não apurado — a codificar' (força revisão).
Uso (raiz do cofre): python _meta/scripts/codificar_contrapartida.py [--gravar]
Autor: Thiago Von Zeidler Gomes · Orientadora: Prof.ª Dra. Silvana Zioni"""
import os, re, sys, shutil, datetime, collections, openpyxl
G = "--gravar" in sys.argv
BM = os.path.join("03 - Dados", "_data", "casos por fonte", "Municípios TZ - consolidado.xlsx")
NOVAS = ["Contrapartida — estado", "Contrapartida — itens", "Contrapartida — leitura"]
F = "fronteira (a revisar)"
# (Município, UF): (estado, itens, leitura) — codificação de 17/10/2026 sobre o texto da coluna 'Contrapartida'
TAB = {
 ("Caucaia", "CE"): ("sem", "", F + ": aditivo de 2021 lido sem C, T ou D; o monitoramento por GPS vem da literatura (Baiardi, Zioni e Gomes, 2023), não está escrito no instrumento — a r64 tratou como sem"),
 ("Formosa", "GO"): ("sem", "", "Conselho Diretor do FMTU interno, não participativo — não é instância de controle social; nenhum item T ou D"),
 ("Luziânia", "GO"): ("sem", "", F + ": prestação de contas da beneficiária e critérios no contrato são transparência à Prefeitura, não pública (decisão do autor, 17/10: T só conta se pública)"),
 ("Caeté", "MG"): ("não apurado", "", "só MUNIC 2020"),
 ("Campo Belo", "MG"): ("sem", "", F + ": divulgação de itinerários e devolução em vale-transporte não são C, T ou D"),
 ("Cláudio", "MG"): ("sem", "", "só a publicidade da licitação (transparência genérica)"),
 ("Dores do Indaiá", "MG"): ("sem", "", F + ": fiscalização 'com a cooperação dos usuários', genérica, sem instância"),
 ("Ibirité", "MG"): ("não apurado", "", "só MUNIC 2020; Conselho Diretor não documentado"),
 ("Ijaci", "MG"): ("com", "C T", "Art. 9º: transparência e participação social (consultas públicas, canais)"),
 ("Ituiutaba", "MG"): ("sem", "", F + ": lei lida silente sobre controle social; transparência e desempenho não anotados"),
 ("Mariana", "MG"): ("sem", "", F + ": parecer da Secretaria como condição de pagamento (arts. 10-11) é controle administrativo, como em Tupã (decisão do autor, 17/10: T só conta se pública)"),
 ("Piumhi", "MG"): ("sem", "", F + ": relatórios diários das roletas à Secretaria e publicação no PNCP (genérica) (decisão do autor, 17/10: T só conta se pública)"),
 ("Santana do Deserto", "MG"): ("sem", "", F + ": direito individual de opinar (Decreto, art. 7º, II), sem instância"),
 ("Sarzedo", "MG"): ("sem", "", "não prevista na lei; conselho só na MUNIC"),
 ("São João del Rei", "MG"): ("com", "C T", "Art. 10: transparência e participação social — prevista em lei, não verificada na prática"),
 ("São Lourenço", "MG"): ("não apurado", "", "Conselho Fiscal do Fundo (Lei 3.535/2022, art. 14) com composição não lida (texto truncado), em lei de custeio (decisão do autor, 17/10)"),
 ("Costa Rica", "MS"): ("sem", "", "supervisão pelo Secretário de Governo (art. 6º) — controle interno"),
 ("Sorriso", "MT"): ("sem", "", "nada na lei; conselho só na MUNIC"),
 ("Carambeí", "PR"): ("com", "D", "estudos anuais de continuidade (art. 6º)"),
 ("Cianorte", "PR"): ("com", "C T D", "documentação de custos (art. 5º), GPS (art. 6º), Comitê paritário (arts. 10-12), planilha publicada"),
 ("Clevelândia", "PR"): ("não apurado", "", "só MUNIC 2020"),
 ("Irati", "PR"): ("com", "C", "Concidade (art. 6º) e Comitê Gestor deliberativo (art. 7º)"),
 ("Ivaiporã", "PR"): ("não apurado", "", "só MUNIC 2020"),
 ("Paranaguá", "PR"): ("sem", "", F + ": a transparência mensal dos recursos da TMU (art. 12) foi revogada; não há outro item vigente anotado"),
 ("Pitanga", "PR"): ("não apurado", "", "só MUNIC 2020"),
 ("Quatro Barras", "PR"): ("sem", "", F + ": bilhetagem e contagem de usuários (art. 8º) e fiscalização pela Secretaria (art. 9º) são dados à Prefeitura (decisão do autor, 17/10: T só conta se pública)"),
 ("Rio Branco do Sul", "PR"): ("com", "D", "indicadores de desempenho, utilização e impacto (arts. 14-16)"),
 ("Cantagalo", "RJ"): ("com", "D", F + ": sanções do art. 8º (exigência de desempenho); o relatório mensal à Secretaria (art. 5º) não conta como T (decisão do autor, 17/10: T só conta se pública)"),
 ("Casimiro de Abreu", "RJ"): ("não apurado", "", "só MUNIC 2020"),
 ("Conceição de Macabu", "RJ"): ("sem", "", F + ": art. 72 é salvaguarda fiscal (fonte extratarifária), não C, T ou D"),
 ("Maricá", "RJ"): ("não apurado", "", "controle social do transporte não verificado (Banco Mumbuca é mecanismo correlato)"),
 ("Mendes", "RJ"): ("com", "D", "sistema de monitoramento e avaliação de resultados (art. 4º)"),
 ("São Fidélis", "RJ"): ("não apurado", "", "só MUNIC 2020"),
 ("São João da Barra", "RJ"): ("não apurado", "", "só MUNIC 2020"),
 ("Canoas", "RS"): ("não apurado", "", "só MUNIC 2020; não verificado para a Tarifa Zero"),
 ("Araranguá", "SC"): ("sem", "", "só publicação no Portal da Transparência (genérica)"),
 ("Lauro Müller", "SC"): ("com", "T D", "contabilidade específica, relatórios mensais, auditoria, indicadores (arts. 9º-12); GPS e bilhetagem (arts. 15-17)"),
 ("Agudos", "SP"): ("com", "C", "Conselho Municipal de Transporte e Trânsito, consultivo (Lei 4.581/2014, arts. 44-46), criado pela lei da gratuidade — C consultivo (decisão do autor, 17/10)"),
 ("Alumínio", "SP"): ("com", "T D", "TR de 2026: relatório operacional mensal, indicadores trimestrais, auditoria; o emergencial de 2025 só fiscalizava"),
 ("Cerquilho", "SP"): ("não apurado", "", "só MUNIC 2020"),
 ("Lins", "SP"): ("não apurado", "", "só MUNIC 2020"),
 ("Santo Antônio de Posse", "SP"): ("com", "T", F + ": publicação dos contratos, aditivos e pagamentos do serviço no Portal"),
 ("São Caetano do Sul", "SP"): ("sem", "", "aditivos lidos sem cláusula de transparência, controle social ou desempenho; relatório USCS/SEMOB com independência questionada"),
 ("Tupã", "SP"): ("sem", "", F + ": planilhas técnicas, econômicas e operacionais chanceladas pela Secretaria como condição do pagamento (Lei 5.348/2025, art. 3º) — dados à Prefeitura (decisão do autor, 17/10: T só conta se pública)"),
 ("Vargem Grande Paulista", "SP"): ("sem", "", F + ": nenhuma cláusula de transparência no contrato lido; conselho e fundo só na MUNIC"),
 ("Monte Mor", "SP"): ("sem", "", F + ": Conselho Diretor do FMTU (arts. 8º-9º), controle institucional interno"),
 ("Palmas", "TO"): ("não apurado", "", "só MUNIC 2020"),
 ("Jucás", "CE"): ("sem", "", "só transparência genérica (Portal, e-SIC, Ouvidoria)"),
 ("Centenário do Sul", "PR"): ("sem", "", "fiscalização legislativa e horários publicados — nada escrito na política"),
 ("Lidianópolis", "PR"): ("sem", "", "transparência genérica (Portal, Diário Oficial)"),
 ("Venda Nova do Imigrante", "ES"): ("sem", "", "nada específico ao transporte gratuito"),
 ("Brodowski", "SP"): ("não apurado", "", "não documentada; leituras contraditórias sobre o COMTRANS"),
 ("Pains", "MG"): ("sem", "", "só publicidade da licitação (PNCP)"),
 ("Águas de São Pedro", "SP"): ("sem", "", F + ": Carta de Serviços ao usuário, não C, T ou D"),
 ("São Joaquim da Barra", "SP"): ("sem", "", F + ": subsídio fixado com base nos tacógrafos (Lei 1.364/2023, art. 2º) — dados à Prefeitura (decisão do autor, 17/10: T só conta se pública)"),
 ("Santa Cruz Cabrália", "BA"): ("com", "C T", "Lei 766/2025, art. 9º: transparência de custos e indicadores, participação da sociedade civil — não verificada na prática"),
}
# 21/10/2026 (decisão do autor): contrapartida lida nos atos do acervo (r78c/r78d) — a tabela de decisão completa a TAB;
# 'div' corrige a codificação de 17/10; 'ato_na' (ato ilegível ou que não é o da gratuidade) não sobrepõe a TAB.
import csv as _csv
_DEC = os.path.join("03 - Dados", "_data", "Analises_Cap6", "r78c", "contrapartida_decisao_r78c.csv")
for _d in _csv.DictReader(open(_DEC, encoding="utf-8")):
    _k = (_d["Município"], _d["UF"])
    if _d["tipo"] == "ato_na" and _k in TAB: continue
    TAB[_k] = (_d["estado"], _d["itens"], _d["leitura"])
ND = re.compile(r"^(não apurad|não verificad|não confirmad|não documentad|a verificar|nan$|none$)", re.I)
wb = openpyxl.load_workbook(BM); ws = wb["consolidado"]; H = [c.value for c in ws[1]]
for n in NOVAS:
    if n not in H: ws.cell(1, len(H) + 1).value = n; H.append(n)
I = {h: i + 1 for i, h in enumerate(H)}; iC = I["Contrapartida"]
cont = collections.Counter(); usados = set(); muda = 0
for r in range(2, ws.max_row + 1):
    m, uf = ws.cell(r, 1).value, ws.cell(r, 2).value
    if not m: continue
    txt = str(ws.cell(r, iC).value or "").strip()
    if (m, uf) in TAB: est, it, lei = TAB[(m, uf)]; usados.add((m, uf))
    elif not txt or ND.match(txt): est, it, lei = "não apurado", "", "leitura da política não registrada" if not txt else "registrado como não apurado"
    else: est, it, lei = "não apurado", "", "não apurado — a codificar: texto novo na coluna Contrapartida"
    for n, v in zip(NOVAS, (est, it, lei)):
        if (ws.cell(r, I[n]).value or "") != v: ws.cell(r, I[n]).value = v; muda += 1
    if ws.cell(r, I["Situação"]).value in ("Ativa", "Encerrada"): cont[est] += 1
faltam = set(TAB) - usados
print("em escopo:", dict(cont), "· apurados:", cont["com"] + cont["sem"], "· com/apurados:",
      f"{cont['com']}/{cont['com'] + cont['sem']}", "· células a mudar:", muda, "· chaves sem linha:", sorted(faltam))
assert not faltam
if G and muda:
    bk = os.path.join("_meta", "_backups", "contrapartida-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")); os.makedirs(bk, exist_ok=True)
    shutil.copy2(BM, bk); wb.save(BM); print("gravado", bk)
