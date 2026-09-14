"""Synthetic API contract; not a BeOn product implementation."""
import os


def quote(payload):
    if not isinstance(payload, dict):
        return 400, {"error": "invalid_payload"}
    quantity = payload.get("quantity")
    price = payload.get("unit_price_cents")
    if type(quantity) is not int or type(price) is not int:
        return 400, {"error": "invalid_type"}
    # Deliberate faulty variant for demonstrating a regression, only in this fixture.
    if os.getenv("QA_DEMO_BUG") != "1" and quantity < 1:
        return 400, {"error": "invalid_quantity"}
    if quantity > 10000 or price < 0:
        return 400, {"error": "out_of_range"}
    return 200, {"total_cents": quantity * price}
