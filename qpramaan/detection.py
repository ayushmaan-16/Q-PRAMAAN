"""Fixed-horizon, one-sided Hoeffding tests. No attack labels enter this module."""
import math


def margin(n, alpha):
    return math.sqrt(math.log(1 / alpha) / (2 * n)) if n > 0 else 1.


def upper_bound(k, n, alpha):
    return min(1., k / n + margin(n, alpha)) if n else 1.


def analyze(rows, baseline=.02, alpha=.01, calibration=None,
            calibrated=True, min_samples=64, max_loss=.10):
    """rows hold only permissible revealed diagnostic counts.

    Family: pooled + 4 branch + 3 basis + 12 joint cells per link/phase.
    All 20 tests share alpha, including the pooled ablation comparator.
    Calibration, if supplied, uses half alpha and union-bound upper limits.
    Basis 0/1/2 is Z/X/Y. Insufficient coverage can never be a healthy verdict.
    """
    if not 0 < alpha < 1 or not 0 <= baseline <= 2 / 3:
        raise ValueError("Invalid alpha or baseline.")
    for row in rows:
        if (row["basis"] not in (0, 1, 2) or row["branch"] not in range(4)
                or not 0 <= row["errors"] <= row["n"] <= row["sent"]):
            raise ValueError("Invalid probe counts.")
    scopes = sorted({(r["link"], r["phase"]) for r in rows})
    specs = []
    for link, phase in scopes:
        scoped = [r for r in rows if (r["link"], r["phase"]) == (link, phase)]
        specs.append((link, phase, "pooled", "all", scoped))
        for c in range(4):
            specs.append((link, phase, "branch", f"{c:02b}", [r for r in scoped if r["branch"] == c]))
        for b in range(3):
            specs.append((link, phase, "basis", "ZXY"[b], [r for r in scoped if r["basis"] == b]))
        for c in range(4):
            for b in range(3):
                specs.append((link, phase, "joint", f"{'ZXY'[b]}/{c:02b}",
                              [r for r in scoped if r["branch"] == c and r["basis"] == b]))
    family = max(1, len(specs))
    test_alpha = alpha / (2 if calibration is not None else 1) / family
    tests, missing = [], not rows or not calibrated
    for link, phase, kind, label, group in specs:
        n, k, sent = (sum(r[key] for r in group) for key in ("n", "errors", "sent"))
        q0 = baseline
        cell_keys = {(r["basis"], r["branch"]) for r in group}
        if calibration is not None:
            cg = [r for r in calibration if r["link"] == link and r["phase"] == phase
                  and (r["basis"], r["branch"]) in cell_keys]
            cn, ck = sum(r["n"] for r in cg), sum(r["errors"] for r in cg)
            if cn < min_samples:
                missing = True
            q0 = upper_bound(ck, cn, alpha / 2 / family)
        loss = 1 - n / sent if sent else 1.
        sufficient = calibrated and n >= min_samples and loss <= max_loss
        missing |= not sufficient
        threshold = min(1., q0 + margin(n, test_alpha))
        rate = k / n if n else None
        flag = sufficient and rate > threshold
        tests.append({"link": link, "phase": phase, "kind": kind, "label": label,
                      "n": n, "errors": k, "sent": sent, "loss": loss,
                      "rate": rate, "baseline_upper": q0, "threshold": threshold,
                      "alpha": test_alpha, "flag": flag, "sufficient": sufficient})
    flagged = [t for t in tests if t["flag"]]
    status = "ANOMALY" if flagged else "INSUFFICIENT_EVIDENCE" if missing else "CONSISTENT"
    return {"status": status, "alpha_family": alpha, "tests": tests,
            "family_size": family, "flagged_count": len(flagged),
            "pooled_flags": sum(t["flag"] for t in tests if t["kind"] == "pooled"),
            "conditional_flags": sum(t["flag"] for t in tests if t["kind"] != "pooled"),
            "model": "Independent bounded observations; fixed batch; one-sided Hoeffding; union bound",
            "calibration": "independent finite calibration" if calibration is not None else
                           "known simulated baseline" if calibrated else "absent",
            "reason": "Measurements exceed the declared baseline envelope; cause is not identified."
                      if flagged else "Coverage or calibration is insufficient; operation is quarantined."
                      if missing else "No tested deviation exceeded this fixed-batch threshold; this is not a security proof."}


def wilson(k, n, z=1.959963984540054):
    if n == 0:
        return [0., 1.]
    p = k / n
    d = 1 + z * z / n
    center = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [max(0., center - half), min(1., center + half)]
