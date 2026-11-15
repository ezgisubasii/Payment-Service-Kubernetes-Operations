import logging
import os
import sys
import uuid

from flask import Flask, jsonify, request
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("payment-service")

GATEWAY_KEY = os.environ.get("PAYMENT_GATEWAY_KEY")
if not GATEWAY_KEY:
    log.error("PAYMENT_GATEWAY_KEY is not set, exiting")
    sys.exit(1)

PAYMENTS = Counter("payments_total", "Number of payment requests", ["status"])
LATENCY = Histogram("payment_request_duration_seconds", "Time spent handling a payment request")


def mask_card(number):
    return "**** **** **** " + number[-4:]


@app.get("/health")
def health():
    return jsonify(status="ok")


@app.post("/pay")
@LATENCY.time()
def pay():
    data = request.get_json(silent=True) or {}
    card = str(data.get("card_number", ""))
    amount = data.get("amount")

    if not (card.isdigit() and len(card) == 16):
        PAYMENTS.labels(status="failed").inc()
        log.warning("payment rejected: invalid card_number")
        return jsonify(error="invalid card_number"), 400

    if not isinstance(amount, (int, float)) or amount <= 0:
        PAYMENTS.labels(status="failed").inc()
        log.warning("payment rejected: invalid amount card=%s", mask_card(card))
        return jsonify(error="invalid amount"), 400

    tx_id = str(uuid.uuid4())
    PAYMENTS.labels(status="success").inc()
    log.info("payment ok tx=%s card=%s amount=%s", tx_id, mask_card(card), amount)
    return jsonify(transaction_id=tx_id, status="success")


@app.get("/metrics")
def metrics():
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
