import sqlite3,os,json,re
Z=os.path.expanduser("~/mnt/Zotero"); DB=os.path.expanduser("~/zcopy/zotero.sqlite")
c=sqlite3.connect(DB); c.execute("pragma wal_checkpoint(TRUNCATE)")
tipos={r[0]:r[1] for r in c.execute("select itemTypeID,typeName from itemTypes")}
del_ids={r[0] for r in c.execute("select itemID from deletedItems")}
att_ids={r[0] for r in c.execute("select itemID from itemAttachments")}
note_ids={r[0] for r in c.execute("select itemID from itemNotes")}
items={}
for iid,key,tid in c.execute("select itemID,key,itemTypeID from items"):
    if iid in del_ids or iid in att_ids or iid in note_ids: continue
    items[iid]={"itemID":iid,"key":key,"tipo":tipos.get(tid,""),"campos":{},"autores":[],"anexos":[]}
for iid,fn,v in c.execute("""select id.itemID,f.fieldName,idv.value from itemData id
    join fields f on f.fieldID=id.fieldID join itemDataValues idv on idv.valueID=id.valueID"""):
    if iid in items: items[iid]["campos"][fn]=v
for iid,fn,ln in c.execute("""select cr.itemID,cd.firstName,cd.lastName from itemCreators cr
    join creators cd on cd.creatorID=cr.creatorID order by cr.itemID,cr.orderIndex"""):
    if iid in items: items[iid]["autores"].append(((ln or "")+", "+(fn or "")).strip(", "))
akeys={r[0]:r[1] for r in c.execute("select itemID,key from items")}
for pid,aid,lm,ct,path in c.execute("select parentItemID,itemID,linkMode,contentType,path from itemAttachments where parentItemID is not null"):
    if pid not in items or aid in del_ids: continue
    k=akeys.get(aid); fp=None; ex=False
    if path and path.startswith("storage:") and k:
        fp=os.path.join(Z,"storage",k,path[8:]); ex=os.path.exists(fp)
    elif path:
        fp=path.replace("attachments:",""); ex=os.path.exists(fp)
    items[pid]["anexos"].append({"key":k,"ct":ct or "","path":path or "","existe":ex})
def ck(it):
    v=it["campos"].get("citationKey")
    if v: return v
    m=re.search(r"Citation Key:\s*([^\s\n]+)",it["campos"].get("extra","") or "")
    return m.group(1) if m else ""
def ano(it):
    m=re.search(r"(1[89]\d\d|20\d\d)",it["campos"].get("date","") or ""); return m.group(1) if m else ""
out=[{"itemID":it["itemID"],"key":it["key"],"tipo":it["tipo"],"citekey":ck(it),
      "titulo":it["campos"].get("title","") or it["campos"].get("caseName","") or "",
      "ano":ano(it),"autores":" | ".join(it["autores"]),
      "veiculo":it["campos"].get("publicationTitle") or it["campos"].get("bookTitle") or it["campos"].get("publisher") or "",
      "n_anexos":len(it["anexos"]),"n_anexos_ok":sum(1 for a in it["anexos"] if a["existe"]),
      "pdf_ok":sum(1 for a in it["anexos"] if a["existe"] and "pdf" in a["ct"]),
      "anexos":it["anexos"]} for it in items.values()]
json.dump(out,open(os.path.expanduser("~/rsl/zotero.json"),"w",encoding="utf-8", newline="\n"),ensure_ascii=False)
print("itens:",len(out),"| com anexo:",sum(1 for x in out if x["n_anexos"]),
      "| anexo em disco:",sum(1 for x in out if x["n_anexos_ok"]),"| com citekey:",sum(1 for x in out if x["citekey"]))
