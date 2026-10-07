#!/usr/bin/env python3
"""Install pinned Linux amd64 tools after verifying upstream SHA256 manifests."""
import hashlib
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile

TARGET = Path(os.environ.get("TOOLS_DIR", "/workspace/tooling/bin"))
TARGET.mkdir(parents=True, exist_ok=True)
TOOLS = {
    "kind": ("https://kind.sigs.k8s.io/dl/v0.27.0", "kind-linux-amd64", "kind-linux-amd64.sha256sum"),
    "kubectl": ("https://dl.k8s.io/release/v1.32.2/bin/linux/amd64", "kubectl", "kubectl.sha256"),
    "trivy": ("https://github.com/aquasecurity/trivy/releases/download/v0.75.0", "trivy_0.75.0_Linux-64bit.tar.gz", "trivy_0.75.0_checksums.txt"),
    "syft": ("https://github.com/anchore/syft/releases/download/v1.54.1", "syft_1.54.1_linux_amd64.tar.gz", "syft_1.54.1_checksums.txt"),
    "cosign": ("https://github.com/sigstore/cosign/releases/download/v3.1.3", "cosign-linux-amd64", "cosign_checksums.txt"),
}
selected = os.environ.get("LAB_TOOLS", ",".join(TOOLS)).split(",")
with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp)
    for name in selected:
        base, artifact, manifest = TOOLS[name]
        archive = root / artifact
        checks = root / (name + ".checks")
        for url, dest in ((base + "/" + artifact, archive), (base + "/" + manifest, checks)):
            subprocess.run(["curl", "--fail", "--silent", "--show-error", "--location", url, "-o", str(dest)], check=True)
        lines = [line.split() for line in checks.read_text().splitlines() if line.strip()]
        if len(lines) == 1 and len(lines[0]) == 1:
            expected = lines[0][0]
        else:
            expected = next(parts[0] for parts in lines if parts[-1].lstrip("*").endswith(artifact))
        if hashlib.sha256(archive.read_bytes()).hexdigest() != expected:
            raise RuntimeError("SHA256 mismatch: " + artifact)
        dest = TARGET / name
        if artifact.endswith(".tar.gz"):
            with tarfile.open(archive) as package:
                member = next(m for m in package.getmembers() if Path(m.name).name == name and m.isfile())
                dest.write_bytes(package.extractfile(member).read())
        else:
            dest.write_bytes(archive.read_bytes())
        dest.chmod(0o755)
        print("Verified and installed", name, flush=True)
