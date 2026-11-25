"""Boletins diários abrem com a previsão geral, sem antecipar o volume de chuva."""
from src.previsao.editorial.formats import abertura_previsao, antes_de_sair, amanha_no_estado


def test_abertura_curta_sem_chuva():
    for quando in ('hoje', 'amanhã'):
        beat = abertura_previsao(quando)
        fala = beat['fala'].lower()
        assert quando in fala and len(fala.split()) <= 12
        assert beat['tipo'] == 'nenhum' and not beat['dados']
        assert not any(p in fala for p in ('milímetro', 'chuva', 'olá', 'eu sou'))


def test_formatos_diarios_abrem_sem_chuva_e_encerram_com_acumulado(snapshot):
    for chave, montar, quando in (
        ('today', antes_de_sair, 'hoje'),
        ('tomorrow', amanha_no_estado, 'amanhã'),
    ):
        bloco = snapshot['forecast'][chave]
        for loc in bloco['locations']:
            loc['rain_mm'] = 80
        bloco['rain_scan_rs'] = {
            'ponto': {'name': 'Muçum', 'rain_mm': 92.5}, 'validos': 99, 'total': 100}
        beats = montar(snapshot, False)
        assert beats[0]['tipo'] == 'nenhum' and not beats[0]['dados']
        primeira = beats[0]['fala'].lower()
        assert quando in primeira and len(primeira.split()) <= 12
        assert not any(p in primeira for p in ('milímetro', 'chuva', 'olá', 'eu sou'))
        assert any(loc['name'].lower() in primeira for loc in bloco['locations'])
        assert beats[1]['tipo'] == 'gancho' and 'graus' in beats[1]['fala']
        assert any(b['tipo'] == 'resumo' for b in beats[1:-1])
        assert all('milímetro' not in b['fala'].lower() for b in beats[:-1])
        assert beats[-1]['tipo'] == 'alerta'
        assert beats[-1]['dados']['destaque_chuva']
        assert 'Muçum' in beats[-1]['fala'] and '92,5 milímetros' in beats[-1]['fala']


def test_rodizio_de_retencao_e_engajamento():
    from datetime import date, timedelta
    from src.previsao.editorial.formats import gancho_rotativo, engajamento_rotativo
    pontos = [{'name': 'Cidade A', 'min_c': 15, 'max_c': 27},
              {'name': 'Cidade B', 'min_c': 20, 'max_c': 33}]
    ganchos, ctas = set(), set()
    for i in range(28):
        pub = date(2026, 11, 1) + timedelta(days=i // 2)
        quando = 'amanhã' if i % 2 else 'hoje'
        alvo = pub + timedelta(days=i % 2)
        fala = gancho_rotativo(pontos, alvo, quando, canal='teste')
        assert quando in fala.lower() and len(fala.split()) <= 12
        assert 'Cidade A' in fala or 'Cidade B' in fala
        assert not any(x in fala.lower() for x in ('alerta', 'rajada', 'chuva forte'))
        assert fala == gancho_rotativo(pontos, alvo, quando, canal='teste')
        ganchos.add(fala)
        ctas.add(engajamento_rotativo(alvo, quando, canal='teste'))
    assert len(ganchos) >= 12
    assert len(ctas) >= 8
