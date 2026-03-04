from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel

from agents.loop import build_agent

app = FastAPI(title="Blockchain Investigation API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class InvestigateRequest(BaseModel):
    wallet: str


@app.get("/")
def root():
    return FileResponse("index.html")


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/investigate")
def investigate(req: InvestigateRequest):
    wallet = req.wallet.strip()

    if not wallet.startswith("0x") or len(wallet) != 42:
        raise HTTPException(status_code=400, detail="Invalid Ethereum wallet address")

    try:
        agent = build_agent()

        result = agent.invoke({
            "target":            wallet,
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

        return {
            "risk_score":       result["risk_score"],
            "flags":            result["flags"],
            "report":           result["report"],
            "wallets_analyzed": len(result["investigated"]),
            "investigated":     result["investigated"],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))