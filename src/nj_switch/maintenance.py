"""One-time baseline snapshots. Never rewrite or delete a prior baseline."""
import hashlib
import json
import shutil
from pathlib import Path

from .registry import PROJECT_ROOT


def backup_baseline() -> Path:
    target = PROJECT_ROOT / "data/legacy/pre-v2-baseline"
    if target.exists():
        manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
        for item in manifest:
            if hashlib.sha256((target / item["path"]).read_bytes()).hexdigest() != item["sha256"]:
                raise ValueError("Baseline verification failed: " + item["path"])
        return target
    target.mkdir(parents=True)
    sources = list((PROJECT_ROOT / "data").glob("*.csv"))
    sources += [PROJECT_ROOT / "src/scraper/nj_scraper.py", PROJECT_ROOT / "src/scraper/demo_test.py",
                PROJECT_ROOT / "src/TPSCompilation/master_third_party_supplier_list.csv"]
    manifest = []
    for source in sources:
        relative = source.relative_to(PROJECT_ROOT)
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        manifest.append({"path": relative.as_posix(), "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(), "bytes": destination.stat().st_size})
    (target / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return target

