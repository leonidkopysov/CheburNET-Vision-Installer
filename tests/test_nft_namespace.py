"""Реальный nftables только в отдельном сетевом namespace, никогда на хосте"""
import fcntl
import os
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch
from test_audit114 import ROOT, tc, state


@unittest.skipUnless(os.environ.get('CHEBURNET_TEST_NFT') == '1', 'Нужен изолированный nftables namespace')
class NftNamespaceTests(unittest.TestCase):
    def setUp(self):
        self.assertEqual(os.geteuid(), 0)
        self.assertNotEqual(os.readlink('/proc/self/ns/net'), os.readlink('/proc/1/ns/net'),
                            'Запрещён запуск теста в сетевом namespace хоста')
        self.tmp = tempfile.TemporaryDirectory(prefix='cheburnet-nft-test-')
        self.base = Path(self.tmp.name)
        self.marker = self.base/'acme'
        self.flag = self.base/'ufw-open'
        self.lock = self.base/'lock'
        self.marker_patch = patch.object(tc, 'ACME_MARKER', self.marker)
        self.marker_patch.start()
        self.source = (ROOT/'src/acme-firewall.sh').read_text().replace(
            '/run/cheburnet-vision-acme.active', str(self.marker)).replace(
            '/run/cheburnet-traffic-control.lock', str(self.lock))
        self.stub = '''ufw(){
case "$*" in
  status) echo 'Status: active';;
  'status numbered') if [[ -f "$FLAG" ]]; then echo '[ 1] 80/tcp ALLOW IN Anywhere # CheburNET-Vision-ACME-temporary'; fi;;
  'insert 1 allow 80/tcp comment CheburNET-Vision-ACME-temporary') touch "$FLAG";;
  '--force delete 1') rm -f -- "$FLAG";;
  *) return 99;;
esac
}
'''

    def tearDown(self):
        subprocess.run(['nft', 'delete', 'table', 'inet', 'cheburnet_tc'], capture_output=True)
        self.marker_patch.stop()
        self.tmp.cleanup()

    def hook(self, mode):
        p = subprocess.run(['bash', '-c', self.stub+self.source, 'acme-test', mode],
                           env={**os.environ, 'FLAG': str(self.flag)}, capture_output=True, text=True, timeout=15)
        self.assertEqual(p.returncode, 0, p.stderr)

    def test_update_retains_acme_and_close_removes_it(self):
        tc.apply(state())
        self.hook('open')
        self.assertTrue(self.marker.exists())
        updated = state(); updated['lists']['test'] = ['198.51.101.0/24']
        tc.apply(updated)
        rules = tc.run('nft', 'list', 'table', 'inet', 'cheburnet_tc').stdout
        self.assertIn('tcp dport @acme_ports', rules)
        self.assertIn('198.51.101.0/24', rules)
        self.hook('close')
        self.assertFalse(self.marker.exists())
        self.assertFalse(self.flag.exists())
        rules = tc.run('nft', 'list', 'table', 'inet', 'cheburnet_tc').stdout
        self.assertNotIn('CheburNET-Vision-ACME-temporary', rules)
        self.hook('close')

    def test_expiry_removes_ufw_rule(self):
        tc.apply(state())
        self.hook('open')
        self.hook('expire')
        self.assertTrue(self.flag.exists())
        self.marker.write_text(str(int(time.time())-1))
        self.hook('expire')
        self.assertFalse(self.flag.exists())
        self.assertFalse(self.marker.exists())

    def test_nft_timeout_expires_without_hooks(self):
        self.marker.write_text(str(int(time.time())+2)); self.marker.chmod(0o600)
        tc.apply(state())
        time.sleep(3)
        result = subprocess.run(['nft', 'get', 'element', 'inet', 'cheburnet_tc', 'acme_ports', '{ 80 }'],
                                capture_output=True)
        self.assertNotEqual(result.returncode, 0)

    def test_hook_waits_for_shared_lock(self):
        tc.apply(state())
        with self.lock.open('w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            p = subprocess.Popen(['bash', '-c', self.stub+self.source, 'acme-test', 'open'],
                                 env={**os.environ, 'FLAG': str(self.flag)}, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                time.sleep(0.2)
                self.assertIsNone(p.poll())
                self.assertFalse(self.marker.exists())
                fcntl.flock(lock, fcntl.LOCK_UN)
                _, err = p.communicate(timeout=10)
                self.assertEqual(p.returncode, 0, err)
            finally:
                if p.poll() is None:
                    p.kill(); p.communicate()


if __name__ == '__main__':
    unittest.main()
