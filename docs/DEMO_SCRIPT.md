# Judge demo: about three minutes

Start the app with `./run.ps1` and open <http://127.0.0.1:8765>. The browser needs no external service.

1. **Open with the paradox.** Show the default *Hidden channel manipulation* experiment. Point to the pooled error near 2%, then the `00` Bell-outcome bar near 8%. The signature can remain **VALID** while the channel is **ANOMALY** and the operation is **QUARANTINED**. Explain that the alarm identifies a deviation, not the attacker.
2. **Show the evidence.** Open **Evidence**. Highlight the observed count, threshold, sample size and exact failed test. Download the JSON report if the judges want to rerun its arithmetic.
3. **Prove it is a signature workflow.** Select *Legitimate operation*. Bob's direct and Charlie's forwarded checks both read **VALID**. Run *Dishonest recipient forgery* and show Charlie's rejection. These are simulated outcomes, not a proof against all strategies.
4. **Show freshness.** Select *Legitimate operation* again and click *Execute simulated approval* twice. The first action executes; the second is blocked as a replay, while signature validity remains unchanged. The separate *Replay attempt* scenario demonstrates the same state directly.
5. **Show honest limits.** Open **Resource planner** and change the target from `10⁻³` to `10⁻⁹`. The reported Bell-pair requirement rises. Switch the delivery model to *Noisy / unproven*: the ideal security bound becomes unavailable.
6. **Close on measured evidence.** Open **Evaluation**. The pooled and full detector saw the same synthetic observations: 0 versus 19,967 flags in 20,000 targeted batches, with the same expected overall 2% error as ordinary noise. Mention the ordinary, sparse and indistinguishable controls.

The one-sentence pitch: **“Q-PRAMAAN makes quantum-signature security inspectable: it exposes manipulation hidden by average error rates, explains every decision, and shows which security claims are supported by their assumptions.”**

No model needs training. The decisions come from projective measurement probabilities, recipient verification rules, counters and finite-sample thresholds.
