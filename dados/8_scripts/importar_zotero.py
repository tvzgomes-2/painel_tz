#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Importador para o Zotero (tese Tarifa Zero) — via API (pyzotero).
SEGURO POR PADRÃO: roda em --dry-run (não grava nada); só escreve com --commit.
Checa DUPLICATAS (por DOI e por título normalizado) antes de criar.

Pré-requisitos:
  pip install pyzotero
  Variáveis de ambiente (NÃO coloque a chave no arquivo):
    ZOTERO_API_KEY   = sua chave de escrita  (zotero.org/settings/keys)
    ZOTERO_USER_ID   = seu userID numérico   (mesma página)
    ZOTERO_GROUP_ID  = id da biblioteca do grupo (opcional; p/ o lote do grupo)

Uso:
  python3 importar_zotero.py            # relatório (dry-run)
  python3 importar_zotero.py --commit   # grava de fato
  python3 importar_zotero.py --only leis # só um lote (leis|relatorios|grupo)
"""
import os, re, sys, glob

ZDIR = "/sessions/kind-sleepy-feynman/mnt/doutorado/05 - Referências/_zotero"

# ---- Lotes: (nome, arquivo .ris, coleção-alvo, biblioteca) ----
BATCHES = [
    ("leis",       "Leis TZ - TODAS (62) tipo bill.ris",                  "Legislação — Leis de TZ", "user"),
    ("relatorios", "NTU 2025 - Tarifa Zero nas Cidades do Brasil.ris",    "Relatórios",              "user"),
    ("relatorios", "NTU 2026 - Tarifa Zero nas Cidades do Brasil.ris",    "Relatórios",              "user"),
    ("relatorios", "GAEP-UnB 2025 - Caminhos para a Tarifa Zero.ris",     "Relatórios",              "user"),
    ("relatorios", "Santini 2024 - Brazilian municipalities FFPT (Dataverse).ris", "Relatórios",      "user"),
    ("relatorios", "Tarifa Zero - conheça os modelos (Rede TVT 2026).ris","Relatórios",              "user"),
    ("grupo",      "Transição sociotécnica (grupo)/transição-sociotécnica.ris", "Transição sociotécnica", "group"),
]

# ---- RIS → item Zotero (parser mínimo, sem dependências) ----
TY2ZOT = {"JOUR":"journalArticle","CHAP":"bookSection","BOOK":"book","RPRT":"report",
          "BILL":"bill","STAT":"statute","CONF":"conferencePaper","THES":"thesis",
          "ELEC":"webpage","GEN":"document","DATA":"dataset","MGZN":"magazineArticle"}

def parse_ris(text):
    items=[]; cur=None
    for raw in text.splitlines():
        m=re.match(r'^([A-Z0-9]{2})  - (.*)$', raw)
        if not m:
            continue
        tag,val=m.group(1),m.group(2).strip()
        if tag=="TY":
            cur={"_ty":val,"AU":[],"KW":[]}
        elif tag=="ER":
            if cur: items.append(cur); cur=None
        elif cur is not None:
            if tag in ("AU","A1","A2"): cur["AU"].append(val)
            elif tag=="KW": cur["KW"].append(val)
            else: cur.setdefault(tag,val)
    return items

def ris_to_zotero(it):
    ztype=TY2ZOT.get(it.get("_ty","GEN"),"document")
    creators=[]
    for a in it.get("AU",[]):
        if "," in a:
            ln,fn=a.split(",",1); creators.append({"creatorType":"author","lastName":ln.strip(),"firstName":fn.strip()})
        else:
            creators.append({"creatorType":"author","name":a.strip()})
    z={"itemType":ztype,"title":it.get("TI") or it.get("T1") or "",
       "creators":creators,"date":it.get("PY") or it.get("DA") or "",
       "tags":[{"tag":k} for k in it.get("KW",[])]}
    # campos por tipo
    cont=it.get("T2") or it.get("JO") or it.get("JF") or ""
    if ztype=="journalArticle": z["publicationTitle"]=cont
    elif ztype=="bookSection": z["bookTitle"]=cont
    elif ztype in ("report","conferencePaper"): z["publisher" if ztype=="report" else "proceedingsTitle"]=cont
    for k,zk in [("VL","volume"),("IS","issue"),("SP","pages"),("DO","DOI"),("PB","publisher"),("UR","url"),("SN","ISSN")]:
        if it.get(k): z[zk]=it[k]
    if it.get("SP") and it.get("EP"): z["pages"]=f"{it['SP']}-{it['EP']}"
    return z

def norm(s): return re.sub(r'[^a-z0-9]+',' ',(s or "").lower()).strip()

def main():
    commit = "--commit" in sys.argv
    only = None
    if "--only" in sys.argv:
        only = sys.argv[sys.argv.index("--only")+1]
    print("=== Importador Zotero — modo:", "COMMIT (grava)" if commit else "DRY-RUN (não grava)", "===")
    try:
        from pyzotero import zotero
    except ImportError:
        print("!! pyzotero não instalado. Rode: pip install pyzotero"); return 2
    api=os.environ.get("ZOTERO_API_KEY"); uid=os.environ.get("ZOTERO_USER_ID"); gid=os.environ.get("ZOTERO_GROUP_ID")
    if not api or not uid:
        print("!! Defina ZOTERO_API_KEY e ZOTERO_USER_ID no ambiente."); return 2
    zu = zotero.Zotero(uid, "user", api)
    zg = zotero.Zotero(gid, "group", api) if gid else None

    # índice de duplicatas da biblioteca pessoal (DOI + título normalizado)
    print("Lendo itens existentes (biblioteca pessoal) para dedup…")
    have_doi=set(); have_title=set()
    try:
        for it in zu.everything(zu.items()):
            d=it.get("data",{})
            if d.get("DOI"): have_doi.add(d["DOI"].lower())
            if d.get("title"): have_title.add(norm(d["title"]))
    except Exception as e:
        print("  (aviso: não consegui listar existentes:",e,")")
    print(f"  {len(have_title)} títulos / {len(have_doi)} DOIs já na biblioteca.")

    def ensure_collection(z, name):
        for c in z.everything(z.collections()):
            if c["data"]["name"]==name: return c["key"]
        if not commit:
            print(f"  [dry] criaria coleção: {name}"); return None
        return z.create_collection([{"name":name}])["successful"]["0"]["key"]

    total_new=total_dup=0
    for name, rel, coll, lib in BATCHES:
        if only and only!=name: continue
        path=os.path.join(ZDIR, rel)
        if not os.path.exists(path):
            print(f"\n[{name}] FALTA arquivo: {rel}"); continue
        z = zg if lib=="group" else zu
        if lib=="group" and not zg:
            print(f"\n[{name}] pulado (ZOTERO_GROUP_ID não definido)"); continue
        items=parse_ris(open(path,encoding='utf-8',errors='replace').read())
        print(f"\n[{name}] {rel} → coleção '{coll}' ({lib}): {len(items)} registros")
        collkey=ensure_collection(z, coll)
        payload=[]
        for it in items:
            z_it=ris_to_zotero(it)
            dup = (z_it.get("DOI","").lower() in have_doi) or (norm(z_it["title"]) in have_title)
            if dup: total_dup+=1; continue
            if collkey: z_it["collections"]=[collkey]
            payload.append(z_it)
        total_new+=len(payload)
        print(f"   novos: {len(payload)} | duplicados (pulados): {len(items)-len(payload)}")
        if commit and payload:
            for i in range(0,len(payload),50):
                r=z.create_items(payload[i:i+50])
                print("   gravados:", len(r.get("successful",{})), "| falhas:", len(r.get("failed",{})))
    print(f"\n=== RESUMO: novos a criar {total_new} | duplicados pulados {total_dup} ===")
    if not commit: print("Nada foi gravado (dry-run). Reveja e rode com --commit.")
    return 0

if __name__=="__main__":
    sys.exit(main())
