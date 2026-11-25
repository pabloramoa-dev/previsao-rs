"""Regressões: apresentação estadual deve seguir o mesmo Reel diário do Previsão RJ."""
from pathlib import Path
import subprocess
import sys
import json
import yaml

from src.previsao.editorial.formats import antes_de_sair, amanha_no_estado
from src.previsao.render.characters.pipeline import PRESETS
from src.previsao.editorial.cinco import cinco_regioes

BASE = Path(__file__).resolve().parents[1]


def _snapshot():
    estado = yaml.safe_load((BASE / "config/estado.yaml").read_text(encoding="utf-8"))
    locais = yaml.safe_load((BASE / "config/locais.yaml").read_text(encoding="utf-8"))
    por_id = {l["id"]: l for l in locais["locations"]}
    pontos = []
    for i, regiao in enumerate(estado["regioes"]):
        local = por_id[regiao["ids"][0]]
        pontos.append({
            "id": local["id"], "name": local["name"], "zone": local["zone"],
            "min_c": 13 + i, "max_c": 21 + i, "rain_mm": round(i * 0.5, 1),
            "rain_probability_pct": None, "wind_gust_max_kmh": None,
        })
    return {
        "forecast": {
            "today": {"date": "2026-11-23", "locations": pontos},
            "tomorrow": {"date": "2026-11-24", "locations": pontos},
        }
    }


def test_apresentadores_mesmo_preset_previsao_rj():
    assert PRESETS["bira"]["voice"] == "pm_alex:0.82+pm_santa:0.18"
    assert PRESETS["bia"]["voice"] == "pf_dora:0.85+af_heart:0.15"
    assert PRESETS["bira"]["speed"] == 1.04
    assert PRESETS["bia"]["speed"] == 1.02


def test_boletins_iguais_estrutura_rj_sem_apresentacao_longa():
    snapshot = _snapshot()
    for roteiro in (antes_de_sair(snapshot, False), amanha_no_estado(snapshot, False)):
        assert roteiro[0]["tipo"] == "nenhum"
        primeira = roteiro[0]["fala"].lower()
        assert "tempo" in primeira and len(primeira.split()) <= 12
        assert "chuva" not in primeira and "milímetro" not in primeira
        assert "graus" in roteiro[1]["fala"]
        assert "eu sou" not in primeira and "olá" not in primeira
        assert not any("incerteza" in b["fala"].lower() for b in roteiro)
        assert any(b["tipo"] == "resumo" for b in roteiro)
        assert roteiro[-1]["tipo"] == "cta"
        assert sum(b["tipo"] == "resumo" for b in roteiro) == 1


def test_quadro_representa_seis_regioes_com_chuva_em_mm():
    snapshot = _snapshot()
    quadro = cinco_regioes(snapshot["forecast"]["today"]["locations"])
    assert len(quadro) == 6
    assert all("chuva_mm" in r for r in quadro)


def test_piloto_usa_motor_normal_nao_comunicado():
    texto = (BASE / ".github/workflows/piloto_previsaors_dupla.yml").read_text(encoding="utf-8")
    assert "hyperframes/gerar_hf.py" in texto
    assert "hyperframes/comunicado_dupla.py" not in texto
    assert "src.previsao.publish.cli" not in texto
    assert "instagram_business_content_publish" not in texto
    assert "--snapshot output/snapshot.json" in texto
    assert "--format" in texto


def test_cli_reel_aceita_os_dois_formatos_estaduais():
    """O CLI nao pode receber uma classe dict vazia como choices."""
    cmd = [sys.executable, "hyperframes/gerar_hf.py", "--help"]
    r = subprocess.run(cmd, cwd=BASE, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert "amanha_no_estado" in r.stdout
    assert "antes_de_sair" in r.stdout
