"""Small-state quantum reference and vectorized independent-signal simulation."""
import numpy as np

I = np.eye(2, dtype=complex)
X = np.array([[0, 1], [1, 0]], complex)
Y = np.array([[0, -1j], [1j, 0]], complex)
Z = np.diag([1, -1]).astype(complex)
H = np.array([[1, 1], [1, -1]], complex) / np.sqrt(2)
PAULIS = (I, X, Y, Z)
NAMES = ("0", "1", "+", "-", "+i", "-i")
STATES = np.array([np.array(v, complex) / np.linalg.norm(v)
                   for v in ([1, 0], [0, 1], [1, 1], [1, -1], [1, 1j], [1, -1j])])
BELL = np.array([1, 0, 0, 1], complex) / np.sqrt(2)
CNOT = np.zeros((8, 8), complex)
for _i in range(8):
    _q, _a, _b = (_i >> 2) & 1, (_i >> 1) & 1, _i & 1
    CNOT[(_q << 2) | ((_a ^ _q) << 1) | _b, _i] = 1


def teleport(psi, branch):
    """branch=(z << 1)|x, sender Q first, entanglement half A second.

    Return corrected receiver state and Born probability of that branch.
    Bob applies X^x first, then Z^z. Each call uses three qubits only.
    """
    v = np.kron(np.kron(H, I), I) @ CNOT @ np.kron(psi, BELL)
    out = v[2 * branch:2 * branch + 2]
    prob = float(np.vdot(out, out).real)
    z, x = branch >> 1, branch & 1
    out = np.linalg.matrix_power(Z, z) @ np.linalg.matrix_power(X, x) @ out
    return out / np.sqrt(prob), prob


# Born probabilities, derived from the circuit rather than arbitrary error coins.
# Dimensions: prepared eigenstate, Bell branch, Pauli operation, measured basis.
BORN = np.empty((6, 4, 4, 3))
for _s, _psi in enumerate(STATES):
    for _c in range(4):
        _out, _ = teleport(_psi, _c)
        for _p, _u in enumerate(PAULIS):
            for _basis in range(3):
                BORN[_s, _c, _p, _basis] = np.clip(
                    abs(np.vdot(STATES[2 * _basis], _u @ _out)) ** 2, 0, 1)
BORN[np.isclose(BORN, 0, atol=1e-14)] = 0
BORN[np.isclose(BORN, 1, atol=1e-14)] = 1


def measure_batch(states, bases, branches, paulis, rng):
    """Return projective outcomes; 0 is the positive eigenstate of the basis."""
    p0 = BORN[states, branches, paulis, bases]
    return (rng.random(len(states)) >= p0).astype(np.int8)


def pauli_weights(error_rate):
    """Isotropic Pauli channel with matched-basis mismatch q in [0, 2/3]."""
    if not 0 <= error_rate <= 2 / 3:
        raise ValueError("Pauli matched-basis error must lie in [0, 2/3].")
    return [1 - 1.5 * error_rate, error_rate / 2, error_rate / 2, error_rate / 2]


def correctness():
    checks = []
    for name, psi in zip(NAMES, STATES):
        for branch in range(4):
            out, p = teleport(psi, branch)
            checks.append({"state": name, "branch": f"{branch:02b}",
                           "fidelity": min(1., float(abs(np.vdot(psi, out)) ** 2)),
                           "branch_probability": p})
    return {"checks": checks, "count": len(checks),
            "minimum_fidelity": min(c["fidelity"] for c in checks),
            "maximum_branch_probability_error": max(abs(c["branch_probability"] - .25) for c in checks)}
