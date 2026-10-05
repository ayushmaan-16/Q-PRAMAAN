# Q-PRAMAAN

**Cache Hit · SIH Problem Statement SIH26141 · Team 125961**

Q-PRAMAAN is a local software laboratory for quantum digital signature (QDS) threat detection. It implements a three-party, BB84 P1′-inspired signature workflow with simulated Bell-pair teleportation; independently samples Pauli-channel diagnostic probes; and reports signature validity, channel status, and request authorization as separate decisions. It uses **no AI, machine learning, or trained model**.

The distinctive demonstration gives two channels the same **expected pooled error rate of 2%**. Ordinary noise has 2% error in each Bell-outcome group. A targeted Pauli disturbance has 8% in outcome `00` and 0% in the other three groups. In a seeded evaluation of 20,000 batches per condition, the pooled detector flagged **0/20,000 targeted batches** while the full conditional detector flagged **19,967/20,000**. Both flagged 0/20,000 ordinary batches. These are simulated, independent-signal results under a known baseline, not physical-device data or a proof of unconditional security.

## Run the demo

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\run.ps1
```

Open <http://127.0.0.1:8765>. The server binds to the loopback address only. If Python and NumPy are already installed, `python -m qpramaan.server` also works. The dashboard defaults to the hidden channel manipulation scenario.

The **Laboratory** runs legitimate, targeted-channel, forgery, impersonation, replay, unauthorized-verification, repudiation, benign drift, sparse disturbance, loss, uncalibrated, indistinguishable, and intercept/resend scenarios. **Evidence** exposes measurements and thresholds. **Resource planner** evaluates published reference bounds only when its ideal-channel assumptions apply. **Evaluation** shows the reproducible comparison stored in [`output/benchmark.json`](output/benchmark.json).

To reproduce the benchmark and run checks:

```powershell
python -m qpramaan.benchmark --trials 20000 --protocol-trials 200 --output output/benchmark.json
python -m unittest discover -s tests -v
```

Download a report from the dashboard and independently recompute its statistical decision:

```powershell
python -m qpramaan.evidence path\to\qpramaan-evidence.json
```

The recomputation checks arithmetic, not the provenance of the file or a quantum-security guarantee.

## What the prototype implements

| Problem deliverable | Implemented component |
|---|---|
| Mathematical model | Three-qubit teleportation circuit, six Pauli eigenstates, BB84 state elimination, thresholds, finite-sample tests and conditional reference bounds. |
| Detection framework | Twenty fixed-batch tests over pooled, Bell-outcome, basis, and joint groups; loss and calibration checks; separate identity, freshness and authorization outcomes. |
| Signature module | Alice prepares one-bit signatures for approve/reject; Bob verifies directly; Charlie verifies a forwarded declaration after private record symmetrization. |
| Attack simulator | Honest, forging, impersonation, replay, unauthorized access, repudiation, channel manipulation, loss, drift and indistinguishable-noise experiments. |
| Working prototype | Loopback API, browser dashboard, SQLite execution receipts, evidence export, resource planner and benchmark view. |

For the full assumptions and equations, see [`docs/SECURITY_MODEL.md`](docs/SECURITY_MODEL.md). For a short live walk-through, see [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md).

## Scientific scope

This is an **assurance prototype and simulation**. P1′ is adapted by delivering states through simulated teleportation; the reference paper's security proof does not automatically transfer to the modified or noisy implementation. The resource planner only displays published bounds for its ideal authenticated delivery model, and returns *bound unavailable for this model* otherwise. A detector alarm means the observations depart from the declared baseline under the stated sampling assumptions. It cannot, from those counts alone, identify malicious intent. Diagnostic samples are separate from usable signature material, and the private signing sequence never appears in exported reports.

## Sources

- [Wallden et al., Quantum digital signatures with quantum key distribution components](https://arxiv.org/abs/1403.5551): P1/P1′ protocol, symmetrization, and the reference bounds.
- [Gottesman and Chuang, Quantum Digital Signatures](https://arxiv.org/abs/quant-ph/0105032): foundational QDS model.
- [Nadeem and Wang, Quantum digital signature scheme](https://arxiv.org/abs/1507.03581): teleportation-based QDS research context.
- [IBM Quantum Learning, Quantum teleportation](https://quantum.cloud.ibm.com/learning/en/courses/basics-of-quantum-information/entanglement-in-action/quantum-teleportation): teleportation circuit and corrections.
- [Eagle-Eye QDS](https://pypi.org/project/eagle-eye-qds/): published feature comparison baseline; its implementation was not independently audited here.
