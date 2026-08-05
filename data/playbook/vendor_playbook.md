# Vendor Contract Playbook (Buyer-Side)

This playbook states **our company's** preferred position, as the buyer/
customer, for each of the 7 clause types this project reviews in vendor
contracts. Positions are adapted from public SaaS-contract playbook
guidance — [Common Paper's contract playbook template](https://commonpaper.com/blog/contract-playbook-template/)
(vendor-side; inverted here to the buyer's perspective) and
[Contract Nerds' "Great 8" SaaS playbook webinar](https://contractnerds.com/how-to-build-and-use-a-saas-agreement-playbook-8-common-issues-and-fallback-positions/)
(customer-side positions used directly where available). This is not legal
advice — positions are self-adapted from these sources, not lawyer-reviewed.

Each clause has three positions:
- **Default** — what we ask for first.
- **Fallback** — what we'll accept if the default is rejected.
- **Escalate** — conditions under which this clause needs human/legal
  review rather than an automatic pass/fail.

---

## Renewal Term

- **Default:** No automatic renewal — the agreement ends at the stated
  term unless we affirmatively renew it.
- **Fallback:** Automatic renewal is acceptable if: the renewal term is
  capped at 12 months, the vendor must send a renewal notice at least 60
  days before the renewal date, and we can decline renewal with at least
  30 days' notice before it takes effect.
- **Escalate:** Auto-renewal with no vendor notice requirement, a notice/
  opt-out window under 30 days, a renewal term longer than 12 months, or
  auto-renewal bundled with an automatic price increase we haven't
  pre-approved.

**Rationale:** Unintentional auto-renewals are a well-documented source of
disputed vendor charges; the fallback exists to guarantee we always have a
real, time-bounded opportunity to walk away before being re-committed.

---

## Termination For Convenience

- **Default:** We may terminate the agreement for convenience with 30–60
  days' written notice, with a pro-rated refund of prepaid, unused fees.
- **Fallback:** If the vendor won't grant convenience termination, we
  require termination for cause — material breach, repeated SLA failure,
  security incident, or insolvency — with a 30-day cure period before we
  must terminate rather than being locked in indefinitely.
- **Escalate:** The agreement grants the vendor termination-for-convenience
  rights but not us (one-sided), or imposes an early-termination penalty
  on us that approaches the full remaining contract value.

**Rationale:** Termination rights are about exit optionality — the risk we're
managing is being contractually stuck with an underperforming vendor with
no realistic way out.

---

## Cap On Liability

- **Default:** A mutual liability cap set at not less than the fees paid
  in the preceding 12 months, applied symmetrically to both parties.
- **Fallback:** A lower cap (e.g., fees paid in the preceding 6 months) is
  acceptable only if the carve-outs in "Uncapped Liability" below are
  broad enough to cover our key risk categories (data breach, confidentiality,
  IP indemnification).
- **Escalate:** A cap below 6 months of fees, a cap that applies only to
  our liability and not the vendor's (asymmetric), or a cap denominated
  in a way that's effectively nominal (e.g., "fees paid in the month the
  claim arose").

**Rationale:** The cap is the ceiling on what we can recover if the vendor
causes real damage — it needs to be large enough relative to the deal
that it's a meaningful backstop, not a token number.

---

## Uncapped Liability

- **Default:** The following are carved out of the liability cap entirely
  (uncapped): confidentiality/data breach, IP infringement indemnification,
  gross negligence or willful misconduct, and violations of applicable law.
- **Fallback:** If the vendor won't agree to fully uncapped carve-outs,
  accept a secondary, higher cap (2–3x annual fees) applied specifically
  to those categories rather than the standard cap.
- **Escalate:** The vendor's proposed carve-outs exclude data breach or IP
  indemnification from uncapped treatment, or there are no carve-outs at
  all — meaning even a data breach would be capped at the standard,
  low liability limit.

**Rationale:** These are the categories where a low, standard cap could
leave us dangerously under-protected relative to plausible real-world
damages — the whole point of this clause is making sure the cap above
doesn't silently apply to our worst-case risks.

---

## Minimum Commitment

- **Default:** No minimum spend, volume, or purchase commitment —
  pay-as-you-go / usage-based.
- **Fallback:** If a minimum is required, it must (a) be set at or below
  our realistic forecasted usage, (b) include an annual true-up/
  right-sizing mechanism rather than being fixed for the full contract
  term, and (c) not increase year-over-year by more than 10–20% without
  our separate agreement.
- **Escalate:** A multi-year minimum commitment with no adjustment
  mechanism, a minimum that exceeds our realistic usage forecast, or
  automatic minimum increases tied to the vendor's list price rather than
  our negotiated rate.

**Rationale:** Minimum commitments shift volume risk onto us; the fallback
conditions exist so we're never locked into paying for capacity we don't
end up using.

---

## Audit Rights

- **Default:** We may audit the vendor's security/compliance controls
  directly, or the vendor's current SOC 2 Type II report (or equivalent)
  satisfies this requirement in lieu of an on-site audit.
- **Fallback:** One audit per year, at our expense, with 30 days' notice;
  if the vendor uses subprocessors, we require 30-day advance notice of
  new subprocessors with the right to object/terminate.
- **Escalate:** The vendor refuses any audit right or certification
  evidence, restricts audits to a vendor-selected auditor only, or blocks
  audit access following a security incident.

**Rationale:** Without some form of audit right, our compliance posture is
entirely dependent on the vendor's word — this clause is what makes that
verifiable rather than assumed.

---

## Governing Law

- **Default:** Our home jurisdiction's law and courts govern the agreement.
- **Fallback:** A neutral, well-established U.S. commercial-law
  jurisdiction (e.g., Delaware or New York) is acceptable, as long as the
  governing law and the litigation/arbitration venue match each other
  (no split jurisdiction/venue).
- **Escalate:** Non-U.S. governing law or courts, mandatory arbitration in
  an inconvenient or vendor-favorable venue, or a mismatch between the
  stated governing law and the stated venue.

**Rationale:** This clause determines where and under what legal system we'd
have to fight if something goes wrong — the escalation trigger is about
avoiding forums that make enforcement impractically expensive for us.
