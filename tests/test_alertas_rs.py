from datetime import datetime
from zoneinfo import ZoneInfo
import pytest
from scripts.monitor_alertas_rs import normalizar
AGORA=datetime(2026,11,20,14,tzinfo=ZoneInfo("America/Sao_Paulo"))
def a(id_,geo):
    return dict(id_aviso=id_,id_sequencia=1,descricao="Tempestade",geocodes=geo,encerrado=False,
        data_inicio="2026-11-20T00:00:00.000Z",hora_inicio="09:00",
        data_fim="2026-11-20T00:00:00.000Z",hora_fim="23:00")
def test_so_rs_e_dedup():
    x=normalizar(dict(hoje=[a("1","4305108,3550308")],futuro=[a("1","4305108"),a("2","3550308")]),AGORA)
    assert len(x)==1 and x[0]["municipios_rs"]==1
def test_expirado_ignorado():
    v=a("1","4305108");v["hora_fim"]="12:00"
    assert not normalizar(dict(hoje=[v],futuro=[]),AGORA)
def test_formato_invalido():
    with pytest.raises(ValueError):normalizar(dict(hoje=[]),AGORA)
