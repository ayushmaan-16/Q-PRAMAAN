"""Inspectable Physics: Single-frame quantum state tracing and single-shot sandbox."""
import numpy as np
from .quantum import STATES, NAMES, PAULIS, teleport, I, X, Y, Z, H, BORN, pauli_weights

BELL_NAMES = ("|Φ⁺⟩ = (|00⟩+|11⟩)/√2", "|Ψ⁺⟩ = (|01⟩+|10⟩)/√2",
              "|Φ⁻⟩ = (|00⟩-|11⟩)/√2", "|Ψ⁻⟩ = (|01⟩-|10⟩)/√2")
BELL_LABELS = ("00", "01", "10", "11")
PAULI_NAMES = ("I (Identity / No noise)", "X (Bit flip · σ_x)",
               "Y (Bit & phase flip · σ_y)", "Z (Phase flip · σ_z)")
PAULI_LABELS = ("I", "X", "Y", "Z")
BASIS_NAMES = ("Z (|0⟩ / |1⟩)", "X (|+⟩ / |-⟩)", "Y (|+i⟩ / |-i⟩)")
BASIS_LABELS = ("Z", "X", "Y")

DIRAC_REPR = {
    0: "|0⟩",
    1: "|1⟩",
    2: "(|0⟩ + |1⟩)/√2  [|+⟩]",
    3: "(|0⟩ - |1⟩)/√2  [|-⟩]",
    4: "(|0⟩ + i|1⟩)/√2 [|+i⟩]",
    5: "(|0⟩ - i|1⟩)/√2 [|-i⟩]"
}


def bloch_vector(psi):
    """Compute (rx, ry, rz) Bloch sphere coordinates for a normalized 2D complex state."""
    a, b = psi[0], psi[1]
    rx = float(2 * (np.conj(a) * b).real)
    ry = float(2 * (np.conj(a) * b).imag)
    rz = float((abs(a)**2 - abs(b)**2).real)
    return {"x": round(rx, 4), "y": round(ry, 4), "z": round(rz, 4)}


def format_vector(psi):
    """Format 2D complex state vector for JSON serialization."""
    return [{"real": round(float(c.real), 5), "imag": round(float(c.imag), 5)} for c in psi]


def simulate_frame(state_idx, branch_idx, pauli_idx, basis_idx):
    """Compute exact physics for an arbitrary (state, branch, pauli, basis) frame."""
    state_idx = int(np.clip(state_idx, 0, 5))
    branch_idx = int(np.clip(branch_idx, 0, 3))
    pauli_idx = int(np.clip(pauli_idx, 0, 3))
    basis_idx = int(np.clip(basis_idx, 0, 2))

    psi_alice = STATES[state_idx]
    corrected_clean, branch_prob = teleport(psi_alice, branch_idx)
    u_pauli = PAULIS[pauli_idx]

    # Pauli channel acts on the physical qubit; receiver applies unitary correction
    # Equivalent to U_pauli acting on the recovered teleported state
    psi_received = u_pauli @ corrected_clean
    psi_received = psi_received / np.linalg.norm(psi_received)

    # Quantum fidelity with Alice's original state: |⟨ψ_alice | ψ_received⟩|²
    fidelity = float(abs(np.vdot(psi_alice, psi_received)) ** 2)

    # Projective measurement Born probabilities in chosen basis
    ref_0 = STATES[2 * basis_idx]
    ref_1 = STATES[2 * basis_idx + 1]
    p0 = float(np.clip(abs(np.vdot(ref_0, psi_received)) ** 2, 0.0, 1.0))
    p1 = float(np.clip(abs(np.vdot(ref_1, psi_received)) ** 2, 0.0, 1.0))

    # Normalize to avoid float epsilon discrepancies
    total_p = p0 + p1
    if total_p > 0:
        p0, p1 = p0 / total_p, p1 / total_p

    # Symmetrized state elimination logic (P1-prime protocol):
    # Recipient eliminates incompatible state based on measurement outcome
    elim_0 = 2 * basis_idx + 1  # If outcome 0 is measured, state 1 in this basis is eliminated
    elim_1 = 2 * basis_idx      # If outcome 1 is measured, state 0 in this basis is eliminated

    # Alice's declaration for signing bit (BB84 subset: states 0, 1, 2, 3)
    alice_name = NAMES[state_idx]
    mismatch_if_0 = (state_idx == elim_0)
    mismatch_if_1 = (state_idx == elim_1)

    z = branch_idx >> 1
    x = branch_idx & 1
    corr_formula = "I" if (z == 0 and x == 0) else ("X" if (z == 0 and x == 1) else ("Z" if (z == 1 and x == 0) else "Z · X"))

    return {
        "alice": {
            "index": state_idx,
            "name": alice_name,
            "dirac": DIRAC_REPR[state_idx],
            "basis": "Z" if state_idx < 2 else ("X" if state_idx < 4 else "Y"),
            "vector": format_vector(psi_alice),
            "bloch": bloch_vector(psi_alice)
        },
        "bell": {
            "branch": branch_idx,
            "label": BELL_LABELS[branch_idx],
            "state_name": BELL_NAMES[branch_idx],
            "feed_forward": {"z": z, "x": x},
            "correction_operator": corr_formula,
            "branch_probability": branch_prob
        },
        "channel": {
            "pauli": PAULI_LABELS[pauli_idx],
            "name": PAULI_NAMES[pauli_idx],
            "is_perturbed": pauli_idx != 0,
            "is_targeted_branch": branch_idx == 0
        },
        "receiver": {
            "vector": format_vector(psi_received),
            "bloch": bloch_vector(psi_received),
            "fidelity": round(fidelity, 6)
        },
        "measurement": {
            "basis_index": basis_idx,
            "basis_name": BASIS_NAMES[basis_idx],
            "basis_label": BASIS_LABELS[basis_idx],
            "p0": round(p0, 4),
            "p1": round(p1, 4),
            "eigenstates": [NAMES[2 * basis_idx], NAMES[2 * basis_idx + 1]],
            "eliminated_if_0": NAMES[elim_0],
            "eliminated_if_1": NAMES[elim_1],
            "mismatch_if_0": mismatch_if_0,
            "mismatch_if_1": mismatch_if_1
        }
    }


def sample_experiment_traces(scenario, seed, n_frames=24, baseline=0.02):
    """Generate a representative sample of individual qubit frames from the scenario."""
    rng = np.random.default_rng(seed)
    frames = []

    for i in range(n_frames):
        branch = i % 4
        state = int(rng.integers(0, 4))
        basis = int(rng.integers(0, 2))

        q = baseline
        if scenario == "targeted":
            q = min(4 * baseline, 2 / 3) if branch == 0 else 0.0
        elif scenario == "noise":
            q = max(0.08, baseline)
        elif scenario == "sparse":
            q = (0.9 * baseline + 0.1 * min(4 * baseline, 2 / 3)) if branch == 0 else baseline

        weights = pauli_weights(q)
        pauli_idx = int(rng.choice(4, p=weights))

        sim = simulate_frame(state, branch, pauli_idx, basis)

        measured_bit = 0 if rng.random() < sim["measurement"]["p0"] else 1
        eliminated_state = sim["measurement"]["eliminated_if_0"] if measured_bit == 0 else sim["measurement"]["eliminated_if_1"]
        observed_state = sim["measurement"]["eigenstates"][measured_bit]

        declared_state = NAMES[state]
        mismatch = (declared_state == eliminated_state)
        is_targeted_attack = (scenario == "targeted" and branch == 0 and pauli_idx != 0)

        frames.append({
            "frame_id": i,
            "branch": branch,
            "branch_label": BELL_LABELS[branch],
            "state_idx": state,
            "state_name": declared_state,
            "state_dirac": DIRAC_REPR[state],
            "basis": BASIS_LABELS[basis],
            "feed_forward": sim["bell"]["feed_forward"],
            "correction": sim["bell"]["correction_operator"],
            "pauli": PAULI_LABELS[pauli_idx],
            "pauli_name": PAULI_NAMES[pauli_idx],
            "is_perturbed": pauli_idx != 0,
            "is_targeted_attack": is_targeted_attack,
            "fidelity": sim["receiver"]["fidelity"],
            "p0": sim["measurement"]["p0"],
            "p1": sim["measurement"]["p1"],
            "measured_bit": measured_bit,
            "measured_state": observed_state,
            "eliminated_state": eliminated_state,
            "declared_state": declared_state,
            "mismatch": mismatch,
            "alice_bloch": sim["alice"]["bloch"],
            "receiver_bloch": sim["receiver"]["bloch"]
        })

    return frames
