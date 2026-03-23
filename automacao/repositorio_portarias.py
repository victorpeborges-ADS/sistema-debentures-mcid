"""
Repositório de portarias — persistência em ficheiros (histórico legível).
Espelha o padrão da biblioteca de pareceres: pasta com .md, sem expor SQL ao utilizador.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

REPO_DIR = Path(__file__).parent / "portarias" / "historico"


def _ensure() -> None:
    REPO_DIR.mkdir(parents=True, exist_ok=True)


def listar_portarias() -> List[Dict[str, Any]]:
    """Lista ficheiros .md mais recentes primeiro."""
    _ensure()
    out = []
    for p in sorted(REPO_DIR.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True):
        st = p.stat()
        out.append(
            {
                "nome": p.name,
                "caminho": p,
                "tamanho_kb": round(st.st_size / 1024, 1),
                "modificado": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M"),
            }
        )
    return out


def salvar_portaria(nome_base: str, conteudo_md: str) -> Path:
    """Grava portaria como Markdown."""
    _ensure()
    base = nome_base.strip()
    if not base.endswith(".md"):
        base = f"{base}.md"
    dest = REPO_DIR / base.replace(" ", "_")
    dest.write_text(conteudo_md, encoding="utf-8")
    logger.info("Portaria salva: %s", dest)
    return dest


def ler_portaria(nome: str) -> str:
    p = REPO_DIR / nome
    if p.exists():
        return p.read_text(encoding="utf-8")
    return ""


def remover_portaria(nome: str) -> bool:
    p = REPO_DIR / nome
    if p.exists():
        p.unlink()
        return True
    return False
