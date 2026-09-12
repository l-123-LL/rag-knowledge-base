import zipfile
from pathlib import Path

from app.backup import create_backup


def test_create_backup_contains_data_files() -> None:
    source = Path("test_backup_source")
    output = Path("test_backup_output")
    source.mkdir(exist_ok=True)
    (source / "record.json").write_text('{"ok": true}', encoding="utf-8")

    try:
        archive = create_backup(source, output)
        with zipfile.ZipFile(archive) as zip_file:
            names = zip_file.namelist()
    finally:
        (source / "record.json").unlink(missing_ok=True)
        source.rmdir()
        for path in output.glob("*.zip"):
            path.unlink(missing_ok=True)
        output.rmdir()

    assert "record.json" in names
