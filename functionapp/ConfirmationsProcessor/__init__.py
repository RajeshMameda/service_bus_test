import os
import json
import logging

import psycopg2
import azure.functions as func


def main(msg: func.ServiceBusMessage):
    body = msg.get_body().decode("utf-8")
    logging.info("Confirmation received: %s", body)

    data = json.loads(body)

    order_id = data["order_id"]
    status = data.get("status", "confirmed")

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
                UPDATE orders
                SET status = %s,
                    updated_at = NOW()
                WHERE order_id = %s;
                """,
                (status, order_id),
            )

            if cur.rowcount == 0:
                cur.execute(
                    """
                    INSERT INTO orders (order_id, status, updated_at)
                    VALUES (%s, %s, NOW());
                    """,
                    (order_id, status),
                )

    conn.close()
    logging.info("Order %s updated in Postgres with status=%s", order_id, status)