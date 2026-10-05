"""Attack harness. Only this layer knows which experiment was selected."""
import numpy as np
from .quantum import measure_batch, pauli_weights

SCENARIOS = {
    "legitimate": ("Legitimate operation", "Ideal signature delivery with ordinary 2% diagnostic noise."),
    "targeted": ("Hidden channel manipulation", "Same expected pooled error; Pauli disturbance concentrated in Bell outcome 00."),
    "forgery": ("Dishonest recipient forgery", "Bob guesses undisclosed signature material for the unsigned decision."),
    "impersonation": ("Impersonation", "An outsider submits a fabricated classical authentication tag."),
    "replay": ("Replay attempt", "An authentic release approval is submitted for execution twice."),
    "unauthorized": ("Unauthorized verification", "Eve requests access to a designated verification service."),
    "repudiation": ("Signer repudiation attempt", "Alice distributes inconsistent states to the two recipients."),
    "noise": ("Benign noise increase", "A changed channel also triggers an anomaly; measurements alone do not identify intent."),
    "sparse": ("Sparse manipulation", "Only one in ten outcome-00 signals is exposed to the stronger channel."),
    "loss": ("Missing observations", "Half the probes disappear in one teleportation outcome."),
    "uncalibrated": ("No calibration", "No trusted baseline is supplied, so channel status remains inconclusive."),
    "indistinguishable": ("Indistinguishable disturbance", "Adversarial Pauli noise has exactly the same observable distribution as ordinary noise."),
    "intercept": ("Intercept and resend", "An interceptor measures probes in a random Pauli basis and prepares that outcome."),
}


def probe_batch(scenario, seed, per_branch=2048, baseline=.02, link="Alice-Bob"):
    """Balanced branch strata for an explicitly conditional experiment.

    This models collecting a fixed quota for each Bell outcome, not a claim that
    a single unconditioned run has exactly equal branch counts. Bases and signs
    are random; sender labels are disclosed only after simulated receipt.
    """
    rng = np.random.default_rng(seed)
    rows = []
    for branch in range(4):
        states = rng.integers(0, 6, per_branch)
        bases = states // 2
        branches = np.full(per_branch, branch)
        q = baseline
        if scenario == "targeted":
            q = baseline * 4 if branch == 0 else 0.
        elif scenario == "noise":
            q = max(.08, baseline)
        elif scenario == "sparse" and branch == 0:
            q = .9 * baseline + .1 * min(4 * baseline, 2 / 3)
        paulis = rng.choice(4, per_branch, p=pauli_weights(q))
        if scenario == "intercept":
            eve_bases = rng.integers(0, 3, per_branch)
            eve_out = measure_batch(states, eve_bases, branches, np.zeros(per_branch, int), rng)
            resent = 2 * eve_bases + eve_out
            measured = measure_batch(resent, bases, branches, paulis, rng)
        else:
            measured = measure_batch(states, bases, branches, paulis, rng)
        keep = rng.random(per_branch) >= (.5 if scenario == "loss" and branch == 0 else 0.)
        for basis in range(3):
            selected = bases == basis
            observed = selected & keep
            rows.append({"link": link, "phase": "diagnostic", "basis": basis, "branch": branch,
                         "sent": int(selected.sum()), "n": int(observed.sum()),
                         "errors": int(np.sum(measured[observed] != states[observed] % 2))})
    return rows
