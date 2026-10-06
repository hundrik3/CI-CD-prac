#!/bin/sh
set -eu
# Linux amd64; verified upstream artifacts, installed outside the checkout.
TOOLS_DIR=${TOOLS_DIR:-/workspace/tooling/bin}
mkdir -p "$TOOLS_DIR"
TASK_TMP=$(mktemp -d)
trap 'rm -rf "$TASK_TMP"' EXIT HUP INT TERM
curl -fsSL https://releases.hashicorp.com/terraform/1.11.4/terraform_1.11.4_linux_amd64.zip -o "$TASK_TMP/terraform.zip"
curl -fsSL https://releases.hashicorp.com/terraform/1.11.4/terraform_1.11.4_SHA256SUMS -o "$TASK_TMP/terraform-checksums"
curl -fsSL https://github.com/aquasecurity/tfsec/releases/download/v1.28.14/tfsec_1.28.14_linux_amd64.tar.gz -o "$TASK_TMP/tfsec.tar.gz"
curl -fsSL https://github.com/aquasecurity/tfsec/releases/download/v1.28.14/tfsec_1.28.14_checksums.txt -o "$TASK_TMP/tfsec-checksums"
python - "$TASK_TMP" "$TOOLS_DIR" <<'PY'
import hashlib, pathlib, sys, tarfile, zipfile
root, target = map(pathlib.Path, sys.argv[1:])
for archive, sums, upstream in [('terraform.zip','terraform-checksums','terraform_1.11.4_linux_amd64.zip'),('tfsec.tar.gz','tfsec-checksums','tfsec_1.28.14_linux_amd64.tar.gz')]:
    expected = next(line.split()[0] for line in (root/sums).read_text().splitlines() if line.split()[-1] == upstream)
    if hashlib.sha256((root/archive).read_bytes()).hexdigest() != expected:
        raise SystemExit('Checksum verification failed: ' + upstream)
zipfile.ZipFile(root/'terraform.zip').extract('terraform', target)
with tarfile.open(root/'tfsec.tar.gz') as archive:
    member = next(m for m in archive.getmembers() if pathlib.PurePosixPath(m.name).name == 'tfsec' and m.isfile())
    with archive.extractfile(member) as source:
        (target/'tfsec').write_bytes(source.read())
for name in ('terraform','tfsec'):
    (target/name).chmod(0o755)
PY
python -m venv /workspace/tooling/venv
/workspace/tooling/venv/bin/python -m pip install -r tests/requirements.txt
export PATH="$TOOLS_DIR:$PATH"
terraform -chdir=infra init -backend=false -lockfile=readonly
terraform -chdir=bootstrap init -backend=false -lockfile=readonly
