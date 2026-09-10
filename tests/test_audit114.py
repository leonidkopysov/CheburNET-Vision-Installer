"""Регрессии 1.1.4: без изменений служб, пакетов и firewall хоста"""
import ast
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from test_shell import SOURCE, shell
from test_security import UFW
import runtime
import security_check as security

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('tc114', ROOT/'src/cheburnet-traffic-control.py')
tc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tc)


def state():
    return dict(schema=1, ssh_ports=[22], allow=['203.0.113.10'], manual=[],
                lists={'test': ['198.51.100.0/24']}, logging=True, updated=1)


class Audit114Tests(unittest.TestCase):
    def test_firewall_requires_public_443(self):
        text = '\n'.join(line for line in UFW.splitlines() if '443' not in line)
        with self.assertRaisesRegex(security.CheckFailure, 'TCP/443'):
            security.firewall(text, 2222, '203.0.113.10')

    def test_firewall_requires_each_family(self):
        text = '\n'.join(line for line in UFW.splitlines() if '(v6)' not in line)
        with self.assertRaises(security.CheckFailure):
            security.firewall(text, 2222, '203.0.113.10', (4, 6))
        security.firewall(text+'\n443/tcp (v6)  ALLOW IN  Anywhere (v6)', 2222, '203.0.113.10', (4, 6))

    def test_firewall_detects_preceding_deny(self):
        with self.assertRaisesRegex(security.CheckFailure, 'запрещающее'):
            security.firewall('443/tcp  DENY IN  Anywhere\n'+UFW, 2222, '203.0.113.10')
        security.firewall(UFW+'\n443/tcp  DENY IN  Anywhere', 2222, '203.0.113.10')

    def test_external_network_limits(self):
        for text in ('0.0.0.0/1', '::/1', 'bad', '0.0.0.0/0', ''):
            with self.subTest(text=text), self.assertRaises(ValueError):
                tc.networks(text)
        self.assertEqual(tc.networks('198.51.100.0/24'), ['198.51.100.0/24'])

    def test_union_limit_is_not_per_file(self):
        with patch.object(tc, 'SOURCES', {'a': 'a', 'b': 'b'}), \
             patch.object(tc, 'download', side_effect=[['198.51.100.0/24'], ['198.51.101.0/24']]), \
             patch.object(tc, 'MAX_COVERAGE', {4: 300, 6: 2**104}), self.assertRaises(ValueError):
            tc.fetch_lists()
        tc.validate_coverage(['198.51.100.0/24', '198.51.100.0/24'])

    def test_ipv6_union_limit(self):
        with patch.object(tc, 'MAX_COVERAGE', {4: 4_000_000, 6: 2**64}), self.assertRaises(ValueError):
            tc.validate_coverage(['2001:db8::/64', '2001:db8:1::/64'])

    def test_bad_update_does_not_apply_or_save(self):
        with tempfile.TemporaryDirectory() as td, patch.object(tc, 'ROOT', Path(td)), \
             patch.object(tc, 'load', return_value=state()), \
             patch.object(tc, 'fetch_lists', side_effect=ValueError('rejected')), \
             patch.object(tc, 'commit') as commit:
            with self.assertRaises(ValueError):
                tc.execute(type('Args', (), {'command': 'update'})())
            commit.assert_not_called()

    def test_acme_render_retains_timed_exception(self):
        with tempfile.TemporaryDirectory() as td:
            marker = Path(td)/'acme'; marker.write_text(str(int(time.time())+100)); marker.chmod(0o600)
            with patch.object(tc, 'ACME_MARKER', marker), patch.object(tc.os, 'getuid', return_value=0):
                # CI tests run without root; emulate the root-owned marker metadata only
                real = marker.stat()
                metadata = type('Stat', (), dict(st_mode=real.st_mode, st_uid=0, st_size=real.st_size))()
                with patch.object(Path, 'lstat', return_value=metadata):
                    rules = tc.render(state(), exists=True)
                    self.assertTrue(rules.startswith('delete table'))
                    self.assertIn('tcp dport @acme_ports', rules)
                    self.assertRegex(rules, r'80 timeout \d+s')
                    marker.write_text(str(int(time.time())-1))
                    self.assertNotIn('acme_ports', tc.render(state(), exists=True))

    def test_acme_marker_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td)/'target'; target.write_text(str(int(time.time())+100))
            marker = Path(td)/'marker'; marker.symlink_to(target)
            with patch.object(tc, 'ACME_MARKER', marker), self.assertRaises(ValueError):
                tc.acme_remaining()

    def test_cli_propagates_diagnostic_failure(self):
        entry = ast.parse((ROOT/'src/cheburnet-traffic-control.py').read_text()).body[-1]
        for count, expected in ((0, 0), (7, 1)):
            code = f'import sys,subprocess\ndef main(): return {count}\n'+ast.unparse(entry)
            self.assertEqual(subprocess.run([sys.executable, '-c', code], capture_output=True).returncode, expected)

    def test_runtime_error_is_not_pending(self):
        with tempfile.TemporaryDirectory() as td:
            p = subprocess.run([sys.executable, str(ROOT/'src/runtime.py'), 'render', '--settings', td+'/missing',
                                '--output', td+'/out'], capture_output=True, text=True)
            self.assertEqual(p.returncode, 1)
            self.assertNotIn('Traceback', p.stderr)
            self.assertFalse((Path(td)/'out').exists())

    def test_certificate_mismatch_with_exit_zero_rejected(self):
        p = shell('openssl(){ echo "Hostname wrong.example does NOT match certificate"; }; verify_certificate_name ignored wrong.example')
        self.assertEqual(p.returncode, 1)
        self.assertIn('Сертификат не выдан', p.stderr)
        p = shell('openssl(){ echo "Hostname good.example does match certificate"; }; verify_certificate_name ignored good.example')
        self.assertEqual(p.returncode, 0)

    def test_apt_resume_environment_and_umask(self):
        p = shell('''apt-get(){ printf '%s|%s|%s|%s' "$DEBIAN_FRONTEND" "$NEEDRESTART_MODE" "$APT_LISTCHANGES_FRONTEND" "$(umask)"; }
apt_apply install package
printf '|%s' "$(umask)"
''', {'DEBIAN_FRONTEND': '', 'NEEDRESTART_MODE': '', 'APT_LISTCHANGES_FRONTEND': ''})
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(p.stdout, 'noninteractive|a|none|0022|0077')

    def test_tuning_cannot_install_outside_plan(self):
        function = SOURCE.split('apply_tuning() {', 1)[1].split('\nharden_host()', 1)[0]
        self.assertIn('CHEBURNET_INSTALL_SECURITY_PACKAGES=0', function)
        self.assertIn('CHEBURNET_INSTALL_ZRAM_PACKAGES=0', function)
        self.assertIn("ufw allow 443/tcp", function)

    def test_nginx_mask_precedes_package_install(self):
        function = SOURCE.split('bootstrap_project() {', 1)[1].split('\nmain()', 1)[0]
        self.assertLess(function.index('systemctl mask nginx.service'), function.index('apt_confirmed install'))

    def test_tc_absence_includes_alias_units_and_nft_errors(self):
        with tempfile.TemporaryDirectory() as td:
            source = SOURCE.replace('/usr/local/bin/', td+'/bin/').replace('/var/lib/cheburnet-traffic-control/', td+'/data/').replace('/etc/systemd/system/', td+'/units/')
            for folder in ('bin', 'data', 'units'): (Path(td)/folder).mkdir()
            def run(stub):
                return subprocess.run(['bash', '-c', source+'\nnft(){ '+stub+'; }; traffic_control_absent'], capture_output=True, text=True)
            self.assertEqual(run(':').returncode, 0)
            self.assertNotEqual(run('return 1').returncode, 0)
            alias = Path(td)/'bin/ctc'; alias.symlink_to('/nonexistent-audit-target')
            self.assertNotEqual(run(':').returncode, 0)

    def test_panel_prompt_precedes_full_diagnostics(self):
        main = SOURCE.split('main() {', 1)[1]
        self.assertLess(main.index('\n    show_result\n'), main.index('if ! confirm_panel_ready'))
        self.assertLess(main.index('if ! confirm_panel_ready'), main.index('--check-internal'))
        self.assertIn('exit 2', main.split('if ! confirm_panel_ready', 1)[1].split('fi', 1)[0])

    def test_tc_yes_no_and_empty(self):
        for answer, expected in [('y', True), ('Да', True), ('', False), ('No', False)]:
            with patch.object(tc, 'prompt_input', return_value=answer):
                self.assertEqual(tc.ask_yes('Вопрос'), expected)

    def test_prompt_color_and_no_color(self):
        with patch.object(runtime.sys.stdin, 'isatty', return_value=True), patch.dict(os.environ, {}, clear=True):
            self.assertIn('\033[1;33m', runtime.prompt_label('Порт: '))
            with patch.dict(os.environ, {'NO_COLOR': ''}):
                self.assertEqual(runtime.prompt_label('Порт: '), 'Порт: ')

    def test_panel_prompt_plain_output(self):
        p = shell("ask_yes(){ printf '%s' \"$1\"; return 0; }; confirm_panel_ready", {'NO_COLOR': ''})
        self.assertEqual(p.returncode, 0)
        self.assertIn('стала зелёной', p.stdout)
        self.assertNotIn('\033[', p.stdout)

    def test_relay_ips_are_in_confirmed_allowlist(self):
        args = type('Args', (), {'ssh_port': None, 'allow': []})()
        with patch.object(tc.sys.stdin, 'isatty', return_value=True), \
             patch.object(tc, 'ask_value', side_effect=[['203.0.113.1'], [22], ['203.0.113.2']]), \
             patch.object(tc, 'panel_hint', return_value=''), \
             patch.object(tc, 'prompt_input', return_value='203.0.113.3'), \
             patch.object(tc, 'ask_yes', return_value=True), contextlib.redirect_stdout(io.StringIO()):
            ports, allowed = tc.install_inputs(args)
            self.assertEqual(ports, [22])
            self.assertEqual(allowed, ['203.0.113.1', '203.0.113.2', '203.0.113.3'])


if __name__ == '__main__':
    unittest.main()
