from datetime import date
from src.previsao.editorial.cobertura_rs import priorizar, risco, pauta_local

def test_prioridade_meteorologica_sem_trocar_regiao():
    a = {'id':'a','zone':'z','sample_tier':2}
    b = {'id':'b','zone':'z','sample_tier':2}
    c = {'id':'c','zone':'outra','sample_tier':2}
    dia = '2026-11-25'
    def dado(mm):
        return {'daily': {'time':[dia], 'temperature_2m_min':[12], 'temperature_2m_max':[24], 'precipitation_sum':[mm]}}
    assert priorizar([a], [a,b,c], {'a':dado(1),'b':dado(70),'c':dado(100)},dia) == [b]
    assert priorizar([a], [a,b], {'a':dado(1)},dia) == [a]
    assert risco({},dia) == (0,0)

def test_pautas_sem_dados_nao_inventam():
    assert pauta_local([],set()) is None
    assert 'geada' in pauta_local([{'name':'Vacaria','min_c':2}],set())
    assert 'litoral' in pauta_local([{'id':'torres','name':'Torres','min_c':15,'wind_max_kmh':40}],{'torres'})
