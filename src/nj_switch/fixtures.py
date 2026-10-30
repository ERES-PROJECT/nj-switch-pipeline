"""Freeze selected, already captured public evidence for deterministic regression tests."""
import json
import shutil
from pathlib import Path

from .evidence import redact, safe_url, sanitize_html
from .models import CollectionResult


def freeze_fixture(result_file: Path, destination: Path):
    result = CollectionResult.model_validate_json(result_file.read_text(encoding="utf-8"))
    if destination.exists():
        raise ValueError("Fixture destination exists; choose a new filename")
    destination.parent.mkdir(parents=True, exist_ok=True)
    base = result_file.parent / "artifacts"
    fixture = {"fixture_kind": "observed_public_capture", "captured_at": result.started_at,
               "query": result.query.model_dump(), "context_verified": result.context_verified,
               "payloads": [], "documents": []}
    if result.status in {"empty", "unsupported", "blocked"}:
        fixture["disposition"] = result.status
    seen = set()
    document_ids = {c.artifact_id for c in result.contracts}
    for artifact in result.artifacts:
        path = (base / artifact["path"]).resolve()
        if path.parent != base.resolve():
            raise ValueError("Invalid source artifact path")
        if artifact["kind"] == "html" and artifact["id"] not in document_ids and not artifact.get("stage"):
            fixture["html"] = sanitize_html(path.read_text(encoding="utf-8"))
            fixture["source_url"] = safe_url(artifact["url"])
        elif artifact["kind"] == "json" and artifact["id"] not in seen:
            fixture["payloads"].append({"url": safe_url(artifact["url"]), "body": redact(json.loads(path.read_text(encoding="utf-8")))})
        elif artifact["id"] in document_ids:
            folder = destination.parent / (destination.stem + "-documents")
            folder.mkdir(exist_ok=True)
            target = folder / path.name
            if not target.exists():
                shutil.copyfile(path, target)
            fixture["documents"].append({"url": safe_url(artifact["url"]), "path": target.relative_to(destination.parent).as_posix()})
        seen.add(artifact["id"])
    with destination.open("x", encoding="utf-8") as handle:
        json.dump(fixture, handle, indent=2, ensure_ascii=False)
    return destination
