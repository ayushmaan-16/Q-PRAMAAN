"""Reference-model bounds from Wallden et al. Eqs (2),(3), plus exchange abort."""
import math

ASSUMPTIONS = [
    "Ideal authenticated quantum delivery (teleportation treated as an identity channel)",
    "Authenticated classical channels; secret Bob-Charlie exchange",
    "Uniform independent BB84 signing material; bounded recipient copies",
    "One-time signing, uncompromised devices, three parties, original threshold normalization",
    "Reference bounds are not a composable security proof for the modified noisy implementation",
]


def reference_bounds(length, sa=.02, sv=.04, r=.05):
    if length < 1 or not 0 <= sa < sv < 1 or not 0 < r < .5:
        raise ValueError("Require L >= 1, 0 <= s_a < s_v < 1 and 0 < r < 0.5.")
    k = length * (.5 - r)
    gap = .125 - sv * length / k
    return {"length": length, "sa": sa, "sv": sv, "r": r,
            "forgery": math.exp(-2 * gap * gap * k) if gap > 0 else 1.,
            "repudiation": math.exp(-(sv - sa) ** 2 * length / 2),
            "exchange_abort_union": min(1., 8 * math.exp(-2 * r * r * length)),
            "bell_pairs": 4 * length, "teleportation_classical_bits": 8 * length,
            "projective_measurements": 4 * length,
            "verification_work": "O(L) per one-bit verification",
            "authentication_and_probes": "Additional; excluded from these base resource counts"}


def plan(target=1e-6, budget=1_000_000, model="ideal", sa=.02, sv=.04, r=.05):
    if not 0 < target < 1 or not 1 <= budget <= 1_000_000_000:
        raise ValueError("Invalid target or Bell-pair budget.")
    base = {"target_per_bound": target, "budget_bell_pairs": budget,
            "assumptions": ASSUMPTIONS, "source": "https://arxiv.org/pdf/1403.5551",
            "source_equations": "(2), (3); exchange abort uses Hoeffding and a four-exchange union bound",
            "claim": "Conditional reference estimates, not measured attack probabilities or a composable total."}
    if model != "ideal":
        return {**base, "status": "UNAVAILABLE", "reason": "Bound unavailable for this model. No ideal bound is assigned to noisy, lossy, or externally tampered delivery.", "frontier": [], "selected": None}
    frontier = [reference_bounds(2 ** p, sa, sv, r) for p in range(8, 21)]
    candidates = [v for v in frontier if max(v["forgery"], v["repudiation"], v["exchange_abort_union"]) <= target]
    selected = next((v for v in candidates if v["bell_pairs"] <= budget), None)
    return {**base, "status": "SUPPORTED" if selected else "BUDGET_EXCEEDED",
            "selected": selected, "frontier": frontier,
            "minimum_supported_length": candidates[0]["length"] if candidates else None,
            "search": "Smallest supported power-of-two L from 256 through 1,048,576; thresholds held fixed."}
