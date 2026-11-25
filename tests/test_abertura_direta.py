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
        assert beats[0] == abertura_previsao(quando)
        assert beats[1]['tipo'] == 'gancho' and 'graus' in beats[1]['fala']
        assert any(b['tipo'] == 'resumo' for b in beats[1:-1])
        assert all('milímetro' not in b['fala'].lower() for b in beats[:-1])
        assert beats[-1]['tipo'] == 'alerta'
        assert beats[-1]['dados']['destaque_chuva']
        assert 'Muçum' in beats[-1]['fala'] and '92,5 milímetros' in beats[-1]['fala']
