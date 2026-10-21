import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from compare_publication import normalize_build_time

class BuildTimeComparisonTests(unittest.TestCase):
    # Scenario: two identical article builds have different existing asset cache epochs.
    # Purpose: permit only the demonstrated volatile field, while keeping raw inventory hashes.
    def test_UnitT10_known_asset_epoch_is_ignored_only_for_semantic_comparison(self):
        before=b'<p>Body 123</p><link href="/assets/css/style.css?v=1234567890">'
        after=b'<p>Body 123</p><link href="/assets/css/style.css?v=1234567999">'
        self.assertEqual(normalize_build_time("about/index.html",before),normalize_build_time("about/index.html",after))
        self.assertNotEqual(before,after)

    # Scenario: article prose or an unrelated asset version changes.
    # Purpose: do not allow timestamp handling to hide regressions in retained publications.
    def test_UnitT20_content_and_unrelated_versions_remain_distinct(self):
        for before,after in [(b'<p>1234567890</p>',b'<p>1234567999</p>'),(b'<a href="/other?v=1234567890">',b'<a href="/other?v=1234567999">')]:
            self.assertNotEqual(normalize_build_time("about/index.html",before),normalize_build_time("about/index.html",after))
