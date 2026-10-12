# AI Prompt Log

## Setup

Prompt 1:

> work in homework 5 folder.

Prompt 2:

> go ahead and create the folder following other homework structures

Prompt 3:

> this is due wednesday so update folder name for that date

Prompt 4 (project primer — context only, not acted on):

> Homework 5: Campus Customs Multi-Agent Operations.
> Campus Customs Multi-Agent Operations is the agentic team that runs the shop, whree open tickets land on a board, and 3 pieces (MCP server, FastAPI backend, and React dashboard) so a human can watch the agents and approve requests. The team has full connectivity, an agent can delegate tasks to any other agent. build these agents:
>
> * boss: reads ticket, decides who should work on it, makes final calls
> * inventory: checks stock by sku and size, spots shortfalls, figures out which vendor can restock
> * accounting: watches cash and invoices, checks margins, prepares payments, prepares purchase orders for human approval
> * facilities: handles shop space side (lease, rent, etc>)
> * customer service: drafts messages for customers
>
> rules of this shop:
>
> * field desk.date_today is "today" for the shop and use for determining what's overdue
> * Vendor lead times come from vendors table
> * vendor will not ship new product while they have open unpaid invoice
> * human approval is required for any payments.
> * if there is not enough cash, the pay tool must refuse - no negative balances
> * cash only goes out, no money comes in
> * before a full run to resolve tickets,make sure to reset the databse to original values.
> * do not email customers or call real vendors
> * use PORTKEY_API_KEY for AI calls, only gpt-6-luna allowed for all agents.
>
> work one problem at a time that i type. these will be recorded in AI_prompts.md. Final submission will be public github repo.
>
> again, don't act on this prompt. this is an overview. if later prompts contradict this info then flag it

## Problem 1: Vibe coder prompts

Prompt 1:

> Problem 1: Vibe coder prompts
> Create AI_prompts.md as with other assignments. One problem for each section, these will be indicated by me starting with Problem #: problem title.

## Problem 2: Study the Campus Customs database

Prompt 1:

> Problem 2: Study the Campus Customs database
> Open data/campus_customs.db and look through everything. Copy the original file to data/campus_customs_new.db. Later problems will update that working copy. Study the three open tickets so you see how they link to other tables. Start output/harness.md. for each table, list the fields and one short line on why that table matters for agents. keep growing the harness file in later problems

## Problem 3: Build the MCP server

Prompt 1:

> Problem 3: Build the MCP server
> Write MCP server in mcp_server/ using FastMCP. Talk to data/campus_customs_new.db. you do not need to connect or run it in this problem. every agent in the hw uses tools in this mcp server, you will add more tools to it later. for now write 3 tools you know you will need for the tickets in the database. keep names clear, never invent any data, only use info from database

Prompt 2:

> Problem 3 prompt 2
> in output/harness.md, list the 3 mcp tools, explain what table it reads, which ticket it helps unlock (101, 102, 103) and on sentence on why that tool is the right one for that ticket. don't be vague  like "reads inventory", be specific and tie the tool to the ticket. add a mcp_server/README.md that explains what the server is for, which database file it uses, and the 3 tools it has

## Problem 4: Add the MCP server to vibe coder and test each tool

Prompt 1:

> Problem 4: Add the MCP server to vibe coder and test each tool
>
> add the mcp server to this project so that the vibe coder can call the tools. save the connection json text in .mcp.json at project root.
> once vibe coder connected, test each of 3 mcp tools. save the evidence in output/mcp_smoke.json. each tool evidence should include:
>
> * prompt you asked the vibe coder
> * tool name
> * tool output - must match values in data/campus_customs_new.db

## Problem 5: Build the agent team and grow the MCP tools

Prompt 1:

> Problem 5: Build the agent team and grow the MCP tools
>
> build agentic team using pydanticai: boss, inventory, accounting, facilities, and customer service. include prompots, models, and agent loops so they can delegate work to each other with full connectivity. put agent prompts in backend/prompts/ - one file per agent. put data types in backend/models.py, agent files under backend/ - five roles should be clear. use PORTKEY_API_KEY and only gpt-6-luna for every agent. write each prompt with shop rules that the agent needs. add necessary and relevant details that will cover agent's work and scope aspects
>
> add any tools agents need to mcp server to work on open tickets. shop facts come from mcp server over data/campus_customs_new.db. do not invent a 2nd shop-tools layer that bypasses mcp. wire the agents so they append to output/audit_trail.json. for each agent loop step, record enough to audit later. append this file, do not wipe each run.
>
> in output/harness.md, list each agent, and each mcp tool with which table the tool uses. add a safety section with guardrails a real business would want when agents touch real customers and real money and limits that keep token use in check
>
> update mcp_server/README.md so the tool list matches the update

## Problem 6: Plan the three tickets

Prompt 1:

> Problem 6: Plan the three tickets
>
> Before you wire the backend, write what you expect the team to do on each open ticket. in output/desk_tickets.html a page where you can double click with one tab per titcket (101, 102, 103). empty cash and reflection tabs for later problems. leave blank or "coming later" note. for each ticket tab fill an "expected" section only, and leave room for "actual" section that will be filled after agents are run.
>
> for each "expected" section, write:
>
> * who the boss should call first and why
> * all agent delegations you expect, not "boss calls everyone"
> * which MCP tools you expect that runs to see
>
> plans that send every specialist on every ticket score low.

## Problem 7: Backend routes

Prompt 1:

> Problem 7: Backend routes
> React frontend dashboard will be made in the next problem. here we want to build the backend it can call. in backend/main.py, use FastAPI and add routes that do the following
>
> * return the 3 tickets and whether each is open or resolved
> * take a ticket id and run agent team on that ticket
> * return recent agent events - what each agent said and which tools they used - so board can refresh
> * approve a payment or purchase only after a human clicks approve. agents can only prepare the pay.
> * return current checkinf balance from cash_accounts
> * reset database to original values when you want to try a fresh run
>
> in backend/ folder, start the server with: uvicorn main:app --reload --port 8000
>
> should turn backend on at http://localhost:8000 that the frontend dashboard can call
>
> in output/harness.md, list each route in one line (URL and what it does)

## Problem 8: Agent dashboard

Prompt 1:

> Problem 8: Agent dashboard
>
> Build frontend dashbord in frontend/ with react, vite, typescript. should call routes built in problem 7. it should do the following:
>
> * list all 3 tix
> * let user pick 1 ticket and start agent team on it
> * show each agent and what they're saying/doing while ticket runs
> * mark ticket resolve when run finishes
> * summarizes what each agent did on that tiket and show the summary
> * let human approve pay or purchase when asked
> * show checking balance, which should drop after an approved pay
>
> make dashboard look good, be creative but make it a real desk people would want to sit at, so everything should be clear and intuitive. with color scheme that's tasteful but not exhausting to look at.
>
> tell front end to talk to backend at httpL//localhost:8000. backend vite pagae origin (usually http://localhost:5173) so browsed is allowed to call those routes. start the board with : npm run dev
>
> should open the react desk in browser for user to pick tickets and watch agents
>
> output/design.md should have what you choes for dashboard look (layout, how agents read differently, how tickets and resolved tickets and cash show up) and why, including creative choices and what makes it a site humans would enjoy using

## Problem 9: Resolve the tickets

Prompt 1:

> Problem 9: Resolve the tickets
> before testing the agents on a full run, reset the working database data/campus_customs_new.db again to start clean. note starting checking balance. then run all 3 tickets on board (101,102,103) until each is resolved.
>
> open output/desk_tickets.html from problem 6. on each ticket tab, fill the actual section from this run: which agents worked, what they delegated, which tools they used. keep expected section. on cash tab of output/desk_tickets.html, itemize the money
>
> * starting checking balance (after reset)
> * for each ticket, how cash changed when ticket was resolved and why
> * ending checking balance - must match cash_accounts in the working database
>
> wrong cash math loses points even if every ticket is resolved.
>
> save output/resolved_tickets.json - for each ticket: id, final status, short outcome, what each agent contributed, and any human approvals
>
> save output/resolved_board.html - a page you can double click with a screenshot of your react board for each resolved ticket (101, 102, 103)
>
> append real runs to output/audit_trail.json, finish output/harness.md so it covers tables, mcp tools, 5 agents, api routes, dashboard, and safety rules

## Problem 10: Reflection

Prompt 1:

> Problem 10: Reflection
>
> open output/desk_tickets.html and fill the reflection tab, be detailed and thorough in answering these questions specific to this project and this website and these 3 tickets. use ticket and cash tabs on the same page as evidence.
>
> * how would you evaluate performance of agents on each ticket and why?
> * for each ticket, compare actual to expected
> * what would have been simpler as one agent with tools and why
> * describe 3 new problems campus customs might face that this agent team could solve with the tools you built
> * describe 3 new problems that the agent team could not solve and why. explain the tools and agents you would need to solve them
