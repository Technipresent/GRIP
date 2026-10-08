# GRIP Grounding Engine — Specification v2.0
Status: LOCKED by Founder · Session-287 · 2026-10-08
Supersedes for the engine: GRIP-SPEC-v1.0.md (audit engine). Build order: GRIP-BUILD-PLAN-2026-10-08.md. Diagram: D:\Technipresent\SYNC\SYNC-GRIP-Sequence-Diagram-2026-10-08.html

## 1. Purpose
GRIP decides, for one claim at a time, whether public evidence supports it, contradicts it, or does not settle it — and proves its answer with exact quotes and links. GRIP grounds only. It never writes text.

## 2. Position
SYNC sits between an upstream application and a model crew (SYNC-supplied, or the customer's own). GRIP is called by SYNC and behaves identically whichever model crew is in use. GRIP never calls, and never depends on, the model that produced the claim.

## 3. Locked decisions
1. No generative model decides any verdict.
2. Meaning check uses two self-hosted, non-generative checkers in parallel: HHEM-2.1-Open (Vectara, Apache 2.0) and MiniCheck-FlanT5 (licence to be confirmed). Both must agree; disagreement is uncertainty.
3. Two hired, replaceable search providers behind one fixed connector: Brave (keyword) and Exa (meaning). Searched in parallel; evidence merged.
4. Unsure never guesses: anything uncertain returns Disputed.
5. Search once per claim set, not once per checker; repeat searches within a request are reused.
6. Same input gives the same verdict, every time.
7. GRIP is its own service, in its own repository.

## 4. Contracts (frozen before build, versioned)
### 4.1 Request (SYNC to GRIP)
Batch of claims. Each claim: identifier, claim text, subject, surrounding context, stakes (normal or high).

### 4.2 Response (GRIP to SYNC)
Per claim: verdict (Supported, Contradicted, Disputed, No evidence it exists); exact quotes, each with link and provider that found it; deciding rule; both checkers' scores; confidence.

### 4.3 Provider connector
Query in; links, snippets, page text out. Every provider implements this one interface.

### 4.4 Checker connector
Claim plus evidence passage in; supported probability out. Every checker implements this one interface.

## 5. Components
1. Request intake — validates, plans searches: the claim; "was there an earlier case?"; "are there alternatives?". Routing: exact names, numbers, dates, existence to Brave; meaning and paraphrase to Exa; the main claim to both.
2. Search and read — parallel search, full-page reading, right-subject check, exact-sentence quoting, one source one vote, forums and summaries excluded. Evidence from both providers merged and de-duplicated.
3. Meaning check — sends each claim-and-evidence pair to both checkers in parallel. Both above the support threshold: supported. Both below the contradiction threshold: contradicted. Anything else: uncertain.
4. Rules engine — deterministic: authority tiers, weighing, scope words ("first", "only", "the standard"), unit equivalence, numbers and dates recomputed, zero results anywhere means "no evidence it exists", the too-close zone always returns Disputed. Exact facts are decided here by rule, never by checker.
5. Result sender — assembles the frozen response; every verdict carries its deciding rule.

## 6. Thresholds
Starting thresholds set per checker from SYNC's test set, then frozen per release. Changed only by a new release that passes the proof gates.

## 7. Proof gates (build fails if any fails)
1. Every component has tests written before code.
2. Known-answer bank: GRIP seeded entities plus SYNC gold set — all expected verdicts met.
3. Five identical runs of the same claims give identical verdicts.
4. Published benchmarks (FEVER, SciFact, VitaminC) run and reported.
5. No generative model call anywhere in the verdict path (enforced by test).
6. A provider or checker outage returns Disputed, never a wrong verdict.

## 8. Not in scope
Writing corrections, claim splitting, the screen, the dossier, billing — all stay in SYNC. Fine-tuning the checkers comes after v2.0 ships.

## 9. Before build (Founder)
- Lock this specification.
- GRIP's own repository created on GitHub.
- Exa account and key.
- Railway service for the two checkers.
- Licence clearance: HHEM-2.1-Open training data; MiniCheck-FlanT5 licence and training data.
- Open decision: do the model providers' web searches join GRIP's substrate, or leave grounding?
