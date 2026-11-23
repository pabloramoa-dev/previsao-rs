"""O piloto gaúcho abre diretamente com dados reais das cidades."""
import datetime as dt
from zoneinfo import ZoneInfo

import pytest
import yaml

from scripts.roteiro_piloto_dupla_rs import montar, REGIOES


def _snapshot():
    agora = dt.datetime.now(ZoneInfo("America/Sao_Paulo"))
    data = (agora + dt.timedelta(days=1)).date().isoformat()
    nomes = ["Porto Alegre", "Caxias do Sul", "Tramandaí", "Pelotas", "Santa Maria", "Passo Fundo"]
    locais = [
        {"id": ident, "name": nomes[i], "min_c": 13 + i, "max_c": 24 + i,
         "rain_mm": float(i)}
        for i, (_, ident) in enumerate(REGIOES)
    ]
    return {
        "generated_at": agora.isoformat(),
        "sources": [{"name": "met_no_forecast", "status": "ok"}],
        "forecast": {"tomorrow": {"date": data, "locations": locais}},
    }


def test_começa_pela_previsao_e_dupla_alterna(tmp_path):
    path = tmp_path / "piloto.yaml"
    montar(_snapshot(), path)
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    falas = doc["falas"]
    assert falas[0]["cena"] == "abertura"
    assert falas[0]["fala"].startswith("Porto Alegre terá mínima de")
    assert falas[0]["quem"] == "bia" and falas[1]["quem"] == "bira"
    assert sum(f["cena"] in ("numero", "abertura") for f in falas) == 6
    assert not any("eu sou" in f["fala"].lower() or "olá" in f["fala"].lower()
                   for f in falas)
    assert "@previsaors" in doc["legenda"]


def test_sem_dados_nao_inventa_tempo(tmp_path):
    dados = _snapshot()
    dados["forecast"]["tomorrow"]["locations"][0]["rain_mm"] = None
    with pytest.raises(ValueError, match="Dados insuficientes"):
        montar(dados, tmp_path / "recusar.yaml")
