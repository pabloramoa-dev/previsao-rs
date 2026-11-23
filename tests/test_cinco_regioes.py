"""Regras do quadro meteorológico RS: seis cidades reais, seis regiões."""
from datetime import date

import pytest

from src.previsao import config, estado
from src.previsao.editorial.cinco import cinco_regioes, fala_resumo, faltando
from src.previsao.editorial.formats import antes_de_sair, amanha_no_estado
from src.previsao.editorial.duracao import cortar_para_janela


def locais(dia=date(2026, 11, 23)):
    return [
        {"id": p["id"], "name": p["name"], "zone": p["zone"],
         "min_c": 12 + i, "max_c": 25 + i,
         "rain_mm": float(i), "rain_probability_pct": None,
         "wind_gust_max_kmh": None}
        for i, p in enumerate(config.locations_for_reel(dia))
    ]


def test_seis_municipios_na_ordem_das_regioes():
    pontos = locais()
    linhas = cinco_regioes(pontos)
    assert [l["nome"] for l in linhas] == [l["name"] for l in pontos]
    assert [l["regiao"] for l in linhas] == [r for r, _, _ in estado.regioes()]
    assert [l["id"] for l in linhas] == [l["id"] for l in pontos]
    assert faltando(linhas) == []


def test_regiao_com_ancora_ausente_usa_municipio_cadastrado_na_mesma_regiao():
    pontos = locais()
    regiao, ids, zonas = estado.regioes()[0]
    outro = next(x for x in config.load_places()["locations"]
                 if x["zone"] in zonas and x["id"] != pontos[0]["id"])
    substituto = dict(pontos[0], id=outro["id"], name=outro["name"], zone=outro["zone"])
    linhas = cinco_regioes([substituto] + pontos[1:])
    assert linhas[0]["nome"] == outro["name"]
    assert linhas[0]["regiao"] == regiao


def test_regiao_sem_dados_nao_empresta_numeros_e_explica_falta():
    pontos = locais()
    region_missing = estado.regioes()[0][0]
    pontos = pontos[1:]
    # Outro ponto de uma região já coberta poderá aparecer como linha extra,
    # sem ser apresentado falsamente como previsão da primeira região.
    outro = next(x for x in config.load_places()["locations"]
                 if x["zone"] == pontos[0]["zone"] and x["id"] != pontos[0]["id"])
    extra = dict(pontos[0], id=outro["id"], name=outro["name"])
    linhas = cinco_regioes(pontos + [extra])
    assert region_missing in faltando(linhas)
    assert len(linhas) == 6
    assert linhas[-1]["regiao"] is None
    assert linhas[-1]["nome"] == extra["name"]


def test_ponto_sem_minima_maxima_fica_de_fora():
    pontos = locais()
    pontos[1].pop("min_c")
    linhas = cinco_regioes(pontos)
    assert pontos[1]["name"] not in [l["nome"] for l in linhas]
    assert all(l["min"] is not None for l in linhas)


def test_resumo_fala_os_seis_municipios():
    pontos = locais()
    fala = fala_resumo(cinco_regioes(pontos))
    assert all(p["name"] in fala for p in pontos)
    assert "graus" in fala


@pytest.mark.parametrize("amanha", [False, True])
def test_reel_mostra_cartao_das_seis_regioes(amanha):
    pontos = locais()
    snapshot = {"forecast": {"today": {"date": "2026-11-23", "locations": pontos},
                             "tomorrow": {"date": "2026-11-24", "locations": pontos}}}
    batidas = amanha_no_estado(snapshot, False) if amanha else antes_de_sair(snapshot, False)
    resumos = [b for b in batidas if b["tipo"] == "resumo"]
    assert len(resumos) == 1
    assert [c["nome"] for c in resumos[0]["dados"]["cidades"]] == [p["name"] for p in pontos]
    assert len(resumos[0]["dados"]["cidades"]) == 6


def test_corte_por_duracao_nunca_remove_cartao():
    pontos = locais()
    snapshot = {"forecast": {"today": {"date": "2026-11-23", "locations": pontos},
                             "tomorrow": {"date": "2026-11-24", "locations": pontos}}}
    batidas = antes_de_sair(snapshot, False)
    ficam, _ = cortar_para_janela(batidas, [9.0] * len(batidas))
    assert any(b["tipo"] == "resumo" for b in ficam)
