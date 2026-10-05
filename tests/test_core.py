"""Behavioral checks for the submitted simulation, decisions and evidence."""
import tempfile
import unittest
from pathlib import Path

import numpy as np

from qpramaan.attacks import probe_batch
from qpramaan.auth import OneTimeAuthenticator
from qpramaan.detection import analyze
from qpramaan.evidence import check
from qpramaan.experiments import execute_report, run_experiment
from qpramaan.planner import plan
from qpramaan.protocol import bob_forge, distribute, verify
from qpramaan.quantum import correctness
from qpramaan.store import Store


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / "runs.sqlite")

    def tearDown(self):
        self.temp.cleanup()

    def test_teleportation_all_pauli_eigenstates_and_outcomes(self):
        result = correctness()
        self.assertEqual(result["count"], 24)
        self.assertAlmostEqual(result["minimum_fidelity"], 1., places=12)
        self.assertLess(result["maximum_branch_probability_error"], 1e-12)

    def test_signature_forwarding_and_recipient_view_forgery(self):
        rng = np.random.default_rng(42)
        material = distribute(4096, rng)
        self.assertTrue(material["setup_ok"])
        declaration = material["private"][1]
        self.assertEqual(verify(declaration, 1, material["records"]["Bob"], 4096, .02)["status"], "VALID")
        self.assertEqual(verify(declaration, 1, material["records"]["Charlie"], 4096, .04)["status"], "VALID")
        forged = bob_forge(material["own"]["Bob"], material["records"]["Bob"][0][1], 0, rng)
        self.assertEqual(verify(forged, 0, material["records"]["Charlie"], 4096, .04)["status"], "INVALID")

    def test_equal_average_channel_needs_conditional_checks(self):
        ordinary = analyze(probe_batch("legitimate", 26141, 4096, .02))
        targeted = analyze(probe_batch("targeted", 26141, 4096, .02))
        self.assertEqual(ordinary["status"], "CONSISTENT")
        self.assertEqual(targeted["status"], "ANOMALY")
        self.assertEqual(targeted["pooled_flags"], 0)
        self.assertGreater(targeted["conditional_flags"], 0)

    def test_targeted_channel_affects_signature_delivery_and_is_quarantined(self):
        report = run_experiment({"scenario": "targeted", "length": 4096,
                                 "per_branch": 4096, "seed": 26141}, self.store)
        self.assertEqual(report["config"]["signature_channel_rates_by_bell_outcome"], [.08, 0., 0., 0.])
        self.assertEqual(report["decisions"]["signature"], "VALID")
        self.assertEqual(report["decisions"]["channel"], "ANOMALY")
        self.assertEqual(report["decisions"]["operation"], "QUARANTINED")
        self.assertTrue(check(report)["matches"])
        self.assertNotIn("signing_material", report)
        self.assertTrue(all(set(row) == {"link", "phase", "basis", "branch", "sent", "n", "errors"}
                            for row in report["observations"]))

    def test_replay_preserves_signature_validity(self):
        report = run_experiment({"scenario": "legitimate", "length": 2048,
                                 "per_branch": 1024, "seed": 1}, self.store)
        first = execute_report(report["id"], self.store)
        second = execute_report(report["id"], self.store)
        self.assertEqual(first["status"], "EXECUTED")
        self.assertEqual(second["status"], "REPLAY_BLOCKED")
        self.assertEqual(second["report"]["decisions"]["signature"], "VALID")

    def test_one_time_authentication_rejects_tamper_and_reuse(self):
        auth = OneTimeAuthenticator()
        tag = auth.issue({"session": "one", "action": "approve"})
        self.assertFalse(auth.verify({"session": "one", "action": "reject"}, tag))
        self.assertFalse(auth.verify({"session": "one", "action": "approve"}, tag))

    def test_planner_refuses_unsupported_noise_model(self):
        ideal = plan(1e-6, 1_000_000, "ideal")
        noisy = plan(1e-6, 1_000_000, "noisy")
        self.assertEqual(ideal["status"], "SUPPORTED")
        self.assertLessEqual(ideal["selected"]["bell_pairs"], 1_000_000)
        self.assertEqual(noisy["status"], "UNAVAILABLE")
        self.assertIsNone(noisy["selected"])

    def test_missing_data_never_passes_as_normal(self):
        lost = analyze(probe_batch("loss", 3, 4096, .02))
        self.assertEqual(lost["status"], "INSUFFICIENT_EVIDENCE")

    def test_interactive_qubit_frame_physics_and_state_elimination(self):
        from qpramaan.trace import simulate_frame, sample_experiment_traces
        # Clean frame (+ state, branch 00, no noise, X basis) -> 100% fidelity, p0 = 1.0
        clean = simulate_frame(2, 0, 0, 1)
        self.assertEqual(clean["alice"]["name"], "+")
        self.assertEqual(clean["bell"]["label"], "00")
        self.assertAlmostEqual(clean["receiver"]["fidelity"], 1.0, places=5)
        self.assertAlmostEqual(clean["measurement"]["p0"], 1.0, places=5)
        self.assertFalse(clean["measurement"]["mismatch_if_0"])

        # Targeted Pauli-X error on |0⟩ in Z basis -> bit flips to |1⟩, p0 = 0.0, p1 = 1.0, causes mismatch if outcome 1 eliminates |0⟩
        flipped = simulate_frame(0, 0, 1, 0)
        self.assertEqual(flipped["alice"]["name"], "0")
        self.assertAlmostEqual(flipped["measurement"]["p0"], 0.0, places=5)
        self.assertAlmostEqual(flipped["measurement"]["p1"], 1.0, places=5)
        self.assertTrue(flipped["measurement"]["mismatch_if_1"])

        # Active sample trace generator contains 24 frames with valid attributes
        traces = sample_experiment_traces("targeted", 26141, 24, 0.02)
        self.assertEqual(len(traces), 24)
        self.assertTrue(all(f["branch"] in (0, 1, 2, 3) for f in traces))
        self.assertTrue(any(f["is_targeted_attack"] for f in traces))


if __name__ == "__main__":
    unittest.main()

