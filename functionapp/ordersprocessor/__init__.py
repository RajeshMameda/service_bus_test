import os
import json
import logging

import azure.functions as func
from azure.servicebus import ServiceBusClient, ServiceBusMessage

REQUIRED_KEYS = ["order_id", "customer_id", "product_id", "quantity", "price"]

def main(msg: func.ServiceBusMessage):
    body = msg.get_body().decode("utf-8")
    logging.info("Received order message: %s", body)

    data = json.loads(body)

    missing = [k for k in REQUIRED_KEYS if k not in data]
    if missing:
        raise ValueError(f"Missing required keys: {missing}")

    conn_str = os.environ["ServiceBusConnection"]
    confirmations_queue = os.getenv("CONFIRMATIONS_QUEUE_NAME", "order-confirmations")

    confirmation_payload = {
        "order_id": data["order_id"],
        "status": "confirmed"
    }

    with ServiceBusClient.from_connection_string(conn_str) as client:
        sender = client.get_queue_sender(queue_name=confirmations_queue)
        with sender:
            sender.send_messages(ServiceBusMessage(json.dumps(confirmation_payload)))

    logging.info("Confirmation sent for order_id=%s", data["order_id"])