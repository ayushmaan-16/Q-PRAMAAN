"""P1-prime inspired three-party reference, with teleportation delivery.

Only designated participant views are passed to a forger. Private signing state
is never serialized in a public report. Signature seeds are never exported.
"""
import math
import numpy as np
from .quantum import measure_batch, pauli_weights


def distribute(length, rng, q=0., repudiation=False, transport=None, q_by_branch=None):
    private = rng.integers(0, 4, (2, length), dtype=np.int8)
    own = {}
    branches_all = []
    for recipient in ("Bob", "Charlie"):
        records, outputs, bases_all = [], [], []
        for bit in (0, 1):
            states = private[bit].copy()
            if repudiation and recipient == "Charlie":
                states[rng.random(length) < .30] ^= 1
            bases = rng.integers(0, 2, length)
            branches = rng.integers(0, 4, length)
            if transport:
                transport({"sender": "Alice", "recipient": recipient, "phase": "correction",
                           "bit": bit, "frames": branches.tolist()})
            if q_by_branch is None:
                paulis = rng.choice(4, length, p=pauli_weights(q))
            else:
                if len(q_by_branch) != 4:
                    raise ValueError("A rate is required for each Bell outcome.")
                paulis = np.empty(length, dtype=np.int8)
                for branch in range(4):
                    mask = branches == branch
                    paulis[mask] = rng.choice(4, int(mask.sum()), p=pauli_weights(q_by_branch[branch]))
            measured = measure_batch(states, bases, branches, paulis, rng)
            records.append(2 * bases + (1 - measured))
            outputs.append(2 * bases + measured)
            bases_all.append(bases)
            branches_all.append(np.bincount(branches, minlength=4))
        own[recipient] = {"excluded": np.array(records), "observed": np.array(outputs),
                          "send": rng.random((2, length)) < .5}
    records = {}
    for recipient, other in (("Bob", "Charlie"), ("Charlie", "Bob")):
        records[recipient] = []
        for bit in (0, 1):
            keep = ~own[recipient]["send"][bit]
            receive = own[other]["send"][bit]
            records[recipient].append([
                (np.flatnonzero(keep), own[recipient]["excluded"][bit, keep]),
                (np.flatnonzero(receive), own[other]["excluded"][bit, receive])])
    # Published exchange-count guard. A failed setup is not a signature rejection.
    counts = {who: [int(x.sum()) for x in own[who]["send"]] for who in own}
    if transport:
        for who, other in (("Bob", "Charlie"), ("Charlie", "Bob")):
            for bit in (0, 1):
                indices = np.flatnonzero(own[who]["send"][bit])
                transport({"sender": who, "recipient": other, "phase": "symmetrization", "bit": bit,
                           "indices": indices.tolist(), "excluded": own[who]["excluded"][bit, indices].tolist()}, secret=True)
    setup_ok = all(length * .45 <= n <= length * .55 for ns in counts.values() for n in ns)
    return {"private": private, "own": own, "records": records, "length": length,
            "setup_ok": setup_ok, "exchange_counts": counts,
            "bell_counts": np.sum(branches_all, axis=0).tolist()}


def verify(declaration, bit, records, length, threshold):
    if bit not in (0, 1) or len(declaration) != length or np.any((declaration < 0) | (declaration > 3)):
        return {"status": "INVALID", "reason": "Malformed declaration"}
    parts = [int(np.sum(declaration[indices] == excluded)) for indices, excluded in records[bit]]
    mismatches = sum(parts)
    # Strictly fewer than sL, exactly as in the reference (s=0 means zero errors).
    allowed = max(0, math.ceil(threshold * length) - 1)
    return {"status": "VALID" if mismatches <= allowed else "INVALID",
            "mismatches": mismatches, "own_mismatches": parts[0], "forwarded_mismatches": parts[1],
            "length": length, "checked_records": sum(len(indices) for indices, _ in records[bit]),
            "threshold_fraction": threshold, "allowed_mismatches": allowed,
            "normalization": "mismatches / original L; not divided by retained-record count",
            "reason": "Declaration is compatible with retained verification evidence."
                      if mismatches <= allowed else "Declaration exceeds the signature mismatch threshold."}


def bob_forge(bob_view, received_charlie, bit, rng):
    """Local projective measurement attack; does not receive Alice's private key.

    On Charlie's undisclosed positions Bob guesses his own measurement outcome.
    On disclosed positions he can avoid the known eliminated state. This is a
    concrete attack, not a claim of optimality for this entire modified protocol.
    """
    guesses = bob_view["observed"][bit].copy()
    indices, excluded = received_charlie
    for i, e in zip(indices, excluded):
        if guesses[i] == e:
            permitted = [s for s in range(4) if s != e and s != bob_view["excluded"][bit, i]]
            guesses[i] = rng.choice(permitted)
    return guesses
