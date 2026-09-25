import os
import unittest
from unittest import mock

from django.conf import settings
from django.test import SimpleTestCase

from wachtrijker.model.classifier import classifier

_WEIGHTS_PRESENT = os.path.isdir(os.path.join(settings.MODEL_DIR, "context"))


class ClassifyClampingTests(SimpleTestCase):
    """The clamping math should never leave the 1..5 range."""

    def _classify_with_prediction(self, value):
        stub = mock.Mock()
        stub.item.return_value = value
        with mock.patch("wachtrijker.model.classifier.predict.predict", return_value=stub):
            return classifier.classify("context", "wat tekst")

    def test_clamps_and_offsets(self):
        cases = {
            -1.0: 1,  # round(-1)+1=0 -> floored to 1
            0.0: 1,  # round(0)+1=1
            2.2: 3,  # round(2)+1=3
            4.6: 5,  # round(5)+1=6 -> capped to 5
            10.0: 5,  # capped to 5
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(self._classify_with_prediction(raw), expected)


@unittest.skipUnless(_WEIGHTS_PRESENT, "model weights not present")
class ClassifyRealModelTests(SimpleTestCase):
    """End-to-end test against the model."""

    def test_returns_score_in_range(self):
        score = classifier.classify(
            "context",
            "Ik krijg een NullPointerException in mijn Java-code en snap niet waarom.",
        )
        self.assertIsInstance(score, int)
        self.assertGreaterEqual(score, 1)
        self.assertLessEqual(score, 5)
