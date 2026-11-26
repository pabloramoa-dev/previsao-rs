"""Busca o maior acumulado no cadastro do RS sem mudar o quadro de seis cidades."""
from math import isfinite
from .. import config


def valido(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value) and value >= 0


def anexar_varredura(snapshot, cadastro, pontos):
    """Cruza volumes extras com o dia exato da previsão, preservando o rodízio.

    Dados ausentes nunca viram zero. Registra a cobertura de cada dia.
    """
    for bloco in snapshot['forecast'].values():
        if not isinstance(bloco, dict) or 'date' not in bloco or 'locations' not in bloco:
            continue
        localizados = {loc['id']: loc for loc in bloco['locations']}
        volumes = []
        for local in cadastro:
            ident = local['id']
            if ident in localizados:
                mm = localizados[ident].get('rain_mm')
            else:
                daily = pontos.get(ident, {}).get('daily') or {}
                dates = daily.get('time') or []
                sums = daily.get('precipitation_sum') or []
                i = dates.index(bloco['date']) if bloco['date'] in dates else -1
                mm = sums[i] if 0 <= i < len(sums) else None
            if valido(mm):
                volumes.append({'id': ident, 'name': local['name'], 'rain_mm': round(mm, 1)})
        bloco['rain_scan_rs'] = {
            'ponto': max(volumes, key=lambda p: p['rain_mm'], default=None),
            'pontos': [p for p in volumes if p['rain_mm'] >= 50],
            'validos': len(volumes), 'total': len(cadastro),
        }


def destaque_chuva(snapshot, formato, candidate=None):
    forecast = snapshot['forecast']
    chave = 'tomorrow' if formato == 'amanha_no_estado' else 'today'
    bloco = forecast.get(chave) or {}
    quando = 'amanhã' if chave == 'tomorrow' else 'hoje'
    if formato == 'fim_de_semana':
        datas = ((candidate or {}).get('extra') or {}).get('dates') or []
        blocos = [b for b in forecast.values() if isinstance(b, dict)
                  and b.get('date') in datas and 'rain_scan_rs' in b]
        if blocos:
            bloco = max(blocos, key=lambda b: (b['rain_scan_rs'].get('ponto') or {}).get('rain_mm', -1))
            quando = 'no dia ' + bloco['date'][8:10]
    scan = bloco.get('rain_scan_rs')
    if scan is None:
        return None
    ponto = scan.get('ponto')
    forte = bool(ponto and ponto['rain_mm'] >= config.load_thresholds().get('rain_highlight_heavy_mm', 50))
    return dict(scan, quando=quando, forte=forte)
