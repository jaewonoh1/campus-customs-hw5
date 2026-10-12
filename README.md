# Campus Customs — Multi-Agent Operations (Homework 5)

An agentic team that runs a small Yale apparel shop. Open tickets land on a board;
five AI agents triage and work them; a human watches and approves the money. Three
pieces:

- **MCP server** (`mcp_server/`) — a FastMCP server, the single tool surface over
  the shop database. Every agent reaches shop data only through it.
- **FastAPI backend** (`backend/`) — the agent team (boss, inventory, accounting,
  facilities, customer_service, built with PydanticAI) plus the HTTP API the
  dashboard calls. All agents use **gpt-6-luna** via the Portkey gateway.
- **React dashboard** (`frontend/`) — Vite + TypeScript "operations desk": pick a
  ticket, watch the agents work live, approve payments/purchases, see cash drop.

Full design notes: [`output/harness.md`](output/harness.md) (system),
[`output/design.md`](output/design.md) (dashboard).

## Layout

```
hw5/
├── AI_prompts.md          # prompt log
├── requirements.txt       # backend + MCP Python deps
├── .env.example           # copy to .env and fill in
├── .gitignore             # ignores .env, .venv, node_modules (NOT the DBs)
├── .mcp.json              # registers the campus-customs MCP server
├── README.md
├── data/                  # BOTH databases are committed:
│   ├── campus_customs.db       # original, pristine reference (never written)
│   └── campus_customs_new.db   # working copy (the system reads/writes this)
├── mcp_server/            # FastMCP server + its README
├── backend/               # FastAPI app, agents, prompts/
└── output/                # harness.md, design.md, deliverables, audit trail
```

## 1. Secrets (never committed)

The real `.env` is **not** in this repo. Copy the example and fill in your keys:

```bash
cp .env.example .env
```

Set `PORTKEY_API_KEY` (model access via the Portkey gateway). Only `gpt-6-luna` is
used for every agent.

## 2. Install

```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
npm install --prefix frontend
```

## 3. The two database files

Both are committed. `data/campus_customs.db` is the **original** (pristine) and is
never written. `data/campus_customs_new.db` is the **working copy** the system
reads and updates.

**Copy the original over the working copy whenever you want a clean run:**

```bash
cp data/campus_customs.db data/campus_customs_new.db
```

(The committed working copy is left in its post-run state — all three tickets
resolved, checking balance $160 — as evidence for `output/resolved_tickets.json`.
Copy the original over it, or use the Reset button / `POST /api/reset`, to start
fresh.)

## 4. Start the MCP server

The MCP server is launched automatically by anything that uses `.mcp.json` (the
agents start it over stdio). To run it directly:

```bash
./.venv/bin/python mcp_server/server.py
```

## 5. Start the FastAPI backend

From the `backend/` folder, on port 8000:

```bash
cd backend
uvicorn main:app --reload --port 8000
```

This serves the API at **http://localhost:8000** (the backend spawns the MCP
server itself when it runs the agent team). Run the team from the command line
instead with `./.venv/bin/python backend/team.py` (add `--ticket 101` for one).

## 6. Start the React board

From the `frontend/` folder:

```bash
npm run dev
```

Open the printed localhost URL (usually http://localhost:5173). The dashboard
talks to the backend at `http://localhost:8000`; the backend allows the dev-server
origin via CORS.

## 7. Reset the database before a full 3-ticket run

Before running all three tickets for a clean, reproducible run, reset the working
database to the original:

```bash
cp data/campus_customs.db data/campus_customs_new.db
```

or click **Reset shop** on the dashboard (or `curl -X POST
http://localhost:8000/api/reset`). Then run tickets 101, 102, and 103 from the
board and approve the prepared payments/purchases. A clean full run goes from a
$3,400 starting balance to $160 after the two approved payments (invoice #501
$840 and rent $2,400).

## Shop rules enforced

Human approval is required for every payment; agents only *prepare* them. The
`pay` tool refuses any payment that would overdraw the account (cash never goes
negative) and cash only goes out. Vendors won't ship while they have an open
unpaid invoice. "Today" is `desk.date_today`. No real emails or vendor calls —
customer messages are drafts only. See `output/harness.md` for the full safety
section.
