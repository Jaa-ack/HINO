"""Delivery archives contain reproducible inputs, never machine environments or secrets."""
import hashlib
import json
from zipfile import ZipFile


def test_delivery_excludes_runtime_and_preserves_raw(tmp_path):
    from scripts import package_delivery
    root = tmp_path/'project'
    root.mkdir()
    for name in ['README.md', 'src/app.py', '.venv/bin/python', '.runtime/tmp/cache', '__pycache__/x.pyc',
                 '.pytest_cache/state', '.playwright-cli/snapshot', '.env', '.env.example', 'docs/screenshots/fleet.png']:
        p = root/name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b'content')
    source = tmp_path/'source.xlsx'
    source.write_bytes(b'unchanged raw workbook fixture')
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    manifest = root/'data/interim/source_manifest.json'
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({'source_path': str(source), 'sha256': before}))
    archive = tmp_path/'delivery.zip'
    package_delivery.build_archive(root, source, archive)
    with ZipFile(archive) as z:
        names = set(z.namelist())
        assert 'hino-ecopilot/README.md' in names
        assert 'hino-ecopilot/.env.example' in names
        assert 'hino-ecopilot/docs/screenshots/fleet.png' in names
        for forbidden in ['.venv', '.runtime', '__pycache__', '.pytest_cache', '.playwright-cli', '.env']:
            assert not any(forbidden in name.split('/') for name in names)
        assert hashlib.sha256(z.read('hino-ecopilot/data/raw/source.xlsx')).hexdigest() == before
        out = json.loads(z.read('hino-ecopilot/data/interim/source_manifest.json'))
        assert out['source_path'] == 'data/raw/source.xlsx'
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before


def test_delivery_cannot_overwrite_source(tmp_path):
    import pytest
    from scripts.package_delivery import build_archive
    root = tmp_path/'project'
    root.mkdir()
    source = tmp_path/'source.xlsx'
    source.write_bytes(b'original workbook')
    with pytest.raises(ValueError, match='source|Source|zip'):
        build_archive(root, source, source)
    assert source.read_bytes() == b'original workbook'
