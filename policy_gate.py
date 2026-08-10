"""A minimal policy gate for agent-driven trading — the layer the model cannot modify.

Every order the deterministic engine emits passes through authorize() before it may reach
the broker adapter. The agent has NO tool that edits this module or its limits at runtime;
a rejected order returns a reason code, not a conversation.

Deliberately boring and dependency-free. Tune the limits to your account; the SHAPE is the
point. Not investment advice.
"""
from dataclasses import dataclass

@dataclass(frozen=True)
class Limits:
    allowed_account: str          # the ONE account the agent may touch
    long_only: bool = True
    max_order_notional: float = 500.0
    max_total_exposure: float = 2000.0
    max_position_weight: float = 0.20   # of total equity
    daily_loss_halt: float = -0.03      # -3% on the day -> stop trading

APPROVED, REJECTED = "APPROVED", "ORDER_REJECTED"

def authorize(order: dict, portfolio: dict, limits: Limits) -> tuple[str, str]:
    """order: {account, symbol, side, notional} — emitted by the deterministic engine.
    portfolio: {equity, exposure, day_pnl_pct, positions: {symbol: notional}}."""
    if order["account"] != limits.allowed_account:
        return REJECTED, "ACCOUNT_NOT_ALLOWLISTED"
    if limits.long_only and order["side"] not in ("BUY", "SELL"):
        return REJECTED, "SIDE_NOT_ALLOWED"
    if limits.long_only and order["side"] == "SELL" \
            and portfolio["positions"].get(order["symbol"], 0) < order["notional"]:
        return REJECTED, "SELL_EXCEEDS_POSITION"   # a short in disguise
    if order["side"] == "BUY":
        if order["notional"] > limits.max_order_notional:
            return REJECTED, "MAX_ORDER_NOTIONAL"
        if portfolio["exposure"] + order["notional"] > limits.max_total_exposure:
            return REJECTED, "MAX_TOTAL_EXPOSURE"
        w = (portfolio["positions"].get(order["symbol"], 0) + order["notional"]) / max(portfolio["equity"], 1e-9)
        if w > limits.max_position_weight:
            return REJECTED, "MAX_POSITION_WEIGHT"
    if portfolio["day_pnl_pct"] <= limits.daily_loss_halt:
        return REJECTED, "DAILY_LOSS_HALT"
    return APPROVED, "OK"

if __name__ == "__main__":
    lim = Limits(allowed_account="AGENTIC-123")
    pf = {"equity": 1000.0, "exposure": 400.0, "day_pnl_pct": -0.01, "positions": {"NVDA": 100.0}}
    tests = [
        ({"account": "AGENTIC-123", "symbol": "NVDA", "side": "BUY",  "notional": 100.0}, APPROVED),
        ({"account": "OTHER-999",   "symbol": "NVDA", "side": "BUY",  "notional": 100.0}, REJECTED),
        ({"account": "AGENTIC-123", "symbol": "NVDA", "side": "BUY",  "notional": 900.0}, REJECTED),
        ({"account": "AGENTIC-123", "symbol": "NVDA", "side": "SELL", "notional": 500.0}, REJECTED),
    ]
    for order, want in tests:
        got, why = authorize(order, pf, lim)
        assert got == want, (order, got, why)
        print(f"{got:14} {why:22} {order['side']} {order['symbol']} ${order['notional']:.0f} @{order['account']}")
    print("self-test OK")
