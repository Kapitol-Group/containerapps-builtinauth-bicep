from __future__ import annotations

import unittest

from services.batch_metrics import build_batch_metrics


class BatchMetricsTests(unittest.TestCase):
    def test_build_batch_metrics_uses_exact_submission_and_completion(self) -> None:
        batch = {
            'submitted_at': '2026-03-12T10:00:00',
            'status': 'completed',
            'completed_at': '2026-03-12T10:10:00',
            'uipath_reference': 'batch-batch-1',
            'submission_attempts': [
                {
                    'timestamp': '2026-03-12T10:00:00',
                    'started_at': '2026-03-12T10:00:00',
                    'completed_at': '2026-03-12T10:01:00',
                    'duration_seconds': 60,
                    'status': 'success',
                }
            ],
        }
        progress = {
            'status_counts': {'queued': 0, 'extracted': 1, 'failed': 0, 'exported': 0},
            'files': [
                {
                    'filename': 'a101.pdf',
                    'status': 'extracted',
                    'created_at': '2026-03-12T10:00:00',
                    'updated_at': '2026-03-12T10:09:00',
                }
            ],
        }

        metrics = build_batch_metrics(batch, progress)

        self.assertEqual(metrics['submission']['source'], 'exact')
        self.assertEqual(metrics['submission']['duration_seconds'], 60)
        self.assertEqual(metrics['completion']['source'], 'exact')
        self.assertEqual(metrics['completion']['completed_at'], '2026-03-12T10:10:00')
        self.assertEqual(metrics['extraction']['started_at'], '2026-03-12T10:01:00')
        self.assertEqual(metrics['extraction']['duration_seconds'], 480)
        self.assertEqual(metrics['total']['duration_seconds'], 600)

    def test_build_batch_metrics_falls_back_for_legacy_completed_batch(self) -> None:
        batch = {
            'submitted_at': '2026-03-12T10:00:00',
            'status': 'completed',
            'completed_at': '',
            'uipath_reference': 'batch-batch-2',
            'submission_attempts': [
                {
                    'timestamp': '2026-03-12T10:00:00',
                    'status': 'success',
                }
            ],
        }
        progress = {
            'status_counts': {'queued': 0, 'extracted': 0, 'failed': 0, 'exported': 2},
            'files': [
                {
                    'filename': 'a101.pdf',
                    'status': 'exported',
                    'created_at': '2026-03-12T10:02:00',
                    'updated_at': '2026-03-12T10:07:00',
                },
                {
                    'filename': 'a102.pdf',
                    'status': 'exported',
                    'created_at': '2026-03-12T10:03:00',
                    'updated_at': '2026-03-12T10:06:00',
                },
            ],
        }

        metrics = build_batch_metrics(batch, progress)

        self.assertEqual(metrics['submission']['source'], 'estimated')
        self.assertEqual(metrics['submission']['duration_seconds'], 120)
        self.assertEqual(metrics['completion']['source'], 'estimated')
        self.assertEqual(metrics['completion']['completed_at'], '2026-03-12T10:07:00')
        self.assertEqual(metrics['throughput']['processed_files'], 2)
        self.assertEqual(metrics['throughput']['source'], 'estimated')


if __name__ == '__main__':
    unittest.main()
