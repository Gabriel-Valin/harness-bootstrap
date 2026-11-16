import importlib.util
import pathlib
import sys
import unittest

sys.dont_write_bytecode = True

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("feature", HERE / "feature.py")
feature = importlib.util.module_from_spec(spec)
spec.loader.exec_module(feature)


class ProofGapTest(unittest.TestCase):
    def gap(self, text, require_positive=False):
        return feature.proof_gap(text, require_positive=require_positive)

    def test_runner_summaries_with_skipped_or_todo_tests_are_gaps(self):
        for text in [
            "Tests  74 passed | 1 skipped (75)",
            "  Tests  1 skipped (1)",
            "Tests  1 passed | 1 todo (2)",
            "Tests:       1 skipped, 2 passed, 3 total",
            "Tests:       2 passed, 1 todo, 3 total",
            "=== 1 skipped, 2 passed in 0.10s ===",
            "=== 2 passed, 1 skipped in 0.1s ===",
            "  1 skipped",
        ]:
            with self.subTest(text=text):
                self.assertEqual(self.gap(text), "skipped some tests")

    def test_zero_test_runs_are_gaps(self):
        for text in [
            "No test files found, exiting with code 0",
            "Test Files  no tests",
            "  Tests  no tests",
            "Ran 0 tests",
        ]:
            with self.subTest(text=text):
                self.assertEqual(self.gap(text), "ran no tests")

    def test_ordinary_application_output_is_not_a_gap(self):
        for text in [
            "booking-sync: 2 skipped appointments",
            "Tests run: 2 skipped appointments",
            "=== 2 skipped appointments ===",
            "Test data loaded: 2 skipped appointments",
            "    2 skipped appointments",
            "Skipped 3 slots",
            "Tests  0 skipped (0)",
        ]:
            with self.subTest(text=text):
                self.assertIsNone(self.gap(text))

    def test_clean_summaries_are_not_gaps(self):
        for text in [
            "  Tests  95 passed (95)",
            "Tests:       3 passed, 3 total",
            "=== 3 passed in 0.02s ===",
            "  3 passed (5.2s)",
        ]:
            with self.subTest(text=text):
                self.assertIsNone(self.gap(text))

    def test_require_tests_demands_a_passing_summary(self):
        self.assertEqual(self.gap("", require_positive=True), "reports no passing tests")
        self.assertEqual(self.gap("Tests  2 passed (2)", require_positive=True), None)
        self.assertEqual(
            self.gap("Tests  1 passed | 1 todo (2)", require_positive=True),
            "skipped some tests",
        )


if __name__ == "__main__":
    unittest.main()
