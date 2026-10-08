"""Create a portable delivery archive without virtual environments, caches or secrets."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from zipfile import ZipFile, ZIP_DEFLATED

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.ingest import find_workbook
from src.utils import ROOT, sha256

EXCLUDED = {'.venv', '.runtime', '__pycache__', '.pytest_cache', '.playwright-cli', '.git', '.env', '.DS_Store', 'output'}


def build_archive(root, source, destination):
    root, source, destination = Path(root).resolve(), Path(source).resolve(), Path(destination).resolve()
    if destination == source or destination.suffix.lower() != '.zip':
        raise ValueError('Destination must be a .zip and must not overwrite the source')
    before = sha256(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    source_member = 'data/raw/' + source.name
    temporary = destination.with_suffix('.zip.tmp')
    with ZipFile(temporary, 'w', ZIP_DEFLATED, compresslevel=6) as archive:
        for directory, dirs, files in os.walk(root):
            dirs[:] = sorted(d for d in dirs if d not in EXCLUDED and not (Path(directory)/d).is_symlink())
            for name in sorted(files):
                path = Path(directory)/name
                relative = path.relative_to(root)
                if name in EXCLUDED or name.endswith(('.pyc', '.zip', '.tmp')) or path.is_symlink() or path == source:
                    continue
                member = 'hino-ecopilot/' + relative.as_posix()
                if relative.as_posix() == 'data/interim/source_manifest.json':
                    manifest = json.loads(path.read_text())
                    if manifest['sha256'] != before:
                        raise ValueError('Delivery source does not match the analyzed workbook')
                    manifest['source_path'] = source_member
                    archive.writestr(member, json.dumps(manifest, ensure_ascii=False, indent=2))
                else:
                    archive.write(path, member)
        archive.write(source, 'hino-ecopilot/' + source_member)
    if sha256(source) != before:
        raise RuntimeError('Source changed while packaging')
    temporary.replace(destination)
    return destination


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path)
    parser.add_argument('--output', type=Path, default=ROOT.parent/'hino-ecopilot-delivery.zip')
    args = parser.parse_args()
    path = build_archive(ROOT, args.input or find_workbook(), args.output)
    print(f'Delivery archive: {path.name}; {path.stat().st_size:,} bytes; SHA-256 {sha256(path)}')
