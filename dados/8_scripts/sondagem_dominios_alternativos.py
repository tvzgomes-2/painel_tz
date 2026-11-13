#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sondagem_dominios_alternativos.py — testa se câmaras municipais expõem a API
SAPL num domínio diferente do padrão `sapl.<slug>.<uf>.leg.br` já colhido.

CONTEXTO
  A varredura nacional (`sapl_varredura.py`) colheu 850 câmaras no padrão
  `https://sapl.<slug>.<uf>.leg.br/api/norma/normajuridica/`. Dos 177/179
  municípios da camada universal (base-mestre), 138 não resolveram nesse
  padrão. Uma busca dirigida na web (11/09/2026 — ver
  "Descoberta de dominio da camara - 138 municipios sem host SAPL
  (11-09-2026).md", em 04 - Análises/Pesquisa legal/) dividiu esses 138 em
  três grupos: A (12, "parece SAPL"), B (49, outro vendor confirmado por
  evidência) e C (77, sem sinal claro).

  GRUPO A e GRUPO C — ambos já testados (11/09/2026), 218 candidatos / 89
  municípios no total. Resultado real, registrado na nota "Descoberta de
  domínio...": 9 confirmados como SAPL, mas só **1 com normas cadastradas**
  (Arthur Nogueira/SP) — os outros 8 são API funcionando mas vazia. Ainda
  pendentes desta rodada, por causa que não é "não é SAPL" definitivo:
    - SSL (4): Tarumã/SP, Morretes/PR, Santa Isabel/SP, Vargem/SP — use
      `--ignorar-ssl` para decidir se são SAPL atrás de certificado ruim.
    - timeout (2): Silva Jardim/RJ, Costa Rica/MS — pode ser servidor
      lento, não domínio morto; use `--timeout` mais alto para reconferir.
  Ver a nota para o detalhe completo (inclusive dois achados incidentais:
  8 municípios com a mesma plataforma não identificada, 3 com sinal do
  vendor "Legisoft").

  GRUPO B (49, vendor já confirmado por evidência — SISCAM, PortalTP etc.)
  NÃO está neste script — testar o padrão SAPL contra domínios que a própria
  busca já identificou como outro sistema é testar uma hipótese que a
  evidência já descartou. Só entra aqui variante por variante, se houver
  suspeita concreta de grafia (como Arthur→Artur no grupo A).

  ⚠️ RODAR NA SUA MÁQUINA, não em ambiente de nuvem. O proxy de saída do
  ambiente de nuvem onde a busca foi feita bloqueia domínios fora de uma
  lista liberada (confirmado: até hosts .leg.br já colhidos por este mesmo
  projeto voltaram 403 quando testados de lá). A varredura original também
  sempre rodou localmente, pelo mesmo motivo.

USO
  python sondagem_dominios_alternativos.py --grupo a
  python sondagem_dominios_alternativos.py --grupo c
  python sondagem_dominios_alternativos.py --grupo todos
  python sondagem_dominios_alternativos.py --grupo c --saida grupo_c.csv
  python sondagem_dominios_alternativos.py --grupo c --contato seu@email.com

  # reteste dirigido dos pendentes da rodada de 11/09/2026, sem rodar tudo de novo:
  python sondagem_dominios_alternativos.py --grupo todos --ignorar-ssl --filtro "Taruma,Morretes,Santa Isabel,Vargem"
  python sondagem_dominios_alternativos.py --grupo todos --timeout 30 --filtro "Silva Jardim,Costa Rica"

SAÍDA
  Uma linha por candidato no console, e um CSV (padrão:
  sondagem_dominios_alternativos.csv) com município, UF, host testado,
  origem do host (achado/hipótese/já testado), status HTTP, se parece SAPL
  de fato, motivo, e um trecho da resposta para conferência manual.

  Um HTTP 200 cujo corpo comece por `{"count":` ou `{"pagination":` (ou
  contenha "results"/"total_entries") é SAPL confirmado — pode entrar direto
  na lista de descoberta do `sapl_varredura.py` (`descobrir`/`corpus`), sem
  código novo. Corrigido em 11/09/2026: a primeira versão só reconhecia o
  formato clássico do Django REST Framework (`{"count":...}`) e perdeu dois
  casos reais que respondem com um wrapper de paginação diferente
  (`{"pagination":{"links":{"next":...`) — Arthur Nogueira/SP e Pains/MG.

  ⚠️ SAPL confirmado não é SAPL com dados: Pains/MG respondeu confirmado mas
  com `"total_entries":0` — API funciona, câmara não tem nada cadastrado.
  Não entra no corpus (nada para colher), mas não é falha do script.

  Erros são separados por causa: DNS (domínio não resolve — provavelmente
  saiu do ar), SSL (certificado inválido/autoassinado — pode ainda ser SAPL,
  mas exige decidir se aceita `--ignorar-ssl`), e outros.

Autor: Thiago Von Zeidler Gomes · Orientadora: Prof. Dra. Silvana Zioni
"""

import argparse
import csv
import sys
import unicodedata

import requests
import urllib3


def normalizar(txt: str) -> str:
    """minúsculas e sem acento, para filtro de município tolerante a como foi digitado."""
    n = unicodedata.normalize("NFKD", txt)
    return "".join(c for c in n if not unicodedata.combining(c)).lower()

# (município, UF, host candidato) — grupo A, já testado em 11/09/2026; ver a
# nota de descoberta de domínio para o porquê de cada um, incluindo os cinco
# sem prefixo "sapl." (hipótese mais fraca, e a que rendeu mais falso positivo).
CANDIDATOS_GRUPO_A = [
    ("Arthur Nogueira", "SP", "sapl.arturnogueira.sp.leg.br"),
    ("Assis", "SP", "sapl.assis.sp.leg.br"),
    ("Tarumã", "SP", "sapl.taruma.sp.leg.br"),
    ("Leopoldina", "MG", "sapl.leopoldina.mg.leg.br"),
    ("Pains", "MG", "sapl.pains.mg.leg.br"),
    ("Morretes", "PR", "sapl.morretes.pr.leg.br"),
    ("Jaboticabal", "SP", "sapl.jaboticabal.sp.leg.br"),
    ("Anicuns", "GO", "anicuns.go.leg.br"),
    ("Aruanã", "GO", "aruana.go.leg.br"),
    ("Garopaba", "SC", "garopaba.sc.leg.br"),
    ("Porto Belo", "SC", "portobelo.sc.leg.br"),
    ("Agudos", "SP", "agudos.sp.leg.br"),
]

# (município, UF, host candidato) — grupo C, 77 municípios sem sinal de SAPL
# na busca web (11/09/2026), ainda não testados. Cada município aparece com o
# domínio real já achado na busca (quando houve) e a(s) hipótese(s) de slug.
CANDIDATOS_GRUPO_C = [
    ("Caucaia", "CE", "cmcaucaia.ce.gov.br"),
    ("Caucaia", "CE", "sapl.caucaia.ce.leg.br"),
    ("Caucaia", "CE", "caucaia.ce.leg.br"),
    ("Goiás", "GO", "sapl.goias.go.leg.br"),
    ("Goiás", "GO", "goias.go.leg.br"),
    ("Campo Belo", "MG", "campobelo.mg.leg.br"),
    ("Campo Belo", "MG", "sapl.campobelo.mg.leg.br"),
    ("São Lourenço", "MG", "camarasl.mg.gov.br"),
    ("São Lourenço", "MG", "sapl.saolourenco.mg.leg.br"),
    ("São Lourenço", "MG", "saolourenco.mg.leg.br"),
    ("Engenheiro Beltrão", "PR", "cmengenheirobeltrao.pr.gov.br"),
    ("Engenheiro Beltrão", "PR", "sapl.engenheirobeltrao.pr.leg.br"),
    ("Engenheiro Beltrão", "PR", "engenheirobeltrao.pr.leg.br"),
    ("Wenceslau Braz", "PR", "camarawbraz.pr.gov.br"),
    ("Wenceslau Braz", "PR", "sapl.wenceslaubraz.pr.leg.br"),
    ("Wenceslau Braz", "PR", "wenceslaubraz.pr.leg.br"),
    ("Japeri", "RJ", "camarajaperi.rj.gov.br"),
    ("Japeri", "RJ", "sapl.japeri.rj.leg.br"),
    ("Japeri", "RJ", "japeri.rj.leg.br"),
    ("Silva Jardim", "RJ", "cmsilvajardim.rj.gov.br"),
    ("Silva Jardim", "RJ", "sapl.silvajardim.rj.leg.br"),
    ("Silva Jardim", "RJ", "silvajardim.rj.leg.br"),
    ("Parobé", "RS", "parobe.rs.leg.br"),
    ("Parobé", "RS", "sapl.parobe.rs.leg.br"),
    ("Balneário Camboriú", "SC", "balneariocamboriu.sc.leg.br"),
    ("Balneário Camboriú", "SC", "sapl.balneariocamboriu.sc.leg.br"),
    ("Governador Celso Ramos", "SC", "sapl.governadorcelsoramos.sc.leg.br"),
    ("Governador Celso Ramos", "SC", "governadorcelsoramos.sc.leg.br"),
    ("Nazaré Paulista", "SP", "sapl.nazarepaulista.sp.leg.br"),
    ("Nazaré Paulista", "SP", "nazarepaulista.sp.leg.br"),
    ("Potirendaba", "SP", "sapl.potirendaba.sp.leg.br"),
    ("Potirendaba", "SP", "potirendaba.sp.leg.br"),
    ("São Joaquim da Barra", "SP", "sapl.saojoaquimdabarra.sp.leg.br"),
    ("São Joaquim da Barra", "SP", "saojoaquimdabarra.sp.leg.br"),
    ("Tietê", "SP", "sapl.tiete.sp.leg.br"),
    ("Tietê", "SP", "tiete.sp.leg.br"),
    ("Abaeté", "MG", "camaraabaete.mg.gov.br"),
    ("Abaeté", "MG", "sapl.abaete.mg.leg.br"),
    ("Abaeté", "MG", "abaete.mg.leg.br"),
    ("Coromandel", "MG", "coromandel.mg.leg.br"),
    ("Coromandel", "MG", "sapl.coromandel.mg.leg.br"),
    ("Machado", "MG", "camaramachado.mg.gov.br"),
    ("Machado", "MG", "sapl.machado.mg.leg.br"),
    ("Machado", "MG", "machado.mg.leg.br"),
    ("Costa Rica", "MS", "legislativo.costarica.ms.leg.br"),
    ("Costa Rica", "MS", "sapl.costarica.ms.leg.br"),
    ("Costa Rica", "MS", "costarica.ms.leg.br"),
    ("Palmas", "PR", "camarapalmas.pr.gov.br"),
    ("Palmas", "PR", "sapl.palmas.pr.leg.br"),
    ("Palmas", "PR", "palmas.pr.leg.br"),
    ("São João da Barra", "RJ", "camarasjb.rj.gov.br"),
    ("São João da Barra", "RJ", "sapl.saojoaodabarra.rj.leg.br"),
    ("São João da Barra", "RJ", "saojoaodabarra.rj.leg.br"),
    ("Pedro Osório", "RS", "campedroosorio.rs.gov.br"),
    ("Pedro Osório", "RS", "sapl.pedroosorio.rs.leg.br"),
    ("Pedro Osório", "RS", "pedroosorio.rs.leg.br"),
    ("São Lourenço da Serra", "SP", "cmsls.sp.gov.br"),
    ("São Lourenço da Serra", "SP", "sapl.saolourencodaserra.sp.leg.br"),
    ("São Lourenço da Serra", "SP", "saolourencodaserra.sp.leg.br"),
    ("Arceburgo", "MG", "camaraarceburgo.mg.gov.br"),
    ("Arceburgo", "MG", "sapl.arceburgo.mg.leg.br"),
    ("Arceburgo", "MG", "arceburgo.mg.leg.br"),
    ("Dom Silvério", "MG", "camaradomsilverio.mg.gov.br"),
    ("Dom Silvério", "MG", "sapl.domsilverio.mg.leg.br"),
    ("Dom Silvério", "MG", "domsilverio.mg.leg.br"),
    ("Mariana", "MG", "camarademariana.mg.gov.br"),
    ("Mariana", "MG", "sapl.mariana.mg.leg.br"),
    ("Mariana", "MG", "mariana.mg.leg.br"),
    ("Pirapora", "MG", "pirapora.mg.leg.br"),
    ("Pirapora", "MG", "sapl.pirapora.mg.leg.br"),
    ("Sorriso", "MT", "sorriso.mt.leg.br"),
    ("Sorriso", "MT", "sapl.sorriso.mt.leg.br"),
    ("Paranaguá", "PR", "paranagua.pr.leg.br"),
    ("Paranaguá", "PR", "sapl.paranagua.pr.leg.br"),
    ("Natividade", "RJ", "camaranatividade.rj.gov.br"),
    ("Natividade", "RJ", "sapl.natividade.rj.leg.br"),
    ("Natividade", "RJ", "natividade.rj.leg.br"),
    ("Dourado", "SP", "camaradourado.sp.gov.br"),
    ("Dourado", "SP", "sapl.dourado.sp.leg.br"),
    ("Dourado", "SP", "dourado.sp.leg.br"),
    ("Santa Isabel", "SP", "camarasantaisabel.sp.gov.br"),
    ("Santa Isabel", "SP", "sapl.santaisabel.sp.leg.br"),
    ("Santa Isabel", "SP", "santaisabel.sp.leg.br"),
    ("São Sebastião da Grama", "SP", "camarassgrama.sp.gov.br"),
    ("São Sebastião da Grama", "SP", "sapl.saosebastiaodagrama.sp.leg.br"),
    ("São Sebastião da Grama", "SP", "saosebastiaodagrama.sp.leg.br"),
    ("Belo Vale", "MG", "camarabelovale.mg.gov.br"),
    ("Belo Vale", "MG", "sapl.belovale.mg.leg.br"),
    ("Belo Vale", "MG", "belovale.mg.leg.br"),
    ("Ibirité", "MG", "camaraibirite.mg.gov.br"),
    ("Ibirité", "MG", "sapl.ibirite.mg.leg.br"),
    ("Ibirité", "MG", "ibirite.mg.leg.br"),
    ("Monte Carmelo", "MG", "camaramontecarmelo.mg.gov.br"),
    ("Monte Carmelo", "MG", "sapl.montecarmelo.mg.leg.br"),
    ("Monte Carmelo", "MG", "montecarmelo.mg.leg.br"),
    ("São Joaquim de Bicas", "MG", "camarasaojoaquimdebicas.mg.gov.br"),
    ("São Joaquim de Bicas", "MG", "sapl.saojoaquimdebicas.mg.leg.br"),
    ("São Joaquim de Bicas", "MG", "saojoaquimdebicas.mg.leg.br"),
    ("Picos", "PI", "picos.pi.leg.br"),
    ("Picos", "PI", "sapl.picos.pi.leg.br"),
    ("Itaperuçu", "PR", "itaperucu.pr.leg.br"),
    ("Itaperuçu", "PR", "sapl.itaperucu.pr.leg.br"),
    ("Guapimirim", "RJ", "camaradeguapimirim.rj.gov.br"),
    ("Guapimirim", "RJ", "sapl.guapimirim.rj.leg.br"),
    ("Guapimirim", "RJ", "guapimirim.rj.leg.br"),
    ("Paracambi", "RJ", "paracambi.rj.leg.br"),
    ("Paracambi", "RJ", "sapl.paracambi.rj.leg.br"),
    ("Tanguá", "RJ", "cmtangua.rj.gov.br"),
    ("Tanguá", "RJ", "sapl.tangua.rj.leg.br"),
    ("Tanguá", "RJ", "tangua.rj.leg.br"),
    ("Quaraí", "RS", "camaraquarai.rs.gov.br"),
    ("Quaraí", "RS", "sapl.quarai.rs.leg.br"),
    ("Quaraí", "RS", "quarai.rs.leg.br"),
    ("Bombinhas", "SC", "camarabombinhas.sc.gov.br"),
    ("Bombinhas", "SC", "sapl.bombinhas.sc.leg.br"),
    ("Bombinhas", "SC", "bombinhas.sc.leg.br"),
    ("Cerquilho", "SP", "cerquilho.sp.leg.br"),
    ("Cerquilho", "SP", "sapl.cerquilho.sp.leg.br"),
    ("Getulina", "SP", "camaragetulina.sp.gov.br"),
    ("Getulina", "SP", "sapl.getulina.sp.leg.br"),
    ("Getulina", "SP", "getulina.sp.leg.br"),
    ("Macatuba", "SP", "cmmacatuba.sp.gov.br"),
    ("Macatuba", "SP", "sapl.macatuba.sp.leg.br"),
    ("Macatuba", "SP", "macatuba.sp.leg.br"),
    ("Santa Rita do Passa Quatro", "SP", "camarasantarita.sp.gov.br"),
    ("Santa Rita do Passa Quatro", "SP", "sapl.santaritadopassaquatro.sp.leg.br"),
    ("Santa Rita do Passa Quatro", "SP", "santaritadopassaquatro.sp.leg.br"),
    ("Tambaú", "SP", "camaratambau.sp.gov.br"),
    ("Tambaú", "SP", "sapl.tambau.sp.leg.br"),
    ("Tambaú", "SP", "tambau.sp.leg.br"),
    ("Vargem", "SP", "camaravargem.sp.gov.br"),
    ("Vargem", "SP", "sapl.vargem.sp.leg.br"),
    ("Vargem", "SP", "vargem.sp.leg.br"),
    ("Ituiutaba", "MG", "ituiutaba.mg.leg.br"),
    ("Ituiutaba", "MG", "sapl.ituiutaba.mg.leg.br"),
    ("Muzambinho", "MG", "camaramuzambinho.mg.gov.br"),
    ("Muzambinho", "MG", "sapl.muzambinho.mg.leg.br"),
    ("Muzambinho", "MG", "muzambinho.mg.leg.br"),
    ("São José da Lapa", "MG", "camarasjl.mg.gov.br"),
    ("São José da Lapa", "MG", "sapl.saojosedalapa.mg.leg.br"),
    ("São José da Lapa", "MG", "saojosedalapa.mg.leg.br"),
    ("Antonina", "PR", "camaramunicipaldeantonina.pr.gov.br"),
    ("Antonina", "PR", "sapl.antonina.pr.leg.br"),
    ("Antonina", "PR", "antonina.pr.leg.br"),
    ("Lidianópolis", "PR", "cmlidianopolis.pr.gov.br"),
    ("Lidianópolis", "PR", "sapl.lidianopolis.pr.leg.br"),
    ("Lidianópolis", "PR", "lidianopolis.pr.leg.br"),
    ("Tijucas do Sul", "PR", "tijucasdosul.pr.leg.br"),
    ("Tijucas do Sul", "PR", "sapl.tijucasdosul.pr.leg.br"),
    ("Itaboraí", "RJ", "camaraitaborai.rj.gov.br"),
    ("Itaboraí", "RJ", "sapl.itaborai.rj.leg.br"),
    ("Itaboraí", "RJ", "itaborai.rj.leg.br"),
    ("Canoas", "RS", "camaracanoas.rs.gov.br"),
    ("Canoas", "RS", "sapl.canoas.rs.leg.br"),
    ("Canoas", "RS", "canoas.rs.leg.br"),
    ("Araranguá", "SC", "cmva.sc.gov.br"),
    ("Araranguá", "SC", "sapl.ararangua.sc.leg.br"),
    ("Araranguá", "SC", "ararangua.sc.leg.br"),
    ("Forquilhinha", "SC", "camaraforquilhinha.sc.gov.br"),
    ("Forquilhinha", "SC", "sapl.forquilhinha.sc.leg.br"),
    ("Forquilhinha", "SC", "forquilhinha.sc.leg.br"),
    ("Três Barras", "SC", "sapl.tresbarras.sc.leg.br"),
    ("Três Barras", "SC", "tresbarras.sc.leg.br"),
    ("Itapeva", "SP", "camaraitapeva.sp.gov.br"),
    ("Itapeva", "SP", "sapl.itapeva.sp.leg.br"),
    ("Itapeva", "SP", "itapeva.sp.leg.br"),
    ("Penápolis", "SP", "camaradepenapolis.sp.gov.br"),
    ("Penápolis", "SP", "sapl.penapolis.sp.leg.br"),
    ("Penápolis", "SP", "penapolis.sp.leg.br"),
    ("Santo Antônio de Posse", "SP", "sapl.santoantoniodeposse.sp.leg.br"),
    ("Santo Antônio de Posse", "SP", "santoantoniodeposse.sp.leg.br"),
    ("Taquarituba", "SP", "sapl.taquarituba.sp.leg.br"),
    ("Taquarituba", "SP", "taquarituba.sp.leg.br"),
    ("Vargem Grande Paulista", "SP", "sapl.vargemgrandepaulista.sp.leg.br"),
    ("Vargem Grande Paulista", "SP", "vargemgrandepaulista.sp.leg.br"),
    ("Caeté", "MG", "camaradecaete.mg.gov.br"),
    ("Caeté", "MG", "sapl.caete.mg.leg.br"),
    ("Caeté", "MG", "caete.mg.leg.br"),
    ("Ouro Branco", "MG", "ourobranco.cam.mg.gov.br"),
    ("Ouro Branco", "MG", "sapl.ourobranco.mg.leg.br"),
    ("Ouro Branco", "MG", "ourobranco.mg.leg.br"),
    ("São João del Rei", "MG", "camarasaojoaodelrei.mg.gov.br"),
    ("São João del Rei", "MG", "sapl.saojoaodelrei.mg.leg.br"),
    ("São João del Rei", "MG", "saojoaodelrei.mg.leg.br"),
    ("Matinhos", "PR", "camaramatinhos.pr.gov.br"),
    ("Matinhos", "PR", "sapl.matinhos.pr.leg.br"),
    ("Matinhos", "PR", "matinhos.pr.leg.br"),
    ("Rio das Flores", "RJ", "riodasflores.rj.leg.br"),
    ("Rio das Flores", "RJ", "sapl.riodasflores.rj.leg.br"),
    ("Ivoti", "RS", "camaraivoti.rs.gov.br"),
    ("Ivoti", "RS", "sapl.ivoti.rs.leg.br"),
    ("Ivoti", "RS", "ivoti.rs.leg.br"),
    ("Balneário Arroio do Silva", "SC", "cmbas.sc.gov.br"),
    ("Balneário Arroio do Silva", "SC", "sapl.balnearioarroiodosilva.sc.leg.br"),
    ("Balneário Arroio do Silva", "SC", "balnearioarroiodosilva.sc.leg.br"),
    ("Batatais", "SP", "camarabatatais.sp.gov.br"),
    ("Batatais", "SP", "sapl.batatais.sp.leg.br"),
    ("Batatais", "SP", "batatais.sp.leg.br"),
    ("Holambra", "SP", "camaraholambra.sp.gov.br"),
    ("Holambra", "SP", "sapl.holambra.sp.leg.br"),
    ("Holambra", "SP", "holambra.sp.leg.br"),
    ("Itararé", "SP", "camaraitarare.sp.gov.br"),
    ("Itararé", "SP", "sapl.itarare.sp.leg.br"),
    ("Itararé", "SP", "itarare.sp.leg.br"),
    ("Pirapora do Bom Jesus", "SP", "piraporadobomjesus.sp.leg.br"),
    ("Pirapora do Bom Jesus", "SP", "sapl.piraporadobomjesus.sp.leg.br"),
]


def parece_sapl(status: int, corpo: str):
    """Retorna (True/False, motivo). Reconhece os dois formatos de paginação
    já vistos em instalações SAPL reais: o clássico do DRF (`{"count":...}`)
    e o wrapper alternativo (`{"pagination":{...}}`, com `total_entries`)."""
    if status != 200:
        return False, f"HTTP {status}, não é resposta de API"
    trecho = corpo.strip()[:80].lower()
    if trecho.startswith('{"count"'):
        return True, "formato DRF classico"
    if trecho.startswith('{"pagination"') or '"total_entries"' in corpo[:300].lower():
        vazio = '"total_entries":0' in corpo[:300].replace(" ", "")
        return True, "formato paginacao alternativo" + (" — VAZIO (0 normas)" if vazio else "")
    if '"results"' in trecho:
        return True, "campo results presente"
    if trecho.startswith("<!doctype") or trecho.startswith("<html") or trecho.startswith("<!doctype html"):
        return False, "HTTP 200 mas corpo é HTML — não é API"
    return False, "corpo não reconhecido como SAPL"


def sondar(candidatos, contato: str, ignorar_ssl: bool, timeout: int = 10):
    headers = {"User-Agent": f"pesquisa-doutorado-tarifazero ({contato})"}
    if ignorar_ssl:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    resultados = []
    for mun, uf, host in candidatos:
        url = f"https://{host}/api/norma/normajuridica/?page=1"
        try:
            r = requests.get(url, timeout=timeout, headers=headers, verify=not ignorar_ssl)
            corpo = r.text
            sapl, motivo = parece_sapl(r.status_code, corpo)
            trecho = corpo[:150].replace("\n", " ")
            marca = "✅ SAPL" if sapl else "—"
            print(f"{marca}  {mun}/{uf}  {host}  HTTP {r.status_code}  ({motivo})  {trecho}")
            resultados.append([mun, uf, host, r.status_code, sapl, motivo, trecho])
        except requests.exceptions.SSLError as e:
            print(f"⚠️ SSL  {mun}/{uf}  {host}  certificado inválido — talvez SAPL real; rode com --ignorar-ssl para conferir. {e}")
            resultados.append([mun, uf, host, "ERRO_SSL", False, "certificado inválido, não testado o corpo", str(e)])
        except requests.exceptions.ConnectionError as e:
            causa = "DNS não resolve (domínio provavelmente fora do ar)" if "NameResolutionError" in str(e) else "erro de conexão"
            print(f"❌ CONEXÃO  {mun}/{uf}  {host}  {causa}")
            resultados.append([mun, uf, host, "ERRO_CONEXAO", False, causa, str(e)])
        except Exception as e:  # noqa: BLE001 — continuar mesmo se um host falhar por motivo imprevisto
            print(f"ERRO  {mun}/{uf}  {host}  {e}")
            resultados.append([mun, uf, host, "ERRO", False, "erro imprevisto", str(e)])
    return resultados


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--grupo", choices=["a", "c", "todos"], default="c",
                     help="qual lista de candidatos rodar: 'a' (12, já testado em "
                          "11/09/2026 — só para reteste pontual), 'c' (77 municípios sem "
                          "sinal, ainda não testado — padrão) ou 'todos' (a + c, 218 linhas).")
    ap.add_argument("--saida", default=None,
                     help="nome do CSV de saída; padrão: sondagem_grupo_<grupo>.csv")
    ap.add_argument("--contato", default="thiago@poloplanejamento.com")
    ap.add_argument("--ignorar-ssl", action="store_true",
                     help="não verifica certificado TLS — só para casos como Morretes/PR, "
                          "que respondem com certificado autoassinado. Decisão sua: é leitura "
                          "pública e de baixo risco, mas ignorar verificação de certificado "
                          "nunca é o padrão recomendado.")
    ap.add_argument("--timeout", type=int, default=10,
                     help="segundos de espera por resposta antes de desistir do host "
                          "(padrão: 10). Suba para 30+ em hosts que deram timeout na "
                          "rodada anterior (ex.: Silva Jardim/RJ, Costa Rica/MS) — pode "
                          "ser servidor lento, não domínio morto.")
    ap.add_argument("--filtro", default=None,
                     help="roda só os municípios cujo nome contenha um destes textos "
                          "(separados por vírgula, sem acento tolerado). Ex.: "
                          "--filtro \"Taruma,Morretes,Santa Isabel,Vargem\" testa só os "
                          "quatro pendentes por SSL, em vez do grupo inteiro.")
    args = ap.parse_args()

    if args.grupo == "a":
        candidatos = CANDIDATOS_GRUPO_A
    elif args.grupo == "c":
        candidatos = CANDIDATOS_GRUPO_C
    else:
        candidatos = CANDIDATOS_GRUPO_A + CANDIDATOS_GRUPO_C

    if args.filtro:
        termos = [normalizar(t.strip()) for t in args.filtro.split(",") if t.strip()]
        candidatos = [c for c in candidatos if any(t in normalizar(c[0]) for t in termos)]
        if not candidatos:
            print(f"Nenhum município do grupo '{args.grupo}' bate com --filtro {args.filtro!r}.")
            return 1

    saida = args.saida or f"sondagem_grupo_{args.grupo}.csv"

    print(f"Rodando grupo '{args.grupo}': {len(candidatos)} candidatos "
          f"({len(set((m, u) for m, u, h in candidatos))} municípios).\n")

    resultados = sondar(candidatos, args.contato, args.ignorar_ssl, args.timeout)

    with open(saida, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["municipio", "uf", "host", "http_status", "parece_sapl", "motivo", "trecho_resposta"])
        w.writerows(resultados)

    confirmados = [r for r in resultados if r[4] is True]
    vazios = [r for r in confirmados if "VAZIO" in r[5]]
    print(f"\nSalvo em {saida}")
    print(f"{len(confirmados)} de {len(resultados)} candidatos confirmados como SAPL "
          f"({len(vazios)} deles sem nenhuma norma cadastrada).")
    uteis = [r for r in confirmados if "VAZIO" not in r[5]]
    if uteis:
        print("Acrescente estes hosts à descoberta do sapl_varredura.py (têm normas):")
        for mun, uf, host, *_ in uteis:
            print(f"  {mun}/{uf} -> {host}")


if __name__ == "__main__":
    sys.exit(main())
