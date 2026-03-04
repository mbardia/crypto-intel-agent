# Crypto Intel Agent

An agentic blockchain fraud investigation tool. Given an Ethereum wallet address, it automatically traces transactions, runs heuristic analysis, checks against sanctions lists, and generates a professional risk report.

**Website:** https://crypto-intel-agent-production.up.railway.app/

## What it does

- Fetches all transactions (normal, internal, and token transfers) for a target wallet
- Checks the wallet against known sanctioned addresses
- Runs heuristic analysis to detect suspicious patterns:
  - **Rapid passthrough** — funds moved in and out within seconds
  - **Peel chains** — layered transactions used to obscure fund flow
  - **Fan-out** — mass transfers to many wallets in a short window
  - **Dormancy** — sudden activity after long periods of inactivity
- Follows the money up to 2 hops deep using an AI agent to identify risky counterparties
- Scores the wallet from 0–100 (LOW / MEDIUM / HIGH / CRITICAL)
- Generates a written investigation report with findings and recommended actions

## Stack

- **Backend** — Python, FastAPI, LangGraph, LangChain, Groq (Llama 3.1)
- **Data** — Etherscan API
- **Deployed on** — Railway
