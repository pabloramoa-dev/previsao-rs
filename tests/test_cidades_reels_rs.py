"""Os seis nomes do quadro e da fala pertencem aos municípios coletados."""
from datetime import date
from pathlib import Path

from src.previsao import config, estado
from src.previsao.editorial.cinco import cinco_regioes, fala_resumo


def _pontos(cidades):
    return [
        dict(id=p["id"], name=p["name"], zone=p["zone"],
             min_c=12 + i, max_c=25 + i, rain_mm=i * 1.25)
        for i, p in enumerate(cidades)
    ]


def test_rodizio_seis_regioes_e_seis_cidades_reais():
    for data in (date(2026, 11, 23), date(2026, 11, 24), date(2026, 12, 1)):
        cidades = config.locations_for_reel(data)
        assert len(cidades) == 6
        assert len({p["id"] for p in cidades}) == 6
        for (regiao, ids, zonas), cidade in zip(estado.regioes(), cidades):
            assert cidade["id"] in ids or cidade["zone"] in zonas
            assert cidade["name"]


def test_rodizio_muda_os_municipios_e_e_deterministico():
    hoje = config.locations_for_reel(date(2026, 11, 23))
    amanha = config.locations_for_reel(date(2026, 11, 24))
    hoje_novamente = config.locations_for_reel(date(2026, 11, 23))
    assert [l["id"] for l in hoje] == [l["id"] for l in hoje_novamente]
    assert [l["id"] for l in hoje] != [l["id"] for l in amanha]


def test_tela_cidade_regiao_e_valores_do_mesmo_ponto():
    pontos = _pontos(config.locations_for_reel(date(2026, 11, 23)))
    linhas = cinco_regioes(pontos)
    assert len(linhas) == 6
    assert [l["nome"] for l in linhas] == [l["name"] for l in pontos]
    assert [l["regiao"] for l in linhas] == [r for r, _, _ in estado.regioes()]
    for original, linha in zip(pontos, linhas):
        assert linha["min"] == original["min_c"]
        assert linha["max"] == original["max_c"]
        assert linha["chuva_mm"] == original["rain_mm"]


def test_fala_menciona_as_cidades_nao_apenas_as_regioes():
    cidades = config.locations_for_reel(date(2026, 11, 23))
    linhas = cinco_regioes(_pontos(cidades))
    fala = fala_resumo(linhas)
    for cidade in cidades:
        assert cidade["name"] in fala


def test_workflows_usam_rodizio_sem_publicar_piloto():
    root = Path(__file__).resolve().parents[1]
    for wf in ("reel_manha.yml", "reel_noite.yml", "piloto_previsaors_dupla.yml"):
        s = (root / ".github/workflows" / wf).read_text(encoding="utf-8")
        assert "scripts.collect_live output/snapshot.json --rodizio" in s
    p = (root / ".github/workflows/piloto_previsaors_dupla.yml").read_text(encoding="utf-8")
    assert "python -m src.previsao.publish.cli" not in p


def test_tela_exibe_cidade_e_regiao_separadamente():
    s = (Path(__file__).resolve().parents[1] / "hyperframes/compor.py").read_text(encoding="utf-8")
    assert 'class="qd-regiao"' in s
    assert 'class="qd-cidade"' in s
