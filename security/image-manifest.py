#!/usr/bin/env python3
"""Bind an image archive, SBOM and scan report to the source commit."""
import hashlib
import json
from pathlib import Path
import subprocess

def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()

if subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=normal'], text=True).strip():
    raise SystemExit('Commit the source before creating provenance; dirty trees cannot be bound to HEAD.')
image = 'portfolio-api:v1'
root = Path('.local/records')
root.mkdir(parents=True, exist_ok=True)
archive = Path('.local/image.tar')
with archive.open('wb') as stream:
    subprocess.run(['docker', 'save', image], stdout=stream, check=True)
record = {'schema': 'portfolio-image-manifest/v1', 'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(), 'image': image, 'image_id': subprocess.check_output(['docker', 'image', 'inspect', image, '--format', '{{.Id}}'], text=True).strip(), 'archive_sha256': digest(archive), 'sbom_sha256': digest(root/'sbom.spdx.json'), 'scan_sha256': digest(root/'trivy.json')}
(root/'manifest.json').write_text(json.dumps(record, indent=2)+'\n')
archive.unlink()
print(json.dumps(record, indent=2))
