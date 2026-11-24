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

def test_cap_rs_com_validade_e_ibge():
    now=datetime(2026,11,23,12,tzinfo=ZoneInfo("America/Sao_Paulo"))
    raw=b'''<alert xmlns="urn:oasis:names:tc:emergency:cap:1.2"><identifier>abc</identifier><sender>Defesa Civil RS</sender><status>Actual</status><msgType>Alert</msgType><scope>Public</scope><info><senderName>Defesa Civil RS</senderName><event>Tempestade</event><severity>Severe</severity><onset>2026-11-23T13:00:00-03:00</onset><expires>2026-11-23T18:00:00-03:00</expires><area><geocode><valueName>IBGE</valueName><value>4314902</value></geocode></area></info></alert>'''
    a=normalizar_cap(raw,now)
    assert len(a)==1 and a[0]["orgao"]=="Defesa Civil" and a[0]["geocodes_rs"]==["4314902"]
    assert normalizar_cap(raw.replace(b"4314902",b"3550308"),now)==[]
    assert normalizar_cap(raw.replace(b"Actual",b"Test"),now)==[]
