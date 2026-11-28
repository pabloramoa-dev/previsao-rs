"""Guard de isolamento: um canal nunca carrega a identidade de outro.

Nenhum @, nome de repositorio, id de conta ou caminho de OUTRO canal pode
aparecer no codigo, na configuracao ou nos workflows deste repositorio. A lista
de proibidos fica em config/isolamento.yaml e e escrita pelo gerador de estado
(todos os canais da rede, menos este).

`tests/` fica de fora de proposito: a bateria roda sobre o estado de referencia
(tests/ref_config), que e outro canal por definicao.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

ROOTS = [Path("src"), Path(".github"), Path("config"), Path("scripts"), Path("hyperframes"),
         Path("video"), Path("tools")]
# O gerador da rede (so no modelo) lista todos os canais por definicao.
ISENTOS = {Path("config/isolamento.yaml"), Path("scripts/novo_estado.py")}
SKIP_SUFFIXES = {".pyc", ".mp4", ".wav", ".png", ".jpg", ".woff2", ".ttf", ".js", ".csv", ".lock"}
SKIP_PARTS = {"__pycache__", "node_modules", "rede", "build"}


def _dados() -> dict:
    caminho = RAIZ / "config" / "isolamento.yaml"
    return yaml.safe_load(caminho.read_text(encoding="utf-8")) or {}


def proibidos() -> list[str]:
    return [str(t).casefold() for t in _dados().get("proibidos") or []]


def permitidos_por_arquivo() -> dict[Path, set[str]]:
    """Excecoes estreitas (arquivo -> tokens), ex.: o workflow do Radar central
    que busca o publicador no repositorio-modelo (hub da rede, nao um canal)."""
    bruto = _dados().get("permitidos_por_arquivo") or {}
    return {Path(k): {str(t).casefold() for t in v or []} for k, v in bruto.items()}


def _padrao(token: str) -> re.Pattern[str]:
    # Limite de palavra: um repo "previsao-xx" nao pode acusar "previsao-xxyz".
    return re.compile(r"(?<![a-z0-9])" + re.escape(token) + r"(?![a-z0-9_-])")


def scan(raiz: Path = RAIZ) -> list[tuple[str, str]]:
    padroes = [(t, _padrao(t)) for t in proibidos()]
    liberacoes = permitidos_por_arquivo()
    violations: list[tuple[str, str]] = []
    for root in ROOTS:
        base = raiz / root
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            rel = path.relative_to(raiz)
            if not path.is_file() or rel in ISENTOS:
                continue
            if path.suffix in SKIP_SUFFIXES or SKIP_PARTS & set(rel.parts):
                continue
            try:
                text = path.read_text(encoding="utf-8").casefold()
            except (UnicodeDecodeError, OSError):
                continue
            liberados = liberacoes.get(rel, set())
            for token, padrao in padroes:
                if token in liberados:
                    continue
                if padrao.search(text):
                    violations.append((str(rel), token))
    return violations


def main() -> None:
    violations = scan()
    if violations:
        lines = "\n".join(f"  {path}: {token!r}" for path, token in violations)
        raise SystemExit(f"isolamento falhou:\n{lines}")
    print(f"isolation_guard: ok ({len(proibidos())} identificadores proibidos, {len(ROOTS)} raizes)")


if __name__ == "__main__":
    main()
