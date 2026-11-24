from src.previsao.editorial.chuva_rs import anexar_varredura, destaque_chuva
from src.previsao.editorial.formats import batida_final_chuva, antes_de_sair, amanha_no_estado
from src.previsao.editorial.duracao import cortar_para_janela
from src.previsao.publish.caption import build_caption


def test_varredura_busca_fora_do_rodizio_e_separa_os_dias():
    cadastro = [{'id': 'a', 'name': 'Cidade A'}, {'id': 'b', 'name': 'Cidade B'},
                {'id': 'c', 'name': 'Cidade C'}]
    doc = {'forecast': {'today': {'date': '2026-11-24', 'locations': [
        {'id': 'a', 'rain_mm': 5}]}, 'tomorrow': {'date': '2026-11-25', 'locations': [
        {'id': 'a', 'rain_mm': 20}]}}}
    extra = {'b': {'daily': {'time': ['2026-11-24', '2026-11-25'],
                             'precipitation_sum': [83.4, 2]}}}
    anexar_varredura(doc, cadastro, extra)
    hoje = destaque_chuva(doc, 'antes_de_sair')
    amanha = destaque_chuva(doc, 'amanha_no_estado')
    assert hoje['ponto']['name'] == 'Cidade B' and hoje['ponto']['rain_mm'] == 83.4
    assert hoje['forte'] and hoje['validos'] == 2 and hoje['total'] == 3
    assert amanha['ponto']['name'] == 'Cidade A' and not amanha['forte']
    assert len(doc['forecast']['today']['locations']) == 1
    alerta = batida_final_chuva(doc, 'antes_de_sair')
    assert alerta['tipo'] == 'alerta' and '83,4 milímetros' in alerta['fala']
    assert 'Cidade B' in alerta['dados']['detalhe']
    assert batida_final_chuva(doc, 'amanha_no_estado')['tipo'] == 'gancho'


def test_destaque_final_dos_dois_turnos_sobrevive_ao_corte(snapshot):
    for chave, montar, formato in (
        ('today', antes_de_sair, 'antes_de_sair'),
        ('tomorrow', amanha_no_estado, 'amanha_no_estado'),
    ):
        snapshot['forecast'][chave]['rain_scan_rs'] = {
            'ponto': {'name': 'Muçum', 'rain_mm': 92.5}, 'validos': 99, 'total': 100}
        beats = montar(snapshot, False)
        assert beats[-1]['dados']['destaque_chuva']
        assert beats[-1]['tipo'] == 'alerta'
        assert 'Muçum' in beats[-1]['fala']
        finais, _ = cortar_para_janela(beats, [10] * len(beats))
        assert finais[-1] == beats[-1]
        legenda = build_caption(snapshot, {'format': formato})
        assert 'Muçum, 92,5 mm previstos' in legenda
        assert '99/100' in legenda and 'não aviso oficial' in legenda


def test_sem_dados_nao_inventa_zero_nem_alerta():
    doc = {'forecast': {'today': {'rain_scan_rs': {'ponto': None, 'validos': 0, 'total': 100}}}}
    beat = batida_final_chuva(doc, 'antes_de_sair')
    assert beat['tipo'] == 'nenhum' and 'indisponível' in beat['fala']
