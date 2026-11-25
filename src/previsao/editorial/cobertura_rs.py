"""Amostra estadual com rodízio, orçamento de tempo e prioridade meteorológica."""
from datetime import date
from math import isfinite
import json
from .. import config

def cadastro_estadual():
    core = config.locations_by_tier(3)
    path = config.ROOT / 'data' / 'locais_rs_varredura.json'
    extra = json.loads(path.read_text(encoding='utf-8'))['locations'] if path.exists() else []
    return core + extra

def lote_varredura(cadastro, selecionados, dia, turno, limite_extra=48):
    """Distribui a consulta pelas 12 zonas e alterna os municípios de apoio.
    O limite de tempo do coletor pode reduzir a cobertura: nunca é garantida.
    """
    ids = {p['id'] for p in selecionados}
    core = [p for p in cadastro if 'zone' in p and p['id'] not in ids]
    extra = [p for p in cadastro if 'zone' not in p and p['id'] not in ids]
    passo = dia.toordinal() * 2 + int(turno == 'noite')
    grupos = {}
    for p in core:
        grupos.setdefault(p['zone'], []).append(p)
    for z, ps in grupos.items():
        shift = passo % len(ps)
        grupos[z] = ps[shift:] + ps[:shift]
    fila = [ps[i] for i in range(max(map(len, grupos.values()), default=0))
            for ps in grupos.values() if i < len(ps)]
    if extra:
        offset = (passo * limite_extra) % len(extra)
        apoio = (extra[offset:] + extra[:offset])[:limite_extra]
        # Intercalar, para que o teto de tempo não exclua sempre os extras.
        for i, p in enumerate(apoio):
            fila.insert(min(4*i+3, len(fila)), p)
    return fila

def valor(raw, campo, dia):
    daily = raw.get('daily') or {}
    dates = daily.get('time') or []
    values = daily.get(campo) or []
    if dia not in dates or dates.index(dia) >= len(values):
        return None
    v = values[dates.index(dia)]
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) and isfinite(v) else None

def risco(raw, dia):
    if valor(raw, 'temperature_2m_min', dia) is None or valor(raw, 'temperature_2m_max', dia) is None:
        return (0, 0)
    rain = valor(raw, 'precipitation_sum', dia)
    wind = valor(raw, 'wind_speed_10m_max', dia)
    code = valor(raw, 'weather_code', dia)
    cold = valor(raw, 'temperature_2m_min', dia)
    if rain is not None and rain >= 50:
        return (4, rain)
    if code is not None and code >= 95:
        return (3, rain or 0)
    if wind is not None and wind >= 50:
        return (2, wind)
    if cold is not None and cold <= 3:
        return (1, -cold)
    return (0, 0)

def priorizar(selecionados, cadastro, pontos, dia):
    """Substitui somente dentro da mesma zona e com dados de temperatura válidos."""
    saida = []
    for atual in selecionados:
        melhor = atual
        nota = risco(pontos.get(atual['id'], {}), dia)
        for candidato in cadastro:
            if candidato.get('zone') != atual['zone'] or candidato.get('sample_tier', 3) > 2:
                continue
            outra = risco(pontos.get(candidato['id'], {}), dia)
            if outra > nota:
                melhor, nota = candidato, outra
        saida.append(melhor)
    return saida

def pauta_local(locs, coastal_names):
    """Informação meteorológica local, não diagnóstico nem alerta oficial."""
    valid = [l for l in locs if isinstance(l.get('min_c'), (int,float))]
    if valid:
        cold = min(valid, key=lambda l: l['min_c'])
        if cold['min_c'] <= 3:
            return f"{cold['name']}: mínima de {cold['min_c']:g} graus; atenção à possibilidade de geada em áreas rurais."
    for l in locs:
        if l.get('id') in coastal_names:
            w = l.get('wind_max_kmh')
            if isinstance(w, (int,float)) and w >= 35:
                return f"{l['name']}: vento sustentado de até {w:g} quilômetros por hora; cuidado no litoral."
    return None
