# Protocol and security model

## Participants and signed decision

Alice signs one bit: `1` approves a release already registered to a session; `0` rejects it. Bob receives the declaration and verifies it directly. Charlie verifies Bob's forwarded declaration. The session identifier, release, action, participant names and transcript sequence are bound to authenticated classical messages. SQLite stores an atomic execution receipt, so a valid old signature cannot execute the release twice.

This reference implementation adapts P1′ from [Wallden et al.](https://arxiv.org/pdf/1403.5551). It is a simulation of the published signature workflow delivered through Bell-pair teleportation. It is not a new proven QDS protocol.

## Teleportation and measurement

For a prepared qubit `|ψ⟩`, Alice and the receiver use `|Φ+⟩ = (|00⟩+|11⟩)/√2`. Alice applies CNOT and Hadamard, then measures her two qubits. For Bell outcome `(z,x)`, the receiver applies `X^x` followed by `Z^z`, yielding `|ψ⟩` up to global phase. Each outcome has probability 1/4 in the ideal circuit. `qpramaan.quantum.correctness()` checks six Pauli eigenstates across all four outcomes: 24 cases, minimum fidelity one to numerical precision.

The signature itself uses four BB84 states: `|0⟩`, `|1⟩`, `|+⟩`, and `|−⟩`. Bob and Charlie randomly measure in Z or X, recording the state their result excludes. After measuring, they secretly exchange a random half of their records, as P1′ requires. For a declaration `d` and recipient record `e`, a mismatch occurs when `d_i = e_i`. Direct acceptance requires fewer than `s_a L` mismatches; forwarded acceptance requires fewer than `s_v L`, with `s_a=0.02`, `s_v=0.04`, and `L` the original number of elements. The ideal run has zero mismatches; noisy acceptance is statistical.

The simulated signature requires `4L` Bell pairs, `8L` classical teleportation-correction bits and `4L` projective measurements for the two possible one-bit messages and two recipients. Diagnostic probes, authenticated classical messages and secret record exchange add resources and are reported separately. Work scales linearly in `L` for the implemented independent-signal simulator; coherent many-qubit attacks are outside its simulation scope.

## Channel monitor

Each diagnostic probe is a randomly prepared Pauli eigenstate, measured in its matching basis after teleportation. The monitor records revealed counts for Z, X and Y by Bell outcome. Preparation information is treated as unavailable to an attacker until the transmission completes; those revealed probes are not used as signature material. The targeted scenario uses independent Pauli-channel draws with 8% matched-basis error on outcome `00` and 0% on outcomes `01`, `10`, `11`, for both signature signals and diagnostic probes. The ordinary diagnostic channel has 2% in each branch. Thus both diagnostic conditions have expected pooled error 2%.

For a fixed batch of `n` independent bounded mismatch observations, the one-sided Hoeffding margin is

`m(n,α) = sqrt(log(1/α)/(2n))`.

The detector tests 20 scopes per link and phase: one pooled group, four Bell-outcome groups, three basis groups, and twelve basis-by-outcome groups. It allocates the family allowance `α=0.01` across tests by the union bound. It flags a scope when its observed error rate exceeds the declared baseline plus its margin. When a baseline comes from independent finite calibration, a separate upper-confidence margin is included. Missing calibration, too few observations or over 10% loss produces **insufficient evidence**, not a normal verdict. A detected deviation may arise from drift or an attack; the measurements alone do not distinguish intent.

The exact fixed-horizon allowance assumes independent observations, correct baseline and calibration model, and a fixed set of tests chosen before seeing results. It does not cover arbitrary adaptive attacks, detector side channels or unmodelled device behavior.

## Separate verdicts

| Verdict | Question answered |
|---|---|
| Signature validity | Does the declaration satisfy Bob's or Charlie's QDS rule? |
| Channel status | Are diagnostic measurements consistent with the declared operating model? |
| Request authorization | Is this participant permitted to act in this registered session, and is the execution fresh? |

An anomalous channel quarantines execution without silently changing the cryptographic validity result. A replay leaves the signature valid while the atomic receipt blocks a duplicate action. Unauthorized callers receive no private verification record in the service response. This access control applies to the service, not to information already disclosed to a legitimate recipient.

Classical transcript authentication is modeled with fresh Toeplitz universal-hash keys and a fresh 128-bit one-time pad for each tag. The key-consumption counter is included in the report. This assumes truly secret, uniform pre-shared keys and uncompromised endpoints; operating-system randomness in the simulator stands in for that resource. The private Bob–Charlie record exchange is modeled using a one-time pad and counted bits. The implementation is a research harness, not a deployment-ready key-management service.

## Reference bounds and their limits

For ideal authenticated delivery under the reference protocol, the planner uses [Wallden et al., Eq. (2) and Eq. (3)](https://arxiv.org/pdf/1403.5551):

`p_rep ≤ exp[-(s_v − s_a)^2 L / 2]`

`p_forge ≤ exp[-2(1/8 − s_v L/K)^2 K]`, with `K = L(1/2 − r)` and `r=0.05`.

A four-exchange union bound for the independent keep/send choices estimates setup abort as at most `8 exp(-2 r² L)`. The planner searches power-of-two `L` values between 256 and 1,048,576 and reports the least supported value within the Bell-pair budget. It displays **bound unavailable** for noisy, lossy or tampered delivery because the ideal-channel result cannot simply be reused there. The signature demonstration, statistical detector, and reference bounds have different assumptions and do not combine into a new unconditional security proof.

## Reproducible experiment

Run `python -m qpramaan.benchmark --trials 20000 --protocol-trials 200`. The committed benchmark JSON records the seed, NumPy version, scenarios, confidence intervals and timing scope. It generates identical observations for the pooled and full detectors within each trial. The targeted condition produced 19,967 full-detector flags and zero pooled-detector flags in 20,000 batches; ordinary produced zero with either detector. A sparse perturbation was not detected at this sample size, and a deliberately indistinguishable disturbance was not detectable from these observables. The 200 ideal protocol trials yielded 200 honest accepts and zero accepts for the particular simulated forger. Zero observed successes is not a universal bound.
