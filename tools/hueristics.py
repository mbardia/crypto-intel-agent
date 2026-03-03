from datetime import datetime,timedelta


def _parse_ts(ts_str):
    return datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S").timestamp()


# ══════════════════════════════════════════════════════════════════
# DORMANCY
# Detects long inactivity gaps 
# ══════════════════════════════════════════════════════════════════
def detect_dormancy(txs, gap_days=365):
    if len(txs) < 2:
        return {"triggered": False, "confidence": 0.0, "evidence": "Insufficient transactions"}

    max_gap = 0
    max_gap_dates = ("", "")
    triggered_count = 0

    for i in range(len(txs) - 1):
        t1 = datetime.strptime(txs[i]["timeStamp"], "%Y-%m-%d %H:%M:%S")
        t2 = datetime.strptime(txs[i+1]["timeStamp"], "%Y-%m-%d %H:%M:%S")
        gap = (t2 - t1).days
        if gap > gap_days:
            triggered_count += 1
            if gap > max_gap:
                max_gap = gap
                max_gap_dates = (txs[i]["timeStamp"][:10], txs[i+1]["timeStamp"][:10])

    if triggered_count == 0:
        return {"triggered": False, "confidence": 0.0, "evidence": "No dormancy gaps found"}
    confidence = min(1.0, round(max_gap / (gap_days * 2), 2))

    return {
        "triggered": True,
        "confidence": confidence,
        "evidence": f"{triggered_count} dormancy gap(s) found. Longest: {max_gap} days ({max_gap_dates[0]} → {max_gap_dates[1]})",
        "longest_gap_days": max_gap,
        "gap_count": triggered_count,
    }


# ══════════════════════════════════════════════════════════════════
# FAN OUT
# Detects rapid distribution to many unique recipients in one day
# ══════════════════════════════════════════════════════════════════
def detect_fan_out(txs, address, threshold=20):
    
    cutoff = (datetime.now() - timedelta(days=730)).strftime("%Y-%m-%d")
    daily_recipients = {}
    daily_volume = {}

    for tx in txs:
        if tx["from"].lower() != address.lower():
            continue
        if tx.get("value", 0) <= 0.001:
            continue
        if tx["timeStamp"][:10] < cutoff:
            continue
        date = tx["timeStamp"][:10]
        if date not in daily_recipients:
            daily_recipients[date] = set()
            daily_volume[date] = 0.0
        daily_recipients[date].add(tx["to"])
        daily_volume[date] += tx.get("value", 0)

    if not daily_recipients:
        return {"triggered": False, "confidence": 0.0, "evidence": "No outgoing transactions found"}

    peak_date = max(daily_recipients, key=lambda d: len(daily_recipients[d]))
    peak_count = len(daily_recipients[peak_date])
    peak_volume = round(daily_volume[peak_date], 4)

    if peak_count <= threshold:
        return {
            "triggered": False,
            "confidence": 0.0,
            "evidence": f"Peak outgoing recipients/day: {peak_count} (threshold: {threshold})",
        }

    confidence = min(1.0, round(peak_count / (threshold * 2), 2))

    return {
        "triggered": True,
        "confidence": confidence,
        "evidence": f"{peak_count} unique recipients on {peak_date}, total volume: {peak_volume} ETH",
        "peak_date": peak_date,
        "peak_recipients": peak_count,
        "peak_volume_eth": peak_volume,
    }


# ══════════════════════════════════════════════════════════════════
# RAPID PASSTHROUGH
# Detects receive and send within a tight time window
# ══════════════════════════════════════════════════════════════════
def detect_rapid_passthrough(txs, address, window_seconds=30):
    incoming = sorted(
        [tx for tx in txs if tx.get("to", "").lower() == address.lower() and tx.get("value", 0) > 0.001],
        key=lambda x: x["timeStamp"]
    )
    outgoing = sorted(
        [tx for tx in txs if tx.get("from", "").lower() == address.lower() and tx.get("value", 0) > 0.001],
        key=lambda x: x["timeStamp"]
    )

    if not incoming or not outgoing:
        return {"triggered": False, "confidence": 0.0, "evidence": "No matching in/out transactions"}

    matched_pairs = []
    j = 0

    for tx_in in incoming:
        t1 = _parse_ts(tx_in["timeStamp"])

   
        while j < len(outgoing) and _parse_ts(outgoing[j]["timeStamp"]) <= t1:
            j += 1

        if j < len(outgoing):
            t2 = _parse_ts(outgoing[j]["timeStamp"])
            diff = t2 - t1
            if diff < window_seconds:
                matched_pairs.append({
                    "in_hash":  tx_in.get("hash", "")[:12],
                    "out_hash": outgoing[j].get("hash", "")[:12],
                    "gap_seconds": round(diff, 1),
                    "in_value":  round(tx_in.get("value", 0), 4),
                    "out_value": round(outgoing[j].get("value", 0), 4),
                })

    if not matched_pairs:
        return {"triggered": False, "confidence": 0.0, "evidence": "No rapid passthrough pairs found"}

    confidence = min(1.0, round(len(matched_pairs) / 5, 2))
    fastest = min(matched_pairs, key=lambda x: x["gap_seconds"])

    return {
        "triggered": True,
        "confidence": confidence,
        "evidence": f"{len(matched_pairs)} rapid passthrough pair(s). Fastest: {fastest['gap_seconds']}s gap ({fastest['in_value']} ETH in → {fastest['out_value']} ETH out)",
        "matched_pairs": len(matched_pairs),
        "fastest_gap_seconds": fastest["gap_seconds"],
        "examples": matched_pairs[:3],
    }


# ══════════════════════════════════════════════════════════════════
# PEEL CHAIN
# Detects receive and forward 90%+ of value
# ══════════════════════════════════════════════════════════════════
def detect_peel_chain(txs, address, min_ratio=0.90, max_ratio=1.0, max_window_seconds=300):
    incoming = sorted(
        [tx for tx in txs if tx.get("to", "").lower() == address.lower() and tx.get("value", 0) > 0.001],
        key=lambda x: x["timeStamp"]
    )
    outgoing = sorted(
        [tx for tx in txs if tx.get("from", "").lower() == address.lower() and tx.get("value", 0) > 0.001],
        key=lambda x: x["timeStamp"]
    )

    if not incoming or not outgoing:
        return {"triggered": False, "confidence": 0.0, "evidence": "No value-bearing in/out transactions"}

    matched_pairs = []
    used_out = set()
    j = 0

    for tx_in in incoming:
        t1 = _parse_ts(tx_in["timeStamp"])
        v_in = tx_in.get("value", 0)

        # advance pointer to first outgoing after t1
        while j < len(outgoing) and _parse_ts(outgoing[j]["timeStamp"]) <= t1:
            j += 1

        # find first unused outgoing tx within window with valid ratio
        for k in range(j, len(outgoing)):
            t2 = _parse_ts(outgoing[k]["timeStamp"])
            diff = t2 - t1

            if diff > max_window_seconds:
                break

            if k in used_out:
                continue

            v_out = outgoing[k].get("value", 0)
            ratio = v_out / v_in if v_in > 0 else 0

            # must forward slightly less than received — not more
            if min_ratio <= ratio < max_ratio:
                matched_pairs.append({
                    "in_value":    round(v_in, 4),
                    "out_value":   round(v_out, 4),
                    "ratio":       round(ratio, 3),
                    "gap_seconds": round(diff, 1),
                    "timestamp":   tx_in["timeStamp"],
                })
                used_out.add(k)
                break

    if not matched_pairs:
        return {"triggered": False, "confidence": 0.0, "evidence": "No peel chain pairs found"}

    confidence = min(1.0, round(len(matched_pairs) / 5, 2))
    avg_ratio = round(sum(p["ratio"] for p in matched_pairs) / len(matched_pairs), 3)

    return {
        "triggered": True,
        "confidence": confidence,
        "evidence": f"{len(matched_pairs)} peel pair(s) within {max_window_seconds // 60}min window. Avg ratio: {avg_ratio}",
        "matched_pairs": len(matched_pairs),
        "avg_ratio": avg_ratio,
        "examples": matched_pairs[:3],
    }

def run_all_heuristics(txs, address):
    return {
        "dormancy":          detect_dormancy(txs),
        "fan_out":           detect_fan_out(txs, address),
        "rapid_passthrough": detect_rapid_passthrough(txs, address),
        "peel_chain":        detect_peel_chain(txs, address),
    }
                
   

'''if __name__ == "__main__":
    from etherscan import get_transactions, parse_transactions
    
    raw = get_transactions("0x098B716B8Aaf21512996dC57EB0615e2383E2f96")
    txs = parse_transactions(raw)
    print("dormancy:", detect_dormancy(txs))
    print("fan_out:", detect_fan_out(txs, "0x098b716b8aaf21512996dc57eb0615e2383e2f96"))
    print("rapid_passthrough:", detect_rapid_passthrough(txs, "0x098b716b8aaf21512996dc57eb0615e2383e2f96"))
    print("peel_chain:", detect_peel_chain(txs, "0x098b716b8aaf21512996dc57eb0615e2383e2f96"))'''
