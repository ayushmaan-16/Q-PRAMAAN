import json
import secrets
import time
import uuid
from datetime import datetime, timezone
import numpy as np
from . import __version__
from .attacks import SCENARIOS, probe_batch
from .auth import OneTimeAuthenticator, canonical
from .detection import analyze
from .protocol import distribute, verify, bob_forge
from .trace import sample_experiment_traces



def operation_decision(signature, channel, authorization):
    if authorization != "AUTHORIZED":
        return "BLOCKED"
    if signature != "VALID":
        return "BLOCKED"
    if channel != "CONSISTENT":
        return "QUARANTINED"
    return "EXECUTABLE"


def run_experiment(config, store):
    start = time.perf_counter()
    scenario = config.get("scenario", "targeted")
    if scenario not in SCENARIOS:
        raise ValueError("Unknown scenario.")
    seed = int(config.get("seed", 26141))
    length = int(config.get("length", 4096))
    n = int(config.get("per_branch", 4096))
    baseline = float(config.get("baseline", .02))
    if not 0 <= seed < 2 ** 63 or not 1024 <= length <= 65536 or not 32 <= n <= 32768 or not 0 <= baseline <= .10:
        raise ValueError("Use L 1024–65536, probes 32–32768/group, baseline 0–10%, and a nonnegative 63-bit seed.")
    report_id = uuid.uuid4().hex
    context = {"session": report_id, "release": "grid-controller / v2.4.1", "action": "release-approval",
               "signer": "Alice", "verifiers": ["Bob", "Charlie"], "protocol": "P1-prime-teleportation-v1"}
    auth = OneTimeAuthenticator()
    confidential_bits = 0
    sequence = 0

    def transport(message, secret=False):
        nonlocal confidential_bits, sequence
        sequence += 1
        bound = {**message, "session": report_id, "sequence": sequence}
        if secret:
            plain = canonical(bound)
            pad = secrets.token_bytes(len(plain))
            cipher = bytes(a ^ b for a, b in zip(plain, pad))
            recovered = bytes(a ^ b for a, b in zip(cipher, pad))
            if recovered != plain:
                raise RuntimeError("Private exchange failed.")
            confidential_bits += len(plain) * 8
        envelope = auth.issue(bound)
        if not auth.verify(bound, envelope):
            raise RuntimeError("Classical transcript authentication failed.")

    transport({"sender": "Alice", "recipient": "Bob", "phase": "registration", "context": context})
    transport({"sender": "Alice", "recipient": "Charlie", "phase": "registration", "context": context})
    # Private RNG intentionally independent of public diagnostic seed.
    rng = np.random.default_rng(secrets.randbits(128))
    delivery_rates = None
    if scenario == "targeted":
        delivery_rates = [min(4 * baseline, 2 / 3), 0., 0., 0.]
    elif scenario == "noise":
        delivery_rates = [max(.08, baseline)] * 4
    elif scenario == "sparse":
        delivery_rates = [.9 * baseline + .1 * min(4 * baseline, 2 / 3), baseline, baseline, baseline]
    material = distribute(length, rng, repudiation=scenario == "repudiation",
                          transport=transport, q_by_branch=delivery_rates)
    honest_decl = material["private"][1].copy()
    transport({"sender": "Alice", "recipient": "Bob", "phase": "signing", "bit": 1,
               "declaration": honest_decl.tolist()})
    bob = verify(honest_decl, 1, material["records"]["Bob"], length, .02)
    bit, declaration = 1, honest_decl
    if scenario == "forgery":
        bit = 0
        declaration = bob_forge(material["own"]["Bob"], material["records"]["Bob"][0][1], 0, rng)
    transport({"sender": "Bob", "recipient": "Charlie", "phase": "forward", "bit": bit,
               "declaration": declaration.tolist()})
    charlie = verify(declaration, bit, material["records"]["Charlie"], length, .04)
    signature = charlie["status"]
    if not material["setup_ok"]:
        signature = "NOT_EVALUATED"
    authorization = "AUTHORIZED"
    auth_reason = "Authenticated participant; registered release and session match."
    actor = "Bob"
    if scenario == "impersonation":
        passed = auth.verify({"sender": "Alice", "session": report_id}, {"key_id": "outside-key", "tag": "0" * 32})
        authorization = "AUTHORIZED" if passed else "IDENTITY_REJECTED"
        auth_reason = "The outsider has no valid one-time authentication key."
        actor, signature = "Eve", "NOT_EVALUATED"
        bob = charlie = {"status": "NOT_EVALUATED", "reason": "Verification material was not disclosed to this caller."}
    elif scenario == "unauthorized":
        authorization, actor, signature = "VERIFIER_DENIED", "Eve", "NOT_EVALUATED"
        auth_reason = "Eve is not a registered verifier; no verification evidence is returned."
        bob = charlie = {"status": "NOT_EVALUATED", "reason": "Access denied before verification."}
    observations = probe_batch(scenario, seed, n, baseline)
    channel = analyze(observations, baseline=baseline, calibrated=scenario != "uncalibrated")
    comparison = analyze(probe_batch("legitimate", seed, n, baseline), baseline=baseline)
    if scenario == "replay" and signature == "VALID" and channel["status"] == "CONSISTENT":
        store.execute_once(report_id, json.dumps(context, sort_keys=True))
        authorization = "REPLAY_BLOCKED"
        auth_reason = "This session already executed. Signature validity is preserved; execution is denied."
    operation = operation_decision(signature, channel["status"], authorization)
    report = {"id": report_id, "version": __version__, "created_at": datetime.now(timezone.utc).isoformat(),
              "scenario": scenario, "title": SCENARIOS[scenario][0], "description": SCENARIOS[scenario][1],
              "context": context, "actor": actor, "requested_bit": bit,
              "decisions": {"signature": signature, "channel": channel["status"],
                            "authorization": authorization, "operation": operation},
              "authorization_reason": auth_reason, "bob": bob, "charlie": charlie,
              "setup": {"completed": material["setup_ok"], "exchange_counts": material["exchange_counts"],
                        "bell_outcome_counts": material["bell_counts"]},
              "traces": sample_experiment_traces(scenario, seed, 24, baseline),
              "channel_analysis": channel, "baseline_analysis": comparison, "observations": observations,
              "authentication": {**auth.summary(), "private_exchange_otp_bits": confidential_bits},
              "resources": {"signature_elements_per_message": length, "bell_pairs_signature": 4 * length,
                            "teleportation_bits_signature": 8 * length, "diagnostic_probes": 4 * n,
                            "scope": "One-bit reference; probes and auth keys additional; balanced diagnostic strata."},
              "config": {"scenario": scenario, "seed": seed, "length": length, "per_branch": n,
                         "baseline": baseline, "signature_channel_rates_by_bell_outcome": delivery_rates},
              "reproducibility": {"public_seed_scope": "Diagnostic probes only. Never derives signing or authentication secrets.",
                                  "recompute": "python -m qpramaan.evidence path-to-report.json",
                                  "report_scope": "Recomputable statistical evidence, not a cryptographic attestation of log truth."},
              "limits": ["Software simulation; no physical quantum-security claim.",
                         "Signature signals and diagnostic probes use independent draws from the scenario's declared Pauli-channel rates; diagnostics are separate, revealed samples.",
                         "An anomaly identifies a model deviation, not attacker identity or intent.",
                         "P1-prime is adapted with teleportation; noisy/external attack proofs are not inherited.",
                         "Coherent multi-signal quantum attacks are not simulated; a single attack trial is not an estimated success rate."],
              "elapsed_ms": round((time.perf_counter() - start) * 1000, 2)}
    store.save(report)
    return report


def execute_report(report_id, store):
    report = store.get(report_id)
    if report is None:
        raise KeyError("Experiment not found.")
    if report["decisions"]["operation"] not in ("EXECUTABLE", "EXECUTED"):
        return {"status": "BLOCKED", "reason": "The experiment does not authorize execution.", "report": report}
    ok = store.execute_once(report_id, json.dumps(report["context"], sort_keys=True))
    if ok:
        report["decisions"]["operation"] = "EXECUTED"
        report["authorization_reason"] = "Simulated release approval executed exactly once."
    else:
        report["decisions"]["authorization"] = "REPLAY_BLOCKED"
        report["decisions"]["operation"] = "BLOCKED"
        report["authorization_reason"] = "Atomic replay guard rejected duplicate execution."
    store.save(report)
    return {"status": "EXECUTED" if ok else "REPLAY_BLOCKED", "report": report}
