"""Abertura dos boletins diários.

Regra editorial vigente: com 50 mm ou mais previstos em 24 h o vídeo ABRE com
alerta localizado, antes das temperaturas; abaixo disso, gancho localizado do
rodízio. O destaque da maior chuva continua no encerramento.
"""
import pytest

from src.previsao.editorial.formats import (abertura_chuva_24h, abertura_previsao,
                                            antes_de_sair, amanha_no_estado)


def test_abertura_curta_sem_chuva():
    for quando in ('hoje', 'amanhã'):
        beat = abertura_previsao(quando)
        fala = beat['fala'].lower()
        assert quando in fala and len(fala.split()) <= 12
        assert beat['tipo'] == 'nenhum' and not beat['dados']
        assert not any(p in fala for p in ('milímetro', 'chuva', 'olá', 'eu sou'))


def _chover(bloco, mm, pico=None):
    for loc in bloco['locations']:
        loc['rain_mm'] = mm
    bloco['rain_scan_rs'] = {
        'ponto': {'name': 'Muçum', 'rain_mm': mm if pico is None else pico},
        'validos': 99, 'total': 100}


FORMATOS = (('today', antes_de_sair, 'hoje'), ('tomorrow', amanha_no_estado, 'amanhã'))


def test_formatos_sem_grande_volume_abrem_com_gancho_localizado(snapshot):
    """Abaixo de 50 mm a abertura é o gancho localizado do rodízio, sem chuva."""
    for chave, montar, quando in FORMATOS:
        bloco = snapshot['forecast'][chave]
        _chover(bloco, 20, 49.9)
        beats = montar(snapshot, False)
        primeira = beats[0]['fala'].lower()
        assert not beats[0]['dados'].get('alerta_chuva_24h')
        assert quando in primeira and len(primeira.split()) <= 12
        assert not any(p in primeira for p in ('milímetro', 'chuva', 'olá', 'eu sou'))
        assert any(loc['name'].lower() in primeira for loc in bloco['locations'])
        assert beats[-1]['dados']['destaque_chuva']
        assert 'Muçum' in beats[-1]['fala'] and '49,9 milímetros' in beats[-1]['fala']


def test_grande_volume_abre_com_alerta_localizado_e_preserva_destaque_final(snapshot):
    """Regra editorial vigente: >= 50 mm em 24 h abre o vídeo, antes das temperaturas."""
    for chave, montar, quando in FORMATOS:
        bloco = snapshot['forecast'][chave]
        _chover(bloco, 80, 92.5)
        beats = montar(snapshot, False)
        abertura = beats[0]
        assert abertura['tipo'] == 'gancho' and abertura['dados']['alerta_chuva_24h']
        assert abertura['fala'].startswith('Se você mora em ')
        assert 'preste atenção' in abertura['fala']
        assert f'previsto {quando}' in abertura['fala']
        assert 'Muçum' in abertura['fala'] and '92,5 milímetros' in abertura['fala']
        assert 'defesa civil' not in abertura['fala'].lower()
        # Temperaturas vêm DEPOIS do alerta.
        assert 'graus' not in abertura['fala']
        assert any('graus' in b['fala'] for b in beats[1:])
        assert any(b['tipo'] == 'resumo' for b in beats[1:-1])
        # Encerramento continua com a localidade de maior volume.
        assert beats[-1]['tipo'] == 'alerta' and beats[-1]['dados']['destaque_chuva']
        assert 'Muçum' in beats[-1]['fala'] and '92,5 milímetros' in beats[-1]['fala']


@pytest.mark.parametrize('mm, obrigatorio', [
    (49.9, False), (50, True), (80, True), (100, True), (143.2, True)])
def test_limiar_de_50_mm(mm, obrigatorio):
    bloco = {'locations': [{'name': 'Cidade A', 'rain_mm': mm}, {'name': 'Cidade B', 'rain_mm': 3}]}
    for quando in ('hoje', 'amanhã'):
        beat = abertura_chuva_24h(bloco, quando)
        if not obrigatorio:
            assert beat is None
            continue
        assert beat is not None and beat['dados']['alerta_chuva_24h']
        assert 'Se você mora em Cidade A, preste atenção!' in beat['fala']
        assert 'Cidade B' not in beat['fala']
        assert f'{mm:g}'.replace('.', ',') + ' milímetros' in beat['fala']


@pytest.mark.parametrize('valor', [None, 'muito', float('nan'), float('inf'), True, -5])
def test_dados_ausentes_ou_invalidos_nao_geram_alerta_falso(valor):
    bloco = {'locations': [{'name': 'Cidade A', 'rain_mm': valor}, {'name': None, 'rain_mm': 120},
                           {'name': 'Cidade B'}]}
    assert abertura_chuva_24h(bloco, 'amanhã') is None
    assert abertura_chuva_24h({}, 'hoje') is None


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
