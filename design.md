\# ORBITAL — Design Spec

Quantum cryptography simulator. Visual language: electron probability densities rendered as heat-glow on black.



\---



\## 1. Concept



Source image: hydrogen orbitals (s/p/d × n=1..3), `|ψ|²` as additive ember glow on pure black, thin black \*\*nodal lines\*\* cutting the glow, white lowercase column labels, right-aligned shell numerals.



Core metaphor: \*\*probability density = the product.\*\* Every protocol (BB84, E91, lattice KEMs, Shor/Grover attacks) is shown as a density field you can sample, measure, and collapse. The UI itself is an orbital chart.



| Image element | Meaning in product |

|---|---|

| Black void | Unobserved Hilbert space |

| Glow intensity | Probability amplitude² |

| Nodal line (dark cut) | Measurement basis boundary / zero-probability plane |

| Column s / p / d | Protocol family (see §4) |

| Row n = 1,2,3 | Complexity tier (qubits / depth) |

| Empty cell (d @ n=1,2) | Locked / not-yet-physical (d needs n≥3) |



\---



\## 2. Color



Single heat ramp, luminance-monotonic (readable in grayscale / CVD).



```css

:root {

&#x20; --void:    #000000;

&#x20; --ember-0: #0B0000;  /\* panel bg \*/

&#x20; --ember-1: #2A0500;

&#x20; --ember-2: #5C0A00;

&#x20; --ember-3: #A31A00;

&#x20; --ember-4: #E04A00;

&#x20; --ember-5: #FF8A1F;

&#x20; --ember-6: #FFC24D;

&#x20; --ember-7: #FFF1C2;  /\* core / peak density \*/



&#x20; --text:    #FFE9D2;

&#x20; --text-dim:#9A6B55;

&#x20; --line:    #2A0F08;  /\* 1px borders \*/



&#x20; --eve:     #3FE0FF;  /\* ONLY color outside the ramp: eavesdropper / tamper / error \*/

&#x20; --ok:      #FFF1C2;  /\* success = brightest ember, not green \*/

}

```



Rules:

\- No gradients except the density ramp. No blue/purple/green UI chrome.

\- `--eve` cyan is reserved for intrusion, QBER spikes, failed verification. Used < 2% of pixels. Its rarity is the signal.

\- Backgrounds are black; elevation = glow, not shadow.



\---



\## 3. Typography



| Role | Font | Notes |

|---|---|---|

| Labels / data / code | JetBrains Mono | lowercase `s p d`, numerals, all telemetry |

| Display / headings | Space Grotesk 500 | tight tracking −0.02em |

| Body | Inter Tight 400 | 15/22, max 68ch |



\- Shell numerals (1,2,3) and orbital letters: bold, white-ish `--text`, 12px mono, right/top aligned exactly as in source.

\- Math: KaTeX, `--text` on black, ket notation `|ψ⟩` in `--ember-6`.



\---



\## 4. Information Architecture — The Orbital Grid



Home nav \*\*is\*\* the image: a 3×3 grid of live density tiles.



```

&#x20;       s                 p                 d

&#x20;  ┌─────────────┬─────────────────┬─────────────────┐

&#x20;1 │ BB84        │ —  (locked)     │ —  (locked)     │

&#x20;  ├─────────────┼─────────────────┼─────────────────┤

&#x20;2 │ B92 / SARG  │ E91 (entangled) │ —  (locked)     │

&#x20;  ├─────────────┼─────────────────┼─────────────────┤

&#x20;3 │ Decoy-state │ MDI-QKD         │ Lattice / PQC   │

&#x20;  └─────────────┴─────────────────┴─────────────────┘

```

\- \*\*s\*\* = prepare-and-measure QKD (spherical, symmetric)

\- \*\*p\*\* = entanglement-based (two lobes, a nodal plane between)

\- \*\*d\*\* = threat / post-quantum (four lobes: Shor, Grover, lattice)

\- Row = tier. Locked cells render pure black with a 1px `--line` frame and no label until hover (`requires tier n≥3`).

\- Each tile renders the \*actual\* density of its orbital via shader; the tile's shape previews the protocol's state geometry.



Routes: `/` grid · `/lab/:protocol` simulator · `/learn` · `/attack` (Shor/Grover) · `/bench` · `/docs`.



\---



\## 5. Layout \& Grid



\- 12-col, 1200 max, 24px gutter, 8px base unit. Page margin 32 (desktop) / 16 (mobile).

\- Tiles are \*\*square\*\*, 1px `--line` border, no radius (`0`), no shadow. Source image is hard-edged; keep it.

\- Header: 56px, wordmark left (`ORBITAL` mono, letterspaced 0.3em), nav right as lowercase `lab learn attack bench docs`.

\- Footer: single mono line, build hash + WebGPU status.



Lab layout (desktop):



```

┌──────────────────────────────┬───────────────┐

│                              │ PARAMS        │

│   FIELD CANVAS  (square)     │ n  l  m       │

│   density + sampled photons  │ basis  noise  │

│                              ├───────────────┤

│                              │ EVE  \[off|on] │

├──────────────────────────────┴───────────────┤

│ ALICE bits  1 0 1 1 0 …                      │

│ BASIS       + × + + ×                        │

│ BOB  bits   1 0 0 1 0 …   QBER 0.8%  KEY 412b│

└──────────────────────────────────────────────┘

```



\---



\## 6. Core Visual Techniques



\### 6.1 Density shader (hero + tiles)

Fragment shader evaluates hydrogenic `|ψ\_nlm|²` on a 2D slice, tone-maps through the ember ramp.



```glsl

// WGSL/GLSL-equivalent logic

float density(vec2 p, int n, int l) {

&#x20; float r = length(p), c = p.y / max(r, 1e-4);          // cosθ

&#x20; if (n==1)           return exp(-2.0\*r);                // 1s

&#x20; if (n==2 \&\& l==1)   return r\*r\*c\*c\*exp(-r);            // 2p\_z

&#x20; if (n==3 \&\& l==2)   { float a=3.0\*c\*c-1.0; return r\*r\*r\*r\*a\*a\*exp(-2.0\*r/3.0); } // 3d\_z²

&#x20; return 0.0;

}

vec3 heat(float t) {            // t in \[0,1], log-ish compress

&#x20; t = pow(clamp(t,0.,1.), 0.45);

&#x20; return mix(mix(mix(C0,C2,smoothstep(0.,.3,t)), C4,smoothstep(.3,.6,t)),

&#x20;            mix(C5,C7,smoothstep(.6,1.,t)), smoothstep(.55,1.,t));

}

```

\- Normalize per-orbital to peak; apply `log1p` gain so outer shells stay visible (matches the faint halos in source).

\- Radial nodes (rings in 2s/3s/3p) emerge naturally — keep them; they're the signature.

\- Add 1-bit blue-noise dither to kill banding on pure black.

\- Bloom: 2-pass Kawase, threshold at `--ember-5`, strength 0.35. Core must stay hot-white (`--ember-7`).



\### 6.2 Sampling = measurement

Click/hold on a canvas = measure. Draw N points from `|ψ|²` (rejection or inverse-CDF on the radial part), each a 2px `--ember-7` dot with 300ms fade-to-`--ember-4` trail. After enough points the density re-emerges (Born rule, visibly). Point position → bit via quadrant parity; this \*is\* the key generation.



\### 6.3 Collapse

On measurement of a single photon: field cross-fades (120ms) to a tight Gaussian at the hit point, then relaxes back over 1.2s. Nodal lines flash `--ember-7` for one frame.



\### 6.4 Eavesdropper

Eve toggled on → a \*\*cyan\*\* thin line appears along the channel, field gets visible interference noise (speckle at 4–8% amplitude), QBER readout counts up; at >11% the key panel border turns `--eve` and the key is struck through.



\### 6.5 Nodal lines as UI

The thin black cut through glows is reused as: dividers inside glowing panels, progress bars (black line sweeping across a lit field), and focus rings (black 2px inner line on glow).



\---



\## 7. Components



\- \*\*Orbital tile\*\* — square canvas + `s|p|d` and `n` labels in corners (label position identical to source). Hover: gain +20%, slow rotation of slice (θ drifts ±8°/s).

\- \*\*Param slider\*\* — 1px line, 8px square thumb in `--ember-6`; track left of thumb glows.

\- \*\*Toggle\*\* — rectangular, no radius; on = `--ember-5` fill, off = outline.

\- \*\*Bit strip\*\* — mono cells 20×28; 1 = `--ember-6` bg, 0 = `--ember-1`; mismatched basis cells dimmed to 30%.

\- \*\*Readout\*\* — label (dim, 10px caps) over value (mono 28px). QBER, key length, fidelity, entropy.

\- \*\*Button\*\* — primary: `--ember-5` bg, black text, 0 radius, 40px h. Secondary: 1px `--ember-3` outline.

\- \*\*Code block\*\* — `--ember-0` bg, `--line` border, syntax: keywords `--ember-5`, strings `--ember-6`, comments `--text-dim`.

\- \*\*Tooltip\*\* — black, 1px `--ember-3`, mono 11px.



\---



\## 8. Motion



\- Ambient: all fields idle-breathe (gain ±4%, 6s sine). Never static.

\- Page transition: current field \*collapses\* to a point at cursor, next page expands from it (300ms, `cubic-bezier(.2,.8,.2,1)`).

\- Numbers tick with mono-width stability (tabular-nums).

\- `prefers-reduced-motion`: disable breathing, drift, and transitions; keep sampling (user-initiated).



\---



\## 9. Hero



Full-viewport single 3d\_z² field, slowly rotating, with `ORBITAL` set bottom-left and one line:



> \*\*Observe a key into existence.\*\*



Below the fold: the 3×3 orbital grid. Scrolling zooms from the hero field down into the grid tile (shared-element transition).



\---



\## 10. Voice



Terse, lowercase labels, no marketing filler. Copy examples: `measure`, `collapse`, `eve: off`, `qber 0.8%`, `key 412 bits`. Errors in `--eve`, never red (red is the brand).



\---



\## 11. Tech / Performance



\- Render: WebGPU primary (compute for sampling, fragment for density); WebGL2 fallback; static pre-rendered PNG tile if neither.

\- Tile canvases 256², lab canvas 768², DPR-capped at 2. Pause offscreen tiles via IntersectionObserver.

\- Budget: 60fps on integrated GPU; tiles share one device, one pipeline, uniform-driven `(n,l,m,gain,t)`.

\- Sim core (BB84/E91/lattice) in Rust → WASM; deterministic seeds exposed in URL (`?seed=`) for reproducible demos.



\---



\## 12. Accessibility



\- Text contrast ≥ 7:1 (`--text` on black ≈ 17:1).

\- All field meaning duplicated in text readouts; canvas has `aria-label` describing state ("2p, 4.1k samples, QBER 0.8%").

\- Information never color-only: Eve state also changes icon + label + border style.

\- Full keyboard: arrows adjust `n,l,m`; `space` = measure; `e` = toggle eve.



\---



\## 13. Don'ts



\- No rounded corners, drop shadows, glassmorphism, purple gradients, or stock "quantum atom" clipart.

\- No blue UI. Cyan is Eve only.

\- No decorative particles — every dot is a sample from a real distribution.

