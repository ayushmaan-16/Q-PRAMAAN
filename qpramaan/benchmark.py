"""Reproducible evaluation from Born-derived Pauli-channel probabilities."""
import argparse
import json
import math
import platform
import time
from pathlib import Path
import numpy as np
from .detection import wilson, margin
from .quantum import correctness, BORN, pauli_weights
from .protocol import distribute, verify, bob_forge
from .planner import plan


def channel_rates(q):
    # All six eigenstates have matched-basis mismatch q for isotropic Pauli noise.
    rates = []
    for s in range(6):
        p0 = float(np.dot(BORN[s, 0, :, s // 2], pauli_weights(q)))
        rates.append(1 - p0 if s % 2 == 0 else p0)
    return float(np.mean(rates))


def evaluate(trials=20000, per_branch=2048, seed=26141, protocol_trials=200):
    start = time.perf_counter()
    rng = np.random.default_rng(seed)
    alpha, q0 = .01, .02
    sizes = np.array([per_branch // 3 + (i < per_branch % 3) for i in range(3)])
    configs = {"ordinary": [.02] * 4, "targeted": [.08, 0, 0, 0],
               "benign_drift": [.08] * 4, "sparse": [.026, .02, .02, .02],
               "indistinguishable": [.02] * 4, "intercept_resend": [1 / 3 + .02 / 3] * 4}
    results = []
    for name, rates in configs.items():
        probs = np.array([channel_rates(q) for q in rates])
        counts = rng.binomial(sizes[None, None, :], probs[None, :, None], (trials, 4, 3))
        pooled = counts.sum(axis=(1, 2)) / (4 * per_branch)
        # Standalone comparator gets its full alpha. Full detector splits alpha over 20 tests.
        baseline_flags = pooled > q0 + margin(4 * per_branch, alpha)
        each_alpha = alpha / 20
        branch_flags = np.any(counts.sum(axis=2) / per_branch > q0 + margin(per_branch, each_alpha), axis=1)
        basis_flags = np.any(counts.sum(axis=1) / (4 * sizes) > q0 + np.sqrt(np.log(1 / each_alpha) / (8 * sizes)), axis=1)
        joint_flags = np.any(counts / sizes > q0 + np.sqrt(np.log(1 / each_alpha) / (2 * sizes)), axis=(1, 2))
        full_flags = branch_flags | basis_flags | joint_flags | (pooled > q0 + margin(4 * per_branch, each_alpha))
        record = {"scenario": name, "expected_pooled_error": float(np.mean(probs)), "trials": trials}
        for method, flags in (("pooled", baseline_flags), ("full", full_flags)):
            k = int(flags.sum())
            record[method] = {"flagged": k, "rate": k / trials, "wilson_95": wilson(k, trials)}
        results.append(record)
    # Replicate the original four-branch-only feasibility study separately.
    original_rng = np.random.default_rng(seed)
    ordinary = original_rng.binomial(per_branch, .02, (trials, 4))
    targeted = original_rng.binomial(per_branch, [ .08, 0, 0, 0], (trials, 4))
    reference = {"kind": "Four-branch-only feasibility experiment; distinct from the 20-test production family",
                 "ordinary_flags": int(np.any(ordinary / per_branch > .02 + margin(per_branch, alpha / 4), axis=1).sum()),
                 "targeted_flags": int(np.any(targeted / per_branch > .02 + margin(per_branch, alpha / 4), axis=1).sum()),
                 "trials": trials}
    attacks = {"honest_accept": 0, "forge_accept": 0, "repudiation_success": 0, "setup_abort": 0}
    for _ in range(protocol_trials):
        mat = distribute(2048, rng)
        if not mat["setup_ok"]:
            attacks["setup_abort"] += 1
            continue
        d = mat["private"][1]
        b = verify(d, 1, mat["records"]["Bob"], 2048, .02)
        c = verify(d, 1, mat["records"]["Charlie"], 2048, .04)
        attacks["honest_accept"] += b["status"] == c["status"] == "VALID"
        forged = bob_forge(mat["own"]["Bob"], mat["records"]["Bob"][0][1], 0, rng)
        attacks["forge_accept"] += verify(forged, 0, mat["records"]["Charlie"], 2048, .04)["status"] == "VALID"
        rep = distribute(2048, rng, repudiation=True)
        d = rep["private"][1]
        rb = verify(d, 1, rep["records"]["Bob"], 2048, .02)
        rc = verify(d, 1, rep["records"]["Charlie"], 2048, .04)
        attacks["repudiation_success"] += rep["setup_ok"] and rb["status"] == "VALID" and rc["status"] == "INVALID"
    attack_results = {k: {"count": int(v), "trials": protocol_trials, "wilson_95": wilson(v, protocol_trials)} for k, v in attacks.items()}
    timings = []
    for length in (1024, 4096, 16384, 65536):
        times = []
        for _ in range(5):
            t = time.perf_counter()
            mat = distribute(length, rng)
            verify(mat["private"][1], 1, mat["records"]["Charlie"], length, .04)
            times.append((time.perf_counter() - t) * 1000)
        timings.append({"length": length, "median_ms": float(np.median(times)), "scope": "distribution + one verification, no HTTP/MAC"})
    return {"version": "1.0.0", "seed": seed, "alpha": alpha, "per_branch": per_branch,
            "environment": {"python": platform.python_version(), "numpy": np.__version__, "platform": platform.platform()},
            "channel_results": results, "reference_four_branch": reference,
            "protocol_results": attack_results, "timing": timings, "correctness": correctness(),
            "planner": plan(), "elapsed_seconds": round(time.perf_counter() - start, 3),
            "notes": ["Synthetic independent Pauli channels; fixed balanced branch and basis quotas; known baseline.",
                      "Full detector uses 20 tests with Bonferroni allocation; standalone pooled comparator gets full 1% budget.",
                      "The attacker that reproduces ordinary noise is intentionally undetectable from these measurements.",
                      "Benign drift is a channel-model anomaly, not an identified cyberattack.",
                      "Protocol attack trials use private reproducible laboratory material only; never reuse it to sign live data.",
                      "No successful attack observed is a finite-sample observation, not a universal security proof."]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=int, default=20000)
    parser.add_argument("--protocol-trials", type=int, default=200)
    parser.add_argument("--output", default="output/benchmark.json")
    args = parser.parse_args()
    result = evaluate(args.trials, protocol_trials=args.protocol_trials)
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(out), "seconds": result["elapsed_seconds"], "channels": result["channel_results"],
                      "protocol": result["protocol_results"]}, indent=2))
