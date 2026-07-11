# Engagement Recommendation engine — signal dependencies & degradation

How the **Sales-Pitch / Engagement Recommendation** engine (`engagement/recommend.py`,
`MODEL_VERSION = "engagement-v1"`) depends on each upstream signal source, and exactly how it
behaves when **Career, Decision Maker Intelligence (Apify), or Blog** feeds are unavailable.

The engine is a **pure rule** over already-fetched master-DB rows (`recommend_for_company`). Every
read is `None`/empty-safe, so **a missing source degrades the output — it never crashes or blocks the
pipeline.** It runs LAST in the orchestrator (`engagement` stage), so it simply consumes whatever the
upstream stages produced, including nothing.

---

## 1. The five inputs and which engine owns them

| Input (ORM) | Master table | Owning engine / source | Used for |
|---|---|---|---|
| `company` | `companies` | **Industry Discovery** | The iteration anchor; `technology_focus` (FPGA nudge + rationale), `prospect_type`, `company_tier` (rationale only) |
| `demand` | `demand_signals` | **Career Scraper** | **Picks the discipline → the offering**; per-discipline job counts; `primary_focus`; `hiring_trend`; `technologies_detected` |
| `opportunities` | `opportunities` | **Blog Crawler** | Contextual **trigger** framing (funding / product / expansion / partnership); confidence |
| `leadership` | `leadership_signals` | **derived from decision-maker snapshots** + **Blog/company-news** events | Engineering-leadership-hire trigger; confidence |
| `dm_count` / `dm_senior_count` | `decision_makers` | **Decision Maker Intelligence (Apify)** | Confidence; rationale |

> **Apify** is the Decision Maker Intelligence engine — it feeds `decision_makers` and therefore the
> snapshot-derived leadership signals. If Apify is down, that engine stops *refreshing* — its tables go
> **stale, not empty** — so the effect is delayed, not immediate (see §5).

---

## 2. Required vs optional signals

**No single source is individually required.** The only hard requirement is the "at least one signal"
gate (`recommend.py:140`):

```python
if not opportunities and demand is None and not leadership and not dm_count:
    return None      # a company with zero signals gets NO recommendation row
```

| Source | Required? | If absent |
|---|---|---|
| **Company** (Industry Discovery) | Always present | It's the anchor PK. Alone it is **not** a signal — a company with only `companies` data and nothing else returns `None`. |
| **Career** (`demand`) | Optional | Engine still runs, but loses discipline specificity (see §3) and up to **45 confidence points**. |
| **Blog** (`opportunities`) | Optional | Loses event triggers and up to **20 points**. |
| **Decision Maker Intelligence** (`leadership` + `dm_count`) | Optional | Loses the eng-leadership trigger and up to **15 points**. |
| **≥ 1 of {Career, Blog, Decision Maker Intelligence}** | **Required (as a set)** | If all three are absent for a company, no row is produced. |

Because `rebuild()` is **clear-and-insert** (`DELETE` all, then re-insert), if a company loses its last
signal on a later run, its stale recommendation is **dropped** on the next refresh rather than
lingering.

---

## 3. What each source uniquely controls

**Offering selection** (`key`, `recommend.py:218-223`) is driven almost entirely by **Career**:

```python
if top_disc:                                  # top_disc comes from demand_signals counts
    key = top_disc                            # verification / rtl / physical_design / dft / fpga / asic / embedded
elif funding or product or expansion or eng_hire:
    key = "staffing"                          # generic fallback (Blog/leadership events present)
else:
    key = "enablement"                        # thin-evidence fallback (always low confidence)
```

- **Career present** → a **discipline-specific** offering (e.g. "Physical design & timing-closure
  services").
- **Career absent** → the engine falls back to **"Engineering staff augmentation"** (if any
  Blog/leadership event exists) or **"Silicon design enablement"** (the provisional fallback).
- **One exception:** if `companies.technology_focus` contains "fpga", the FPGA discipline can be
  selected **without** Career (a +2 nudge, `recommend.py:152-153`). FPGA is the only discipline
  reachable this way.

**Trigger framing** (the "{trigger}" clause in the business-need sentence) is driven by **Blog**, then
**leadership signals**, then **Career**, highest-signal first (`recommend.py:186-202`):
funding round → product/tapeout → expansion → new engineering leadership → "amid a growing hiring
trend". With **no** Blog/leadership/Career trend signal, the need sentence has **no trailing context**.

---

## 4. Confidence math — per-source point budget

`_confidence()` (`recommend.py:120-133`), for any real discipline/staffing recommendation:

| Component | Points | Source |
|---|---|---|
| Base floor (any qualifying signal) | **+25** | — |
| `min(35, top_jobs × 6)` — per-discipline hiring depth | **up to +35** | **Career** |
| `hiring_trend == GROWING` | **+10** | **Career** |
| `min(20, len(opportunities) × 8)` — saturates at 3 events | **up to +20** | **Blog** |
| Engineering-leadership hire/promotion present | **+10** | **Decision Maker Intelligence** (leadership) |
| Any resolved decision maker | **+5** | **Decision Maker Intelligence** (decision_makers) |
| **Theoretical max** (capped at 100) | **105 → 100** | |

Label cutoffs: **≥ 70 high · ≥ 40 medium · else low**.
The `enablement` fallback uses a separate, capped formula — `15 + 10(if opps) + 5(if dm)`, **max 30** —
so a thin-evidence recommendation is **always "low."**

> **Industry Discovery contributes 0 confidence points.** `technology_focus` / `prospect_type` /
> `company_tier` shape the rationale (and the FPGA nudge), but never the score.

---

## 5. Behaviour when a whole source goes away

All four scenarios **degrade gracefully** — the stage still succeeds; output gets less specific and
less confident.

### Career unavailable (`demand_signals` empty)
- **Biggest impact.** Loses discipline specificity → offering collapses to **staffing**/**enablement**
  (except the FPGA-via-tech-focus exception).
- Loses up to **45** confidence points and the "growing hiring trend" trigger.
- Any company whose **only** signal was demand → **no recommendation**.
- Ceiling with Blog + Decision Maker Intelligence still present: `25 + 20 + 10 + 5 = 60` → **medium** at best.

### Decision Maker Intelligence unavailable (`decision_makers` empty → leadership Phase-1 ≈ 0, `dm_count = 0`)
- Loses the "under new engineering leadership" trigger, **−10**, and the DM **−5** (−15 total).
- Offering/discipline **unaffected** (that's Career's job).
- Companies whose only signal was DMs/leadership → no recommendation.
- Ceiling with Career + Blog: `25 + 45 + 20 = 90` → **high** still reachable.

### Blog unavailable (`opportunities` empty)
- Loses all event triggers (funding / product / expansion / partnership) → the need sentence loses its
  contextual tail; **−20** confidence; the funding/product/expansion → "staffing" promotion path is
  gone (an eng-leadership hire can still promote).
- Discipline still from Career.
- Ceiling with Career + Decision Maker Intelligence: `25 + 45 + 10 + 5 = 85` → **high** still reachable.

### Apify unavailable
- Apify is the **Decision Maker Intelligence** engine, so `decision_makers` (and the snapshot-derived
  leadership signals) **stop refreshing but keep their last-good rows** — the engine keeps producing
  recommendations from **stale** decision-maker data (no crash, no blank).
- Recommendations only thin out once the stale rows are actually cleared/expired; at that point the
  behaviour equals **Decision Maker Intelligence unavailable** (loss of the eng-leadership trigger and
  the DM confidence points).
- **Practical takeaway:** an Apify outage is a *freshness* problem first, a *coverage* problem only
  after the data is purged.

---

## 6. One-line summary

> The engine needs **≥ 1 of Career / Blog / Decision Maker Intelligence** to say anything. **Career decides _what_ to
> pitch** (the discipline → offering) and contributes the most confidence; **Blog and Decision Maker Intelligence decide
> _why now_** (trigger framing) and top up confidence; **Industry Discovery is the anchor and colours
> the rationale but is never sufficient on its own.** Remove any one source and the engine keeps
> running with a more generic, lower-confidence pitch; remove all signal sources for a company and it
> simply gets no recommendation.
