from datetime import datetime
from zoneinfo import ZoneInfo
from scripts.alerta_auto_rs import escolher, roteiro, nivel

AGORA = datetime(2026, 11, 23, 12, 30, tzinfo=ZoneInfo("America/Sao_Paulo"))


def aviso(id_, sev="Perigo", tipo="Tempestade", n=40):
    return {"id_aviso": id_, "tipo": tipo, "severidade": sev,
            "inicio": "2026-11-23T10:00:00-03:00", "fim": "2026-11-24T10:00:00-03:00",
            "municipios_rs": n, "geocodes_rs": ["4314902"],
            "municipios_texto": "Porto Alegre - RS (4314902), Canoas - RS (4304606)",
            "riscos": "Granizo e queda de árvores. Corte de energia elétrica.",
            "instrucoes": "Em caso de rajadas de vento, não se abrigue debaixo de árvores."}


def test_escolhe_mais_severo_e_nao_repete():
    a, b = aviso("1", "Perigo potencial"), aviso("2", "Grande Perigo")
    assert escolher([a, b], {"registros": []})["id_aviso"] == "2"
    hist = {"registros": [{"id_aviso": "2", "nivel": 3}, {"id_aviso": "1", "nivel": 1}]}
    assert escolher([a, b], hist) is None


def test_republica_se_severidade_sobe():
    hist = {"registros": [{"id_aviso": "1", "nivel": 1}]}
    assert escolher([aviso("1", "Perigo")], hist)["id_aviso"] == "1"


def test_roteiro_so_com_dados_oficiais():
    a = aviso("1")
    r = roteiro(a, [a, aviso("9", tipo="Acumulado de Chuva")], AGORA)
    assert r["falas"][0]["cena"] == "abertura" and r["falas"][-1]["cena"] == "cta"
    assert "{arroba}" in r["legenda"] and "Porto Alegre" in r["legenda"]
    assert r["validade"] == "2026-11-24T10:00"
    assert nivel("Grande Perigo") == 3


def test_aviso_longo_cabe_no_orcamento_sem_perder_o_essencial():
    """Run 46072589094: riscos e instruções longos do INMET geraram alerta de 52 s."""
    from scripts.alerta_auto_rs import MAX_PALAVRAS_ALERTA
    a = aviso("7", "Grande Perigo")
    a["riscos"] = ("Corte de energia elétrica, queda de galhos de árvores, alagamentos e "
                   "descargas elétricas em diversas áreas urbanas e rurais. "
                   "Estragos em plantações, danos em edificações e transtornos no transporte rodoviário.")
    a["instrucoes"] = ("Em caso de rajadas de vento: não se abrigue debaixo de árvores, pois há "
                       "risco de queda e descargas elétricas, e não estacione veículos próximos a "
                       "torres de transmissão e placas de propaganda.")
    outros = [aviso(str(i), tipo=t) for i, t in enumerate(["Vendaval", "Acumulado de Chuva", "Granizo"], 20)]
    r = roteiro(a, [a, *outros], AGORA)
    total = sum(len(f["fala"].split()) for f in r["falas"])
    assert total <= MAX_PALAVRAS_ALERTA
    falas = " ".join(f["fala"] for f in r["falas"])
    assert falas.startswith("Atenção, Rio Grande do Sul!")
    assert "O aviso vale" in falas and "199" in falas and "193" in falas
    assert r["falas"][-1]["cena"] == "cta"
    # A legenda continua com tudo (riscos completos e outros avisos).
    assert "Estragos em plantações" in r["legenda"] and "Vendaval" in r["legenda"]


def test_aviso_curto_mantem_todas_as_falas():
    a = aviso("1")
    r = roteiro(a, [a, aviso("9", tipo="Vendaval")], AGORA)
    falas = " ".join(f["fala"] for f in r["falas"])
    assert "Riscos apontados" in falas and "Também há aviso oficial" in falas
    assert "não se abrigue" in falas
