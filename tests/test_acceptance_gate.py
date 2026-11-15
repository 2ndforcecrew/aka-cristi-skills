"""Negative evidence tests; these are not independent user acceptance."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from tools.acceptance_gate import assess


class AcceptanceGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_empty_records_block_every_gate(self):
        result = assess({}, self.root)
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertEqual(len(result['gates']), 6)
        self.assertTrue(all(g['status'] == 'BLOCKED' for g in result['gates'].values()))

    def test_self_reported_pass_does_not_count_as_evidence(self):
        record = {'source_sha': 'a' * 40, 'gates': {str(n): {'status': 'PASS'} for n in range(8, 14)}}
        result = assess(record, self.root)
        self.assertEqual(result['status'], 'BLOCKED')
        self.assertFalse(result['completion_notification_allowed'])

    def test_synthetic_attachment_is_blocked(self):
        attachment = self.root / 'test.json'
        attachment.write_text('{"synthetic": true}', encoding='utf-8')
        result = assess({'source_sha': 'a' * 40, 'gates': {'8': {
            'evidence_kind': 'synthetic', 'path': 'test.json',
            'sha256': hashlib.sha256(attachment.read_bytes()).hexdigest(),
        }}}, self.root)
        self.assertEqual(result['gates']['8']['status'], 'BLOCKED')

    def test_traversal_and_symlink_not_read(self):
        item = {'evidence_kind': 'observed', 'path': '../private.json', 'sha256': 'a'*64}
        result = assess({'source_sha':'a'*40, 'gates': {'8': item}}, self.root)
        self.assertIn('unsafe_evidence_path', result['gates']['8']['reasons'])

    def test_symlink_attachment_not_read(self):
        outside = self.root / 'outside.json'
        outside.write_text('{}', encoding='utf-8')
        link = self.root / 'link.json'
        try:
            link.symlink_to(outside)
        except OSError:
            self.skipTest('symlink privilege unavailable')
        item = {'evidence_kind':'observed', 'path':'link.json',
                'sha256':hashlib.sha256(outside.read_bytes()).hexdigest()}
        result = assess({'source_sha':'a'*40, 'gates': {'8':item}}, self.root)
        self.assertIn('unsafe_evidence_path', result['gates']['8']['reasons'])

    def test_tampered_attachments_cannot_enter_review(self):
        file = self.root / 'report.json'
        file.write_text('{}', encoding='utf-8')
        item = {'evidence_kind':'observed', 'path':'report.json','sha256':'a'*64}
        result = assess({'source_sha':'a'*40, 'gates': {'8':item}}, self.root)
        self.assertIn('attachment_digest_mismatch', result['gates']['8']['reasons'])

    def test_documentary_complete_record_requires_independent_review_not_auto_pass(self):
        from tools.acceptance_gate import REQUIRED
        gates = {}
        for issue, keys in REQUIRED.items():
            payload = {key: 'recorded' for key in keys}
            payload.update({'source_sha':'b'*40, 'evidence_kind':'observed'})
            if issue == '12':
                payload['platforms'] = {p: {'independent_tester':'tester-'+p,
                    'standard_user':True, 'first_install':True, 'host_activation':'PASS'}
                    for p in ('windows','macos','linux')}
            path = self.root / (issue + '.json')
            path.write_text(json.dumps(payload), encoding='utf-8')
            gates[issue] = {'evidence_kind':'observed', 'path':path.name,
                'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
        result = assess({'source_sha':'b'*40, 'gates':gates}, self.root)
        self.assertEqual(result['status'], 'REVIEW_REQUIRED')
        self.assertFalse(result['completion_notification_allowed'])
        self.assertNotIn('PASS', [g['status'] for g in result['gates'].values()])
