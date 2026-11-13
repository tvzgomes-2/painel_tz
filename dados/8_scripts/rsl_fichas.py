# -*- coding: utf-8 -*-
"""SUPERADO em 09/09/2026 — nao usar.
O casamento ficha<->item foi absorvido por rsl_inventario.py, que faz tudo num passe.
Motivo: este script e o rsl_inventario.py escreviam o MESMO CSV com conjuntos de colunas
diferentes, e o segundo a rodar quebrava em
    ValueError: dict contains fields not in fieldnames
depois de ja ter aberto o destino em modo 'w' — isto e, truncando o arquivo antes de falhar.
E o mesmo defeito que destruiu o arestas_manuais.csv em 07/09/2026.
Regra que fica: um CSV, um escritor; e validar em memoria antes de abrir o destino."""
import sys
sys.exit("SUPERADO: rode 'python3 _meta/scripts/rsl_inventario.py' (faz o casamento das fichas tambem).")
