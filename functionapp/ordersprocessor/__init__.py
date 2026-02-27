import os
import json
import logging

import psycopg2
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

    conn = psycopg2.connect(
        host=os.environ["PGHOST"],
        port=os.environ.get("PGPORT", "5432"),
        dbname=os.environ["PGDATABASE"],
        user=os.environ["PGUSER"],
        password=os.environ["PGPASSWORD"],
        sslmode=os.environ.get("PGSSLMODE", "require"),
    )

    with conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO orders (order_id, customer_id, product_id, quantity, price, status, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (order_id)
                DO UPDATE SET
                    customer_id = EXCLUDED.customer_id,
                    product_id  = EXCLUDED.product_id,
                    quantity    = EXCLUDED.quantity,
                    price       = EXCLUDED.price,
                    status      = EXCLUDED.status,
                    updated_at  = NOW();
                """,
                (
                    data["order_id"],
                    data["customer_id"],
                    data["product_id"],
                    data["quantity"],
                    data["price"],
                    "validated",
                ),
            )

    conn.close()
    logging.info("Order %s upserted to Postgres with status=validated", data["order_id"])

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