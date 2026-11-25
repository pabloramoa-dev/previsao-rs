"""Coleta ao vivo e grava o snapshot do dia.

Uso:
    python -m scripts.collect_live output/snapshot.json [--tier 1] [--previous output/anterior.json]

Fase 1 do Plano Mestre: previsao multi-modelo + observacao (quando ligada) +
score de confianca, tudo com procedencia. Nao publica nada.
"""
from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timedelta
from dataclasses import replace
from pathlib import Path

from src.previsao import config, estado
from src.previsao.collectors import met_no, observations, open_meteo, marine
from src.previsao.normalizers import snapshot as snap


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("out", nargs="?", default="output/snapshot.json")
    parser.add_argument("--tier", type=int, default=1,
                        help="1 = ancoras do Reel-base; 2 inclui as zonas de apoio")
    parser.add_argument("--previous", help="snapshot anterior, para consistencia temporal")
    parser.add_argument("--rodizio", action="store_true",
                        help="Reel RS: escolher uma cidade diferente por região a cada dia")
    parser.add_argument('--turno', choices=['manha', 'noite'], default='manha')
    args = parser.parse_args()

    locations = (config.locations_for_reel(turno=args.turno)
                 if args.rodizio else config.locations_by_tier(args.tier))
    if not locations:
        raise SystemExit(f"nenhum local no tier {args.tier}")

    collected = open_meteo.fetch_all_models(locations)
    # Provedor independente entra como mais um "modelo": e o que faz a
    # concordancia da secao 5.2 medir divergencia entre PROVEDORES, e nao so
    # entre modelos servidos pelo mesmo lugar.
    collected.update(met_no.collect(locations))
    observed = observations.collect(locations)

    previous = None
    if args.previous and Path(args.previous).exists():
        previous = json.loads(Path(args.previous).read_text(encoding="utf-8"))

    cadastro, pontos = [], {}
    if args.rodizio:
        from src.previsao.editorial.cobertura_rs import cadastro_estadual, lote_varredura, priorizar
        cadastro = cadastro_estadual()
        hoje = datetime.now(estado.fuso()).date()
        extras = lote_varredura(cadastro, locations, hoje, args.turno)
        complemento = met_no.fetch(extras, max_seconds=240)
        pontos = (complemento.payload or {}).get('points', {}) if complemento.usable else {}
        principal = collected.get(met_no.MODEL)
        if principal and principal.usable:
            todos = dict((principal.payload or {}).get('points', {}))
            todos.update(pontos)
            # O canal usa MET Norway; não misturar dados de uma seleção antiga
            # se no futuro outros modelos forem ativados.
            if not config.source(open_meteo.SOURCE).get('enabled', False):
                alvo = (hoje + timedelta(days=int(args.turno == 'noite'))).isoformat()
                novas = priorizar(locations, cadastro, todos, alvo)
                if [p['id'] for p in novas] != [p['id'] for p in locations]:
                    locations = novas
                    collected[met_no.MODEL] = replace(principal, payload={'model': met_no.MODEL, 'points': todos},
                        age_minutes=max(principal.age_minutes, complemento.age_minutes))
                    observed = observations.collect(locations)
            pontos = todos

    document = snap.build(collected, locations,
                          previous_snapshot=previous, observed=observed, marine=marine.collect(locations))

    if args.rodizio:
        from src.previsao.editorial.chuva_rs import anexar_varredura
        anexar_varredura(document, cadastro, pontos)
        for chave in ('today', 'tomorrow'):
            v = document['forecast'][chave]['rain_scan_rs']
            print(f"[chuva RS {chave}] {v['validos']}/{v['total']} pontos com volume válido")

    import yaml
    event_path = config.config_dir() / "eventos_manuais.yaml"
    if event_path.exists():
        document["events"] = (yaml.safe_load(event_path.read_text()) or {}).get("events", [])

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")

    confidence = document["confidence"]
    print(f"{out}")
    print(f"locais: {len(document['forecast']['today']['locations'])} "
          f"({', '.join(document['coverage'])})")
    print(f"modelos: {', '.join(document['forecast']['models'])} "
          f"| principal: {document['forecast']['primary_model']}")
    print(f"confianca: {confidence['score']}/{confidence['max_possible']} "
          f"({confidence['level']}) | linguagem categorica: "
          f"{'sim' if confidence['gates']['allow_categorical_language'] else 'nao'}")
    for source in document["sources"]:
        flag = " [fallback]" if source.get("fallback_used") else ""
        print(f"  - {source['name']}: {source['status']}{flag}")


if __name__ == "__main__":
    main()
