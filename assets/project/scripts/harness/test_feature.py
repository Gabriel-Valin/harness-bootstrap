import importlib.util
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
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

    def test_unittest_skips_and_expected_failures_are_gaps(self):
        for text in [
            "Ran 3 tests in 0.001s\n\nOK (skipped=1)",
            "Ran 3 tests in 0.001s\n\nOK (expected failures=1)",
            "Ran 3 tests in 0.001s\n\nOK (skipped=2, expected failures=1)",
        ]:
            with self.subTest(text=text):
                self.assertEqual(self.gap(text), "skipped some tests")

    def test_unittest_success_counts_as_passing_tests(self):
        self.assertIsNone(self.gap("Ran 2 tests in 0.003s\n\nOK", require_positive=True))
        self.assertIsNone(self.gap("....\nRan 4 tests in 0.1s\n\nOK\n", require_positive=True))
        self.assertEqual(
            self.gap("Ran 2 tests in 0.003s\n\nFAILED (failures=1)", require_positive=True),
            "reports no passing tests",
        )

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


class SealTest(unittest.TestCase):
    """Runs feature.py as a CLI inside a throwaway git repository."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)
        shutil.copytree(HERE.parent.parent / "harness" / "templates", self.root / "harness" / "templates")
        self.run_ok("init", "T-1", "--title", "seal test")
        self.run_ok("add", "--id", "F1", "--behavior", "works", "--verify", "true")
        self.list_path = self.root / ".harness" / "tasks" / "T-1" / "feature_list.json"

    def tearDown(self):
        self.tmp.cleanup()

    def cli(self, *args):
        env = dict(os.environ)
        env.pop("HARNESS_TASK", None)
        return subprocess.run(
            [sys.executable, str(HERE / "feature.py"), *args],
            cwd=self.root,
            env=env,
            capture_output=True,
            text=True,
        )

    def run_ok(self, *args):
        proc = self.cli(*args)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return proc

    def data(self):
        return json.loads(self.list_path.read_text(encoding="utf-8"))

    def write(self, data):
        self.list_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def verify_f1(self):
        self.run_ok("start", "F1")
        self.run_ok("verify", "F1")
        self.assertEqual(self.data()["items"][0]["status"], "passing")

    def test_commands_keep_the_seal_valid(self):
        self.verify_f1()
        self.run_ok("status")
        self.run_ok("validate")

    def test_hand_set_passing_is_refused_until_recover(self):
        data = self.data()
        data["items"][0]["status"] = "passing"
        data["items"][0]["evidence"] = {"command": "true", "exit_code": 0}
        self.write(data)
        proc = self.cli("status")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("changed outside feature.py", proc.stderr)
        self.assertIn("recover", proc.stderr)
        self.run_ok("recover", "--reason", "test")
        item = self.data()["items"][0]
        self.assertEqual(item["status"], "not_started")
        self.assertIsNone(item["evidence"])
        self.run_ok("status")

    def test_hand_removed_item_is_refused(self):
        self.verify_f1()
        data = self.data()
        data["items"] = []
        self.write(data)
        self.assertEqual(self.cli("next").returncode, 1)

    def test_unsealed_state_is_refused(self):
        self.verify_f1()
        data = self.data()
        del data["seal"]
        self.write(data)
        proc = self.cli("status")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("no seal", proc.stderr)

    def test_behavior_text_stays_editable_by_hand(self):
        data = self.data()
        data["items"][0]["behavior"] = "works, reworded"
        self.write(data)
        self.run_ok("status")

    def test_changed_evidence_log_fails_validate(self):
        self.verify_f1()
        log = self.root / self.data()["items"][0]["evidence"]["log"]
        log.write_text("rewritten\n", encoding="utf-8")
        proc = self.cli("validate")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("changed after the run", proc.stdout)

    def test_recover_with_intact_seal_changes_nothing(self):
        self.verify_f1()
        before = self.data()
        self.run_ok("recover", "--reason", "no-op")
        self.assertEqual(self.data(), before)


if __name__ == "__main__":
    unittest.main()
