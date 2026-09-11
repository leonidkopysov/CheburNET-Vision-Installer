#!/usr/bin/env python3
"""Build a reproducible single-file installer without accessing the network."""
import base64
import gzip
import hashlib
import io
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parent
TUNING_SHA256 = 'e8e4016e092edc828d2042d0cf4b99ff2c4cdcece641466edf486e5fb04631ca'
TRAFFIC_CONTROL_SHA256 = '7bb39726a72643bf7cad65ed9d8297944391fac943f7e12a9efacfd9d5963f4a'


def build():
    vendor = ROOT/'vendor/cheburnet-auto-tuning.sh'
    assert hashlib.sha256(vendor.read_bytes()).hexdigest() == TUNING_SHA256, 'Tuning snapshot changed'
    traffic_control = ROOT/'src/cheburnet-traffic-control.py'
    assert hashlib.sha256(traffic_control.read_bytes()).hexdigest() == TRAFFIC_CONTROL_SHA256, 'Traffic Control snapshot changed'
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode='w', format=tarfile.USTAR_FORMAT) as tar:
        files = [(p.name,p) for p in sorted((ROOT/'src').iterdir()) if p.name != 'installer.sh' and p.is_file()]
        # The installed management copy does not need the large embedded payload.
        # Keeping it inside the verified archive makes process substitution safe:
        # Bash never has to copy its already-consumed /dev/fd input.
        files.append(('installer-manager.sh', ROOT/'src/installer.sh'))
        files.append(('cheburnet-auto-tuning.sh', vendor))
        for name, path in files:
            data = path.read_bytes()
            info = tarfile.TarInfo(name)
            info.size, info.mode, info.mtime = len(data), 0o600, 0
            tar.addfile(info, io.BytesIO(data))
    payload = gzip.compress(output.getvalue(), mtime=0)
    encoded = base64.encodebytes(payload).decode('ascii')
    payload_hash = hashlib.sha256(payload).hexdigest()
    func = (f"readonly CHEBURNET_PAYLOAD_SHA256='{payload_hash}'\n\n"
            + "payload() {\n    cat <<'CHEBURNET_PAYLOAD'\n"
            + encoded + 'CHEBURNET_PAYLOAD\n}\n\n')
    source = (ROOT/'src/installer.sh').read_text()
    assert '@PAYLOAD_SHA256@' not in source, 'Obsolete payload placeholder in manager source'
    marker = '# Private child entry'
    assert source.count(marker) == 1, 'Payload insertion marker missing or duplicated'
    source = source.replace(marker, func + marker)
    assert source.count('payload() {') == 1, 'Payload function was not injected'
    assert f"readonly CHEBURNET_PAYLOAD_SHA256='{payload_hash}'" in source, 'Payload hash was not injected'
    manager = (ROOT/'src/installer.sh').read_text()
    assert '@PAYLOAD_SHA256@' not in manager, 'Payload placeholder leaked into manager'
    assert 'payload() {' not in manager, 'Manager must not contain the embedded archive'
    dest = ROOT/'cheburnet-vision-install.sh'
    dest.write_text(source)
    dest.chmod(0o755)
    (ROOT/'SHA256SUMS').write_text(hashlib.sha256(dest.read_bytes()).hexdigest() + '  ' + dest.name + '\n')
    print(f'{dest.name}: {dest.stat().st_size} bytes')


if __name__ == '__main__':
    build()
