TOOL_REGISTRY = {

    "get_transactions": {
        "description": (
            "Fetches all normal ETH transactions for a wallet. Returns parsed dicts "
            "with: from, to, value (ETH), timeStamp, hash, functionName, isError."
        ),
        "args": {"address": "0x..."},
        "returns": "List[dict]",
        "when_to_use": (
            "Call this FIRST for any address you investigate. Required before "
            "running any heuristics. Call again for each counterparty you decide to follow."
        ),
        "cost": "medium",
    },

    "get_token_transfers": {
        "description": (
            "Fetches ERC-20 token transfers. Detects stablecoin flows (USDT/USDC), "
            "DeFi interactions, and value obfuscation via token swaps."
        ),
        "args": {"address": "0x..."},
        "returns": "List[dict]",
        "when_to_use": (
            "Call when normal ETH txs look clean but functionName fields suggest "
            "token activity, or when inflow/outflow doesn't add up in ETH alone."
        ),
        "cost": "medium",
    },

    "get_internal_transactions": {
        "description": (
            "Fetches smart-contract-triggered internal transfers. These are invisible "
            "in normal tx lists and commonly used to hide flows via mixers or DeFi."
        ),
        "args": {"address": "0x..."},
        "returns": "List[dict]",
        "when_to_use": (
            "Call when normal tx count is low but you suspect hidden activity, "
            "or when functionName is non-empty (contract interaction). "
            "High internal volume + low normal volume = red flag."
        ),
        "cost": "medium",
    },

    "check_sanctions": {
        "description": (
            "Checks if an address is on the OFAC ETH sanctions list. "
            "Returns True if sanctioned."
        ),
        "args": {"address": "0x..."},
        "returns": "bool",
        "when_to_use": (
            "Call for EVERY address you encounter — target and counterparties. "
            "Sanctioned = immediate critical finding. If target is sanctioned, "
            "stop investigation and report critical risk."
        ),
        "cost": "low",
    },

    "detect_dormancy": {
        "description": (
            "Detects if a wallet had an inactive gap > 180 days between transactions. "
            "Seen in hacked wallets, reactivated scam addresses, long-term laundering setups."
        ),
        "args": {"txs": "parsed tx list", "gap_days": "int (default 180)"},
        "returns": "bool",
        "when_to_use": (
            "Run when transaction history spans a long time period or timestamps "
            "look sparse. If True, investigate what triggered reactivation."
        ),
        "cost": "low",
    },

    "detect_fan_out": {
        "description": (
            "Detects if a wallet sent to 10+ unique recipients in a single day. "
            "Classic layering pattern: one wallet rapidly distributes to many to obscure trail."
        ),
        "args": {"txs": "parsed tx list", "address": "0x...", "threshold": "int (default 10)"},
        "returns": "bool",
        "when_to_use": (
            "Run when outgoing tx count is high or many txs share the same date. "
            "If True, check sanctions on the top recipients by volume."
        ),
        "cost": "low",
    },

    "detect_rapid_passthrough": {
        "description": (
            "Detects if a wallet receives then sends funds within 5 minutes. "
            "Passthrough wallets are intermediaries used to break the transaction trail."
        ),
        "args": {"txs": "parsed tx list", "address": "0x...", "window_seconds": "int (default 300)"},
        "returns": "bool",
        "when_to_use": (
            "Run when inflow ≈ outflow or when wallet appears to be a relay. "
            "If True, investigate BOTH the upstream sender and downstream recipient."
        ),
        "cost": "low",
    },

    "detect_peel_chain": {
        "description": (
            "Detects if a wallet receives funds and forwards 80%+ of that value onward. "
            "Peel chains pass funds through sequential wallets, each keeping a small slice."
        ),
        "args": {"txs": "parsed tx list", "address": "0x...", "min_ratio": "float (default 0.8)"},
        "returns": "bool",
        "when_to_use": (
            "Run when total inflow ≈ total outflow. "
            "If True, follow the chain — the next wallet is likely another peel node. "
            "Investigate recursively up to 2 hops."
        ),
        "cost": "low",
    },

    "build_graph": {
        "description": (
            "Builds a NetworkX DiGraph from transactions. "
            "Nodes = wallets, edges = transactions with value + timestamp."
        ),
        "args": {"txs": "parsed tx list"},
        "returns": "nx.DiGraph",
        "when_to_use": (
            "Build after collecting all transactions. Use to analyze network structure: "
            "hub wallets, cluster patterns, chain depth."
        ),
        "cost": "low",
    },

    "visualize_graph": {
        "description": (
            "Saves a PNG of the transaction graph. Target address = red, others = blue. "
            "Output: graph_output.png"
        ),
        "args": {"G": "nx.DiGraph", "address": "0x..."},
        "returns": "None (saves file)",
        "when_to_use": (
            "Call at the END of investigation as a visual summary. "
            "Most useful when graph has many nodes — visual clusters reveal structure."
        ),
        "cost": "low",
    },
}

AGENT_GUIDELINES = """
You are an autonomous crypto fraud investigation agent.

WORKFLOW:
1. get_transactions(target) + check_sanctions(target)  ← always first
2. If sanctioned → STOP, report CRITICAL immediately
3. Run all 4 heuristics on target (cheap, always worth it)
4. Based on findings, decide whether to go deeper:
   - peel_chain=True or rapid_passthrough=True → get_transactions on counterparties (hop 1)
   - fan_out=True → check_sanctions on top 5 recipients by volume
   - <5 normal txs → also call get_internal_transactions + get_token_transfers
   - any address appearing in 3+ txs → check_sanctions on them
5. For each hop 1 address: run heuristics again
   - If peel_chain or rapid_passthrough again → investigate hop 2 (final depth)
6. build_graph → visualize_graph once all data is collected
7. Write final report

DEPTH LIMIT: Never exceed 2 hops from target.

RISK SCORING:
  Sanctioned target:          +100
  Each heuristic flag:         +20
  Sanctioned counterparty:     +40
  Hop 1 address also flagged:  +20

  >80  → CRITICAL
  50-80 → HIGH
  20-49 → MEDIUM
  <20  → LOW
"""