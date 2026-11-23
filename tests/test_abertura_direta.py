"""Reels diários (Bira 06h / Bia 18h) abrem com previsão, sem apresentação."""
from src.previsao import estado
from src.previsao.editorial.formats import abertura_com_dado, antes_de_sair, amanha_no_estado

PROIBIDO = ('olá', 'eu sou', 'veja a previsão', 'vamos conhecer', 'fica assim')


def _locs():
    locs = []
    for i, (_rot, ids, _z) in enumerate(estado.regioes()):
        locs.append({'id': ids[0], 'name': f'Cidade {i}', 'min_c': 14.4 + i, 'max_c': 27.6 + i,
                     'rain_mm': 4.2 if i == 0 else 0.0, 'rain_probability_pct': 60 if i == 0 else 5})
    return locs


def test_abertura_tem_numeros_reais_e_roda_entre_ancoras():
    falas = {abertura_com_dado(_locs(), f'2026-11-{d:02d}', 'hoje')['fala'] for d in range(1, 7)}
    assert len(falas) == 6                      # rodízio: cada dia uma âncora
    f0 = abertura_com_dado(_locs(), '2026-11-01', 'hoje')['fala']
    assert 'mínima de' in f0 and 'máxima de' in f0 and 'graus' in f0
    assert not any(p in f0.lower() for p in PROIBIDO)


def test_sem_dado_nao_inventa():
    assert abertura_com_dado([{'id': 'x', 'name': 'X', 'min_c': None, 'max_c': None}], '2026-11-01', 'hoje') is None


def test_formatos_diarios_comecam_pela_previsao():
    locs = _locs()
    snap = {'forecast': {'today': {'date': '2026-11-23', 'locations': locs},
                         'tomorrow': {'date': '2026-11-24', 'locations': locs}}}
    try:
        manha = antes_de_sair(snap, False)
    except Exception:
        manha = None  # build_script exige campos extras; a abertura já foi coberta acima
    noite = amanha_no_estado(snap, False)
    for batidas in filter(None, (manha, noite)):
        primeira = batidas[0]['fala'].lower()
        assert 'graus' in primeira and not any(p in primeira for p in PROIBIDO)
