import os
import zipfile
from datetime import datetime
from pathlib import Path


def create_backup(
    source_dir: str | Path | None = None,
    output_dir: str | Path | None = None,
) -> Path:
    source = Path(source_dir or os.getenv("DATA_DIR", "data"))
    target_dir = Path(output_dir or os.getenv("BACKUP_DIR", "backups"))
    target_dir.mkdir(parents=True, exist_ok=True)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    archive = target_dir / f"rag-backup-{stamp}.zip"

    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zip_file:
        if source.exists():
            for path in source.rglob("*"):
                if path.is_file():
                    zip_file.write(path, path.relative_to(source))

    return archive
