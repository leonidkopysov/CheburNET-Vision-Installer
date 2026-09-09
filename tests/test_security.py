"""Exercise security boundaries with fixtures; never change the real host."""
import contextlib
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
import security_check as sec
import runtime

UFW = '''Status: active
Default: deny (incoming), allow (outgoing), deny (routed)
22/tcp                     ALLOW IN    Anywhere
443/tcp                    ALLOW IN    Anywhere
2222/tcp                   ALLOW IN    203.0.113.10
2222/tcp                   DENY IN     Anywhere
22/tcp (v6)                ALLOW IN    Anywhere (v6)
443/tcp (v6)               ALLOW IN    Anywhere (v6)
2222/tcp (v6)              DENY IN     Anywhere (v6)
'''


class SecurityTests(unittest.TestCase):
    def test_owned_traffic_control_is_embedded(self):
        installer = (ROOT/'src/installer.sh').read_text(encoding='utf-8')
        tuning = (ROOT/'vendor/cheburnet-auto-tuning.sh').read_text(encoding='utf-8')
        traffic_control = (ROOT/'src/cheburnet-traffic-control.py').read_text(encoding='utf-8')
        self.assertIn('VERSION = "1.0.0"', traffic_control)
        self.assertIn('module.main(["install", "--yes"])', installer)
        self.assertIn('/usr/local/bin/cheburnet-traffic-control activate', installer)
        self.assertNotIn('DonMatteoVPN', installer + tuning)
        self.assertNotIn('TrafficGuard', installer + tuning + traffic_control)

    def test_release_version_and_component_order(self):
        installer = (ROOT/'src/installer.sh').read_text(encoding='utf-8')
        self.assertIn('readonly CHEBURNET_VERSION=1.1.0', installer)
        self.assertNotIn('experimental', installer.lower())
        self.assertNotIn('эксперимент', installer.lower())
        sequence = [
            installer.rindex('\n    apply_tuning\n'),
            installer.rindex('\n    harden_host\n'),
            installer.rindex('\n    start_stack\n'),
            installer.rindex('\n    issue_certificate\n'),
            installer.rindex('\n    install_traffic_control\n'),
            installer.rindex("\n    step 'ИТОГИ УСТАНОВКИ / Проверка компонентов'"),
        ]
        self.assertEqual(sequence, sorted(sequence))

    def test_application_version_is_independent_from_os_release(self):
        installer = (ROOT/'src/installer.sh').read_text(encoding='utf-8')
        self.assertIn('readonly CHEBURNET_VERSION=', installer)
        self.assertNotIn('\nVERSION=1.1.0-', installer)
        self.assertIn('local ID VERSION VERSION_ID VERSION_CODENAME UBUNTU_CODENAME', installer)

    def test_manager_source_has_no_payload_placeholder_or_payload_function(self):
        installer = (ROOT/'src/installer.sh').read_text(encoding='utf-8')
        self.assertNotIn('@PAYLOAD_SHA256@', installer)
        self.assertNotIn('\npayload() {', installer)
        self.assertEqual(installer.count('# Private child entry'), 1)

    def test_firewall_accepts_exact_panel_ip(self):
        sec.firewall(UFW, 2222, '203.0.113.10')

    def test_firewall_rejects_bypasses_and_open_acme(self):
        for rule in ('2222/tcp    ALLOW IN    Anywhere',
                     '2222/tcp    ALLOW IN    203.0.113.99',
                     '2222/tcp    ALLOW IN    203.0.113.0/24',
                     '2000:3000/tcp    ALLOW IN    Anywhere',
                     '22,2222/tcp    LIMIT IN    Anywhere',
                     'Anywhere    ALLOW IN    203.0.113.10',
                     '80/tcp    ALLOW IN    Anywhere',
                     '80/tcp    ALLOW IN    203.0.113.10'):
            with self.subTest(rule=rule), self.assertRaises(sec.CheckFailure):
                sec.firewall(UFW+rule+'\n', 2222, '203.0.113.10')

    def test_firewall_rejects_missing_allow_and_inactive(self):
        for text in (UFW.replace('Status: active','Status: inactive'),
                     UFW.replace('deny (incoming)','allow (incoming)'),
                     UFW.replace('2222/tcp                   ALLOW IN    203.0.113.10','')):
            with self.assertRaises(sec.CheckFailure): sec.firewall(text,2222,'203.0.113.10')

    def test_cancel_after_collection_does_not_render_or_print_secret(self):
        answers=['node.example.com','','203.0.113.10','3.4.3','a@example.com','','','']
        output=io.StringIO()
        with patch('builtins.input',side_effect=answers), \
             patch.object(runtime.getpass,'getpass',return_value='SECRET_TEST_ONLY'), \
             patch.object(runtime,'validate_key'),patch.object(runtime,'render') as render, \
             contextlib.redirect_stdout(output),self.assertRaises(KeyboardInterrupt):
            runtime.collect('/unused')
        render.assert_not_called()
        self.assertNotIn('SECRET_TEST_ONLY',output.getvalue())

    def test_ssh_preserves_forwarding_and_rolls_back_conflicting_effective_config(self):
        source=(ROOT/'src/hardening.sh').read_text()
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            for name in ('node','etc/ssh/sshd_config.d','etc/sysctl.d','bin'):
                (root/name).mkdir(parents=True,exist_ok=True)
            (root/'node/.cheburnet-managed').touch()
            dropin=root/'etc/ssh/sshd_config.d/00-cheburnet-vision.conf'
            original='# existing owned configuration\n'
            harness=source.replace('/opt/remnanode',str(root/'node')).replace('/etc/',str(root/'etc')+'/')
            (root/'bin/sshd').write_text('''#!/bin/bash
[[ $1 == -t ]] && exit 0
printf 'allowtcpforwarding %s\npasswordauthentication yes\npubkeyauthentication yes\npermitrootlogin prohibit-password\nkbdinteractiveauthentication no\nauthenticationmethods any\n' "${FORWARD_MODE:-yes}"
if grep -q '^MaxAuthTries' "$TEST_DROPIN"; then
  printf 'maxauthtries %s\nlogingracetime 30\nallowagentforwarding no\npermittunnel no\nx11forwarding no\ngatewayports no\n' "$AUTH_TRIES"
else
  printf 'maxauthtries 6\n'
fi
''')
            (root/'bin/systemctl').write_text('''#!/bin/bash
if [[ $1 == is-active ]]; then
  [[ $3 == "ssh.$SSH_TEST_MODE" ]]
  exit
fi
printf 'systemctl %s\n' "$*" >> "$TEST_EVENTS"
''')
            (root/'bin/sysctl').write_text('#!/bin/bash\nprintf "sysctl %s\\n" "$*" >> "$TEST_EVENTS"\n')
            for p in (root/'bin').iterdir(): p.chmod(0o700)
            for tries in ('3','6'):
                dropin.write_text(original)
                events=root/'events';events.write_text('')
                env={**os.environ,'PATH':str(root/'bin')+':'+os.environ['PATH'],
                     'TEST_DROPIN':str(dropin),'TEST_EVENTS':str(events),'AUTH_TRIES':tries,
                     'FORWARD_MODE':'local','SSH_TEST_MODE':'service'}
                p=subprocess.run(['bash','-c',harness],env=env,capture_output=True,text=True,timeout=10)
                self.assertEqual(p.returncode==0,tries=='3',p.stderr)
                if tries=='3':
                    self.assertIn('systemctl try-reload-or-restart ssh.service',events.read_text())
                    self.assertNotIn('AllowTcpForwarding ', '\n'.join(x for x in dropin.read_text().splitlines() if not x.startswith('#')))
                else:
                    self.assertEqual(dropin.read_text(),original)
                    self.assertIn('systemctl try-reload-or-restart ssh.service',events.read_text())

            dropin.write_text(original)
            events.write_text('')
            env.update({'AUTH_TRIES':'3','SSH_TEST_MODE':'socket'})
            p=subprocess.run(['bash','-c',harness],env=env,capture_output=True,text=True,timeout=10)
            self.assertEqual(p.returncode,0,p.stderr)
            self.assertIn('systemctl daemon-reload',events.read_text())
            self.assertNotIn('try-reload-or-restart',events.read_text())


if __name__ == '__main__': unittest.main(verbosity=2)
