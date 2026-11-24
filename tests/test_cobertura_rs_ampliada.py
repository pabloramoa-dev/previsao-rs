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
assert len(config.load_places()['locations']) >= 100
for day in (date(2026,11,24), date(2026,11,25)):
    a = config.locations_for_reel(day, 'manha')
    b = config.locations_for_reel(day, 'noite')
    assert len(a) == len(b) == 6
    assert len({p['zone'] for p in a+b}) == 12
    for group in (a,b):
        pts = [dict(p,min_c=12,max_c=25) for p in group]
        assert len(cinco_regioes(pts)) == 6
"""
    result = subprocess.run([sys.executable,'-c',code], cwd=ROOT, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
