# Dashboard design — Campus Customs Operations Desk

The dashboard (`frontend/`, React + Vite + TypeScript) is built to feel like a
real **operations desk**: a person sits down, sees the work waiting, sends the
team at a ticket, watches them think out loud, and signs off on the money. Every
choice below serves that "desk you'd want to sit at" goal.

## Layout — three columns, one glance

A fixed **top bar** carries the brand, the shop's identity ("agent team on duty"),
and the two things a manager always wants in view: the **checking balance** and a
**Reset shop** button. Below it, a **three-column grid**:

- **Left — Ticket board.** The three tickets as cards: type icon, id, status
  badge, subject, requester. Click one to select it; the selected card expands a
  **Run agent team** button. This is the "inbox" you triage from.
- **Center — Agent activity.** The widest column, because watching the team work
  is the point. Empty-state invites you to pick a ticket; during a run it fills
  with a live feed; after a run it adds a summary.
- **Right — Approvals.** Where money decisions land. Prepared payments and POs
  appear as cards with an **Approve** button; nothing moves until a human clicks.

Why three columns: triage → watch → approve reads left-to-right, matching the
real workflow. On narrow screens it collapses to a single scrollable column.

## How the agents read differently

Each agent has a consistent **identity**: a colored avatar (initial), a name, and
a one-line role. The five colors are distinct but muted so five of them on screen
never feel loud:

- **Boss** — indigo (routes, final call)
- **Inventory** — green (stock, vendors)
- **Accounting** — Yale blue (cash, margins)
- **Facilities** — amber (lease, rent)
- **Customer Service** — rose (customer drafts)

In the **live feed**, each step is a chat-style bubble tinted and left-bordered in
that agent's color, so you can tell *who is speaking* at a glance without reading.
Delegations **indent** the child step, so the boss → specialist → sub-specialist
structure is visible as a shape. Under each message, small **chips** show the MCP
tools the agent called (`🔧 check_stock`) and who it handed off to
(`→ Accounting`) — the "what they did," not just "what they said." The agents'
light markdown (`**bold**`) is rendered as real emphasis so messages read cleanly.

A run feels **live** because the feed polls the backend's event endpoint every
~1.2s while the run is in flight, so agents appear one by one with a pulsing
"working…" row — not a frozen spinner then a dump.

## Tickets, resolved tickets, and cash

- **Status badges** are color-coded and plain-language: *Open* (grey), *Running…*
  (blue, pulsing), *Awaiting approval* (amber), *Blocked* (red), *Resolved*
  (green). When a run finishes, the ticket flips from *Open* to its real backend
  status — for these tickets that is **Awaiting approval**, which is the honest
  state: the agents have done everything they can, and a human still has to
  approve the money. (We deliberately don't fake a "Resolved" badge over work
  that still needs a signature; a ticket reads as truly handled once its approvals
  are cleared.)
- The **run summary** appears under the feed when the run ends: the boss's final
  decision in a highlighted card, then one small card per agent with its last word
  and the tools it used — a quick "who did what" without re-reading the feed.
- **Cash** lives in the top bar so it's always visible. After an approved payment
  it refreshes and briefly **flashes green and scales up**, so you *see* the money
  leave (e.g. $3,400 → $2,560 after approving an $840 invoice). The sub-label
  "cash only goes out" reinforces the shop rule.

## Human-in-the-loop, made obvious

The Approvals column states the rule in plain words: "Agents only *prepare* money.
Nothing is paid until you approve it." You set **who you are** ("Approving as") —
approval requires a human name, so an empty approver disables the buttons. A
payment card shows the amount and whether it *fits balance*; a purchase card shows
the SKU, qty, ETA, and — crucially — if it's **blocked by an unpaid invoice**, the
reason is shown in red and the **Approve button is disabled**. The guardrail isn't
just backend logic; you can see why you *can't* click.

## Color scheme and typography

A calm, professional palette: a soft blue-grey background, white cards with a
gentle shadow, and **Yale blue** (`#00356b`) as the single brand anchor (top bar,
titles, primary actions). Accents are used sparingly — green only for "approve"
and positive cash, amber/red only for attention states — so the eye goes to what
matters. Headings use **Fraunces** (a warm serif) for a bit of character; body is
**Inter** for clean legibility. Nothing blinks or saturates; the only motion is
the subtle live-feed pulse and the cash flash, both tied to real events.

## What makes it enjoyable to use

- **You watch the team think.** The live, color-coded feed turns an opaque agent
  run into something you can follow and trust — the single most satisfying part.
- **One obvious action at each step:** pick a ticket → run → approve. No menus to
  hunt through.
- **Honest, legible state** everywhere: real statuses, visible guardrails, a cash
  number that reacts. You always know what happened and what's still yours to do.
- **Reset shop** lets you re-run the whole scenario cleanly, so it's fun to poke
  at — try a ticket, approve, reset, try another.

## Talking to the backend

The dashboard calls the FastAPI backend at `http://localhost:8000` directly; the
backend allows the Vite dev-server origin (localhost, any port) via CORS. Start
the backend (`uvicorn main:app --reload --port 8000` from `backend/`) and the
dashboard (`npm run dev` from `frontend/`), then open the printed localhost URL.
