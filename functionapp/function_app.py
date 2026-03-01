import json
import logging

import azure.functions as func

from database import get_order, set_order_status, upsert_order_validated
from trigger import send_confirmation, send_order

app = func.FunctionApp()

REQUIRED_KEYS = ["order_id", "customer_id", "product_id", "quantity", "price"]


@app.service_bus_queue_trigger(
    arg_name="msg",
    queue_name="orders",
    connection="ServiceBusConnection",
)
def ordersprocessor(msg: func.ServiceBusMessage):
    body = msg.get_body().decode("utf-8")
    logging.info("Received order message: %s", body)

    data = json.loads(body)

    missing = [k for k in REQUIRED_KEYS if k not in data]
    if missing:
        raise ValueError(f"Missing required keys: {missing}")

    upsert_order_validated(data)
    logging.info("Order %s upserted to Postgres with status=validated", data["order_id"])

    send_confirmation(order_id=data["order_id"], status="confirmed")
    logging.info("Confirmation sent for order_id=%s", data["order_id"])


@app.service_bus_queue_trigger(
    arg_name="msg",
    queue_name="order-confirmations",
    connection="ServiceBusConnection",
)
def confirmationsprocessor(msg: func.ServiceBusMessage):
    body = msg.get_body().decode("utf-8")
    logging.info("Confirmation received: %s", body)

    data = json.loads(body)
    order_id = data["order_id"]
    status = data.get("status", "confirmed")

    set_order_status(order_id=order_id, status=status)
    logging.info("Order %s updated in Postgres with status=%s", order_id, status)


@app.route(
    route="orders",
    methods=["POST"],
    auth_level=func.AuthLevel.ANONYMOUS,
)
def send_order_http(req: func.HttpRequest) -> func.HttpResponse:
    try:
        order_data = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "Invalid JSON"}),
            status_code=400,
            mimetype="application/json",
        )

    missing = [k for k in REQUIRED_KEYS if k not in order_data]
    if missing:
        return func.HttpResponse(
            json.dumps({"error": f"Missing required keys: {missing}"}),
            status_code=400,
            mimetype="application/json",
        )

    send_order(order_data)
    logging.info("Order sent to Service Bus: %s", order_data["order_id"])

    return func.HttpResponse(
        json.dumps({"message": "Order sent successfully", "order_id": order_data["order_id"]}),
        status_code=202,
        mimetype="application/json",
    )


@app.route(
    route="orders/{order_id}",
    methods=["GET"],
    auth_level=func.AuthLevel.ANONYMOUS,
)
def get_order_http(req: func.HttpRequest) -> func.HttpResponse:
    order_id = req.route_params.get("order_id")

    row = get_order(order_id)
    if not row:
        return func.HttpResponse(
            json.dumps({"error": "Order not found", "order_id": order_id}),
            status_code=404,
            mimetype="application/json",
        )

    result = {
        "order_id": row[0],
        "customer_id": row[1],
        "product_id": row[2],
        "quantity": row[3],
        "price": float(row[4]) if row[4] is not None else None,
        "status": row[5],
        "updated_at": row[6].isoformat() if row[6] is not None else None,
    }

    return func.HttpResponse(
        json.dumps(result),
        status_code=200,
        mimetype="application/json",
    )
