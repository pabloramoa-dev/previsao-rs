from datetime import datetime
from zoneinfo import ZoneInfo
from scripts.monitor_alertas_rs import normalizar_cap
from scripts.alerta_auto_rs import escolher

def test_cap_sem_alerta():
    assert normalizar_cap(b'<feed xmlns="http://www.w3.org/2005/Atom"/>',datetime.now(ZoneInfo("America/Sao_Paulo")))==[]

def test_retomar_story_sem_repetir_reel():
    a=dict(id_aviso="1",severidade="Perigo",municipios_rs=1)
    h={"registros":[dict(id_aviso="1",nivel=2,media_id="123",story_status="pending")]}
    assert escolher([a],h)==a
    h["registros"][0]["story_status"]="published"
    assert escolher([a],h) is None
