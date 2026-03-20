"""
Repositórios (pareceres / portarias) — PostgreSQL quando DATABASE_URL está definido;
caso contrário, ficheiros locais (comportamento anterior).
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, List, Literal, Optional

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

Category = Literal["parecer", "portaria"]

# --- Ficheiros (legado) ---
BIBLIOTECA_DIR = Path(__file__).parent / "biblioteca"
PARECERES_DIR = BIBLIOTECA_DIR / "pareceres_validados"
PORTARIAS_DIR = Path(__file__).parent / "portarias" / "historico"
FEEDBACKS_FILE = BIBLIOTECA_DIR / "feedbacks" / "feedbacks.jsonl"

PARECERES_DIR.mkdir(parents=True, exist_ok=True)
PORTARIAS_DIR.mkdir(parents=True, exist_ok=True)
FEEDBACKS_FILE.parent.mkdir(parents=True, exist_ok=True)

_engine = None
_SessionLocal = None


def _db_enabled() -> bool:
    return bool(os.environ.get("DATABASE_URL", "").strip())


def _get_engine():
    global _engine, _SessionLocal
    if _engine is None:
        from db.models import get_session_factory, init_db, make_engine

        url = os.environ["DATABASE_URL"].strip()
        _engine = make_engine(url)
        init_db(_engine)
        _SessionLocal = get_session_factory(_engine)
    return _engine, _SessionLocal


def list_documents(category: Category) -> List[dict[str, Any]]:
    if _db_enabled():
        _, SessionLocal = _get_engine()
        from db.models import RepositoryDocument

        with SessionLocal() as s:
            rows = s.scalars(
                select(RepositoryDocument)
                .where(RepositoryDocument.category == category)
                .order_by(RepositoryDocument.updated_at.desc())
            ).all()
            out = []
            for r in rows:
                out.append(
                    {
                        "nome": r.filename,
                        "tamanho_kb": round(len(r.content.encode("utf-8")) / 1024, 1),
                        "modificado": r.updated_at.strftime("%d/%m/%Y %H:%M")
                        if r.updated_at
                        else "",
                        "id": r.id,
                    }
                )
            return out

    folder = PARECERES_DIR if category == "parecer" else PORTARIAS_DIR
    globs = list(folder.glob("*"))
    arquivos = sorted(globs, key=lambda f: f.stat().st_mtime, reverse=True)
    out = []
    for p in arquivos:
        if p.is_dir():
            continue
        st = p.stat()
        out.append(
            {
                "nome": p.name,
                "tamanho_kb": round(st.st_size / 1024, 1),
                "modificado": datetime.fromtimestamp(st.st_mtime).strftime(
                    "%d/%m/%Y %H:%M"
                ),
            }
        )
    return out


def read_document(category: Category, filename: str) -> str:
    if _db_enabled():
        _, SessionLocal = _get_engine()
        from db.models import RepositoryDocument

        with SessionLocal() as s:
            r = s.scalars(
                select(RepositoryDocument).where(
                    RepositoryDocument.category == category,
                    RepositoryDocument.filename == filename,
                )
            ).first()
            return r.content if r else ""

    folder = PARECERES_DIR if category == "parecer" else PORTARIAS_DIR
    p = folder / filename
    if p.exists():
        return p.read_text(encoding="utf-8", errors="replace")
    return ""


def _disk_path(category: Category, filename: str) -> Path:
    folder = PARECERES_DIR if category == "parecer" else PORTARIAS_DIR
    safe = filename.replace(" ", "_")
    if not safe.endswith((".md", ".txt", ".html")):
        if "." not in safe:
            safe = f"{safe}.md"
    return folder / safe


def _mirror_to_disk(category: Category, filename: str, content: str) -> None:
    """Espelha em disco (few-shot / legado) quando a fonte de verdade é PostgreSQL."""
    p = _disk_path(category, filename)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def save_document(
    category: Category, filename: str, content: str, mime: str = "text/markdown"
) -> None:
    if _db_enabled():
        _, SessionLocal = _get_engine()
        from db.models import RepositoryDocument

        with SessionLocal() as s:
            r = s.scalars(
                select(RepositoryDocument).where(
                    RepositoryDocument.category == category,
                    RepositoryDocument.filename == filename,
                )
            ).first()
            if r:
                r.content = content
                r.content_mime = mime
                r.updated_at = datetime.utcnow()
            else:
                s.add(
                    RepositoryDocument(
                        category=category,
                        filename=filename,
                        content=content,
                        content_mime=mime,
                    )
                )
            s.commit()
        _mirror_to_disk(category, filename, content)
        return

    folder = PARECERES_DIR if category == "parecer" else PORTARIAS_DIR
    if not filename.endswith((".md", ".txt", ".html")):
        if "." not in filename:
            filename = f"{filename}.md"
    dest = folder / filename.replace(" ", "_")
    dest.write_text(content, encoding="utf-8")


def delete_document(category: Category, filename: str) -> bool:
    if _db_enabled():
        _, SessionLocal = _get_engine()
        from db.models import RepositoryDocument

        with SessionLocal() as s:
            s.execute(
                delete(RepositoryDocument).where(
                    RepositoryDocument.category == category,
                    RepositoryDocument.filename == filename,
                )
            )
            s.commit()
        p = _disk_path(category, filename)
        if p.exists():
            p.unlink()
        return True

    folder = PARECERES_DIR if category == "parecer" else PORTARIAS_DIR
    p = folder / filename
    if p.exists():
        p.unlink()
        return True
    return False


def clear_repository(category: Category) -> int:
    """
    Remove todos os documentos desta categoria (PostgreSQL e/ou ficheiros em disco).
    Não altera feedbacks nem outras categorias.
    Retorna o número de documentos removidos.
    """
    folder = PARECERES_DIR if category == "parecer" else PORTARIAS_DIR
    removidos = 0

    if _db_enabled():
        _, SessionLocal = _get_engine()
        from db.models import RepositoryDocument

        with SessionLocal() as s:
            rows = s.scalars(
                select(RepositoryDocument).where(
                    RepositoryDocument.category == category
                )
            ).all()
            removidos = len(rows)
            for r in rows:
                s.delete(r)
            s.commit()
        logger.info("clear_repository DB: %s, %d linhas", category, removidos)
    else:
        for p in folder.glob("*"):
            if p.is_file():
                p.unlink()
                removidos += 1
        logger.info("clear_repository ficheiros: %s, %d ficheiros", category, removidos)
        return removidos

    # Espelho em disco (se existir) alinhado com a BD
    for p in folder.glob("*"):
        if p.is_file():
            try:
                p.unlink()
            except OSError as e:
                logger.warning("clear_repository: não foi possível apagar %s: %s", p, e)

    return removidos


def total_chars(category: Category) -> int:
    docs = list_documents(category)
    total = 0
    for d in docs:
        total += len(read_document(category, d["nome"]).encode("utf-8"))
    return total


def texto_repositorio_concatenado(
    category: Category, max_chars: int = 120_000
) -> str:
    """Texto único para contexto RAG (só documentos desta categoria)."""
    parts = []
    used = 0
    for d in list_documents(category):
        nome = d["nome"]
        body = read_document(category, nome)
        block = f"\n\n### FICHEIRO: {nome}\n{body}\n"
        if used + len(block) > max_chars:
            block = block[: max_chars - used] + "\n[...truncado...]"
            parts.append(block)
            break
        parts.append(block)
        used += len(block)
    return "\n---\n".join(parts).strip()


def save_feedback(
    category: Category,
    municipio: str,
    secao: str,
    avaliacao: int,
    comentario: str,
    autor: str = "",
    provedor_ia: str = "",
) -> bool:
    if _db_enabled():
        _, SessionLocal = _get_engine()
        from db.models import FeedbackEntry

        with SessionLocal() as s:
            s.add(
                FeedbackEntry(
                    category=category,
                    municipio=municipio.strip(),
                    secao=secao,
                    avaliacao=avaliacao,
                    comentario=comentario.strip(),
                    autor=autor.strip(),
                    provedor_ia=provedor_ia or "",
                )
            )
            s.commit()
        return True

    entrada = {
        "timestamp": datetime.now().isoformat(),
        "category": category,
        "municipio": municipio.strip(),
        "secao": secao,
        "avaliacao": avaliacao,
        "comentario": comentario.strip(),
        "autor": autor.strip(),
        "provedor_ia": provedor_ia,
    }
    try:
        with open(FEEDBACKS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entrada, ensure_ascii=False) + "\n")
        return True
    except Exception as e:
        logger.error("Feedback ficheiro: %s", e)
        return False


def list_feedbacks(category: Optional[Category] = None, limite: int = 50) -> List[dict]:
    if _db_enabled():
        _, SessionLocal = _get_engine()
        from db.models import FeedbackEntry

        with SessionLocal() as s:
            q = select(FeedbackEntry).order_by(FeedbackEntry.created_at.desc())
            if category:
                q = q.where(FeedbackEntry.category == category)
            rows = s.scalars(q.limit(limite)).all()
            return [
                {
                    "timestamp": r.created_at.isoformat() if r.created_at else "",
                    "municipio": r.municipio,
                    "secao": r.secao,
                    "avaliacao": r.avaliacao,
                    "comentario": r.comentario,
                    "autor": r.autor,
                    "provedor_ia": r.provedor_ia,
                    "category": r.category,
                }
                for r in rows
            ]

    if not FEEDBACKS_FILE.exists():
        return []
    out = []
    try:
        with open(FEEDBACKS_FILE, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    e = json.loads(line)
                    if category:
                        cat_e = e.get("category") or "parecer"
                        if cat_e != category:
                            continue
                    out.append(e)
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        logger.warning("Ler feedbacks: %s", e)
    return out[:limite]


def resumo_feedbacks(category: Optional[Category] = None) -> dict:
    rows = list_feedbacks(category=category, limite=500)
    if not rows:
        return {"total": 0, "media": None}
    avs = [r.get("avaliacao") for r in rows if r.get("avaliacao")]
    media = sum(avs) / len(avs) if avs else None
    return {"total": len(rows), "media": round(media, 2) if media else None}
