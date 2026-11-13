#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
Baixa os documentos dos lotes 1 e 2 das buscas manuais (17/10/2026) para _a triar/.

Autor: Thiago Von Zeidler Gomes
Orientadora: Prof.ª Dra. Silvana Zioni
Script criado em 17/10/2026 (Claude, a pedido do autor).

É só um atalho: roda baixar_documentos_busca.py (mesmas regras: robots.txt, 401/403/captcha viram
"baixar à mão", um pedido por vez, deduplicação por SHA-256, nada é apagado) com a fila
04 - Análises/Pesquisa legal/Busca — documentos dos lotes 1 e 2, fila de download (17-10-2026).csv
(linhas n601 a n628; P1 essenciais, P2 opcionais).

USO (da raiz do cofre, ou dois cliques em _meta\scripts\baixar_documentos_lotes_1017.bat)
    python "_meta/scripts/baixar_documentos_lotes_1017.py" --simular
    python "_meta/scripts/baixar_documentos_lotes_1017.py" --prioridade P1
    python "_meta/scripts/baixar_documentos_lotes_1017.py" --seguir-links     # páginas com anexos (Mata, Pres. Kennedy, Tambaú)
    python "_meta/scripts/baixar_documentos_lotes_1017.py" --abrir-manuais    # SAPL de Jaboticabal e DOM/SC de Garopaba
"""
import os, sys, runpy
AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(os.path.dirname(AQUI))
FILA = os.path.join(RAIZ, "04 - Análises", "Pesquisa legal",
                    "Busca — documentos dos lotes 1 e 2, fila de download (17-10-2026).csv")
if not os.path.isfile(FILA):
    sys.exit("Fila não encontrada: " + FILA)
if "--fila" not in sys.argv:
    sys.argv[1:1] = ["--fila", FILA]
sys.argv[0] = os.path.join(AQUI, "baixar_documentos_busca.py")
runpy.run_path(sys.argv[0], run_name="__main__")
