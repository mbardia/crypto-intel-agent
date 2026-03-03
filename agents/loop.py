import json
import operator
from typing import TypedDict, List, Annotated
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

from tools.etherscan import get_transactions, get_all_transactions,parse_transactions, get_token_transfers, get_internal_transactions
from tools.sanctions import load_sanctioned_addresses, is_sanctioned
from tools.hueristics import run_all_heuristics
from graph.builder import build_graph, visualize_graph
from agents.tools_definitions import TOOL_REGISTRY, AGENT_GUIDELINES


llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0)
sanctioned_set = load_sanctioned_addresses()


class InvestigationState(TypedDict):
    target: str
    hop: int
    investigated: List[str]
    all_txs: dict
    sanctions_results: dict
    heuristic_results: dict
    risk_score: int
    flags: List[str]
    report: str
    messages: Annotated[List, operator.add]


# ===============================
# FETCH ADDRESS
# ===============================
def investigate_address(state):
    addr = state["target"]

    if addr in state["investigated"]:
        return state

    print(f"\n[HOP {state['hop']}] Investigating {addr}")

    txs = get_all_transactions(addr)
    print(f"  → {len(txs)} total transactions (normal + internal + token)")

    state["all_txs"][addr] = txs
    state["sanctions_results"][addr] = is_sanctioned(addr, sanctioned_set)

    if state["sanctions_results"][addr]:
        print("  → SANCTIONED WALLET DETECTED")

    state["investigated"].append(addr)
    return state


# ===============================
# HEURISTICS
# ===============================
def run_heuristics(state):

    addr = state["investigated"][-1]
    txs = state["all_txs"].get(addr, [])

    results = run_all_heuristics(txs, addr)

    state["heuristic_results"][addr] = results

    print("Heuristics:", results)

    return state

# ===============================
# RISK PROPAGATION ENGINE 
# ===============================
def compute_risk(state):

    score = 0
    flags = []

    for addr in state["investigated"]:

        if state["sanctions_results"].get(addr):
            score += 100
            flags.append(f"SANCTIONED: {addr}")

        heur = state["heuristic_results"].get(addr, {})

    for h, result in heur.items():
        if result.get("triggered"):
            weighted = int(result.get("confidence", 0.5) * 20)
            score += weighted
            flags.append(f"{h} (conf: {result['confidence']}) — {result['evidence']}")
    return min(score, 100), flags


# ===============================
# AGENT DECISION
# ===============================
def agent_decide(state):

    if state["hop"] >= 2:
        return state

    addr = state["investigated"][-1]
    txs = state["all_txs"].get(addr, [])

    counterparties = list(set(
        tx["to"]
        for tx in txs
        if tx.get("to")
        and tx["to"] not in state["investigated"]
    ))[:12]

    prompt = f"""
You are a crypto fraud investigator.

Investigated wallet: {addr}
Counterparties: {counterparties}

Return JSON ONLY:
{{"next_addresses":[]}}
"""

    response = llm.invoke([
        SystemMessage(content="JSON only."),
        HumanMessage(content=prompt)
    ])

    try:
        decision = json.loads(response.content)
        nxt = decision.get("next_addresses", [])
    except:
        nxt = []

    for n in nxt:
        if n not in state["investigated"]:
            state["target"] = n
            state["hop"] += 1
            state = investigate_address(state)
            state = run_heuristics(state)

    return state

# ===============================
# REPORT
# ===============================
def generate_report(state):

    score, flags = compute_risk(state)

    level = (
        "CRITICAL" if score >= 80 else
        "HIGH" if score >= 50 else
        "MEDIUM" if score >= 20 else
        "LOW"
    )

    target = state["investigated"][0]

    prompt = f"""
Write professional blockchain investigation summary.

Target: {target}
Wallets analyzed: {len(state['investigated'])}
Risk: {score}/100 ({level})
Flags: {flags}

Explain findings and recommended action.
"""

    response = llm.invoke([HumanMessage(content=prompt)])

    all_txs = [
        tx for txs in state["all_txs"].values()
        for tx in txs
    ]

    if all_txs:
        G = build_graph(all_txs)
        visualize_graph(G, target)

    state["risk_score"] = score
    state["flags"] = flags
    state["report"] = response.content

    return state


def route_after_fetch(state):
    return "run_heuristics"


# ===============================
# GRAPH
# ===============================
def build_agent():

    wf = StateGraph(InvestigationState)

    wf.add_node("investigate", investigate_address)
    wf.add_node("run_heuristics", run_heuristics)
    wf.add_node("agent_decide", agent_decide)
    wf.add_node("generate_report", generate_report)

    wf.set_entry_point("investigate")

    wf.add_conditional_edges(
        "investigate",
        route_after_fetch,
        {"run_heuristics": "run_heuristics"}
    )

    wf.add_edge("run_heuristics", "agent_decide")
    wf.add_edge("agent_decide", "generate_report")
    wf.add_edge("generate_report", END)

    return wf.compile()



if __name__ == "__main__":
    agent = build_agent()

    result = agent.invoke({
        "target":            "0x2FAF487A4414Fe77e2327F0bf4AE2a264a776AD2",
        "hop":               0,
        "investigated":      [],
        "all_txs":           {},
        "sanctions_results": {},
        "heuristic_results": {},
        "risk_score":        0,
        "flags":             [],
        "report":            "",
        "messages":          [],
    })

    print("\n" + "=" * 60)
    print(f"RISK SCORE : {result['risk_score']}/100")
    print(f"FLAGS      : {result['flags']}")
    print(f"\nREPORT:\n{result['report']}")