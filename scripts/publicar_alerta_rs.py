"""Publicação de alerta com recibos separados e bloqueio de retry ambíguo."""
import argparse, json, os, hashlib
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import requests
from src.previsao.publish import instagram as ig

def salvar(p,h):
    p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_suffix(".tmp")
    tmp.write_text(json.dumps(h,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    tmp.replace(p)

def story_container(url):
    user,token,version,_=ig._cfg()
    r=requests.post(f"{ig.base_url(version)}/{user}/media",data={"media_type":"STORIES","video_url":url,"access_token":token},timeout=30)
    r.raise_for_status()
    return r.json()["id"]

def procurar(marker):
    user,token,version,_=ig._cfg()
    r=requests.get(f"{ig.base_url(version)}/{user}/media",params={"fields":"id,caption","limit":50,"access_token":token},timeout=30)
    r.raise_for_status()
    return next((x["id"] for x in r.json().get("data",[]) if marker in (x.get("caption") or "")),None)

def publicar(a):
    p=Path(a.historico)
    h=json.loads(p.read_text()) if p.exists() else {"versao":1,"registros":[]}
    d=json.loads(Path(a.decisao).read_text())
    if d.get("seguir")!="sim": return
    if datetime.fromisoformat(d["fim"]) <= datetime.now(ZoneInfo("America/Sao_Paulo")):
        raise RuntimeError("Aviso expirou antes da publicação")
    ig.verify_destination()
    marker="Ref. alerta RS "+hashlib.sha256(f"{d['id_aviso']}:{d['nivel']}".encode()).hexdigest()[:16]
    caption=Path(a.caption_file).read_text().strip()+"\n\n"+marker
    rec=next((x for x in h["registros"] if str(x["id_aviso"])==str(d["id_aviso"]) and x["nivel"]==d["nivel"]),None)
    if rec is None:
        rec={k:d[k] for k in ("id_aviso","nivel","tipo","fim")}
        rec.update(story_status="pending",reel_status="pending")
        h["registros"].append(rec)
    if not rec.get("media_id"):
        mid=procurar(marker)
        if not mid:
            if rec.get("reel_status")=="unknown": raise RuntimeError("Reel com resultado incerto: reconciliar na Meta")
            cid=ig.create_reel(a.video_url,caption)
            ig.wait_ready(cid)
            rec["reel_status"]="unknown"; salvar(p,h)
            mid=ig.publish(cid)
        rec.update(media_id=mid,reel_status="published",publicado_em=datetime.now(ZoneInfo("America/Sao_Paulo")).isoformat())
        salvar(p,h)
    print("Reel media_id=",rec["media_id"])
    if rec.get("story_status")=="published": return
    if rec.get("story_status")=="unknown": raise RuntimeError("Story com resultado incerto: conferir Meta antes de repetir")
    rec["story_status"]="pending"; salvar(p,h)
    cid=story_container(a.video_url)
    ig.wait_ready(cid)
    rec.update(story_status="unknown",story_container=cid); salvar(p,h)
    sid=ig.publish(cid)
    rec.update(story_status="published",story_media_id=sid)
    salvar(p,h)
    print("Story media_id=",sid)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    for name in ("video-url","caption-file","historico","decisao"): p.add_argument("--"+name,required=True)
    publicar(p.parse_args())
