from pathlib import Path
import subprocess
import sys
import os

ROOT = Path(__file__).resolve().parents[1]

def test_cobertura_real_e_turnos_complementares():
    env = dict(os.environ, PREVISAO_CONFIG_DIR=str(ROOT / 'config'))
    code = """
from datetime import date
from src.previsao import config, estado
from src.previsao.editorial.cinco import cinco_regioes
assert len(estado.regioes()) == 12
assert len(config.load_places()['locations']) >= 180
from src.previsao.editorial.cobertura_rs import cadastro_estadual, lote_varredura
from datetime import timedelta
assert len(cadastro_estadual()) == 497
for day in (date(2026,11,24), date(2026,11,25)):
    a = config.locations_for_reel(day, 'manha')
    b = config.locations_for_reel(day, 'noite')
    assert len(a) == len(b) == 6
    assert len({p['zone'] for p in a+b}) == 12
    noite_anterior = config.locations_for_reel(day-timedelta(days=1), 'noite')
    assert len({p['zone'] for p in a+noite_anterior}) == 12
    lote = lote_varredura(cadastro_estadual(), a, day, 'manha')
    assert len({p['id'] for p in lote}) == len(lote)
    assert len([p for p in lote if 'zone' not in p]) == 48
    for group in (a,b):
        pts = [dict(p,min_c=12,max_c=25) for p in group]
        assert len(cinco_regioes(pts)) == 6
"""
    result = subprocess.run([sys.executable,'-c',code], cwd=ROOT, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr

def test_municipios_e_prioridades():
    from scripts.alerta_auto_rs import municipios, nomes_ibge
    cadastro = nomes_ibge()
    assert len(cadastro) == 497
    codigo = next(c for c,n in cadastro.items() if n == 'Tupanciretã')
    assert municipios({'geocodes_rs':[codigo]}) == ['Tupanciretã']
    assert municipios({'geocodes_rs':['4314902'], 'municipios_texto':'Canoas - RS (4304606)'}) == ['Porto Alegre']
