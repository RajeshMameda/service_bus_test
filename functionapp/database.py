import os

import psycopg


def get_conn():
    return psycopg.connect(
        host=os.environ["PGHOST"],
        port=os.environ.get("PGPORT", "5432"),
        dbname=os.environ["PGDATABASE"],
        user=os.environ["PGUSER"],
        password=os.environ["PGPASSWORD"],
        sslmode=os.environ.get("PGSSLMODE", "require"),
    )


def upsert_order_validated(data: dict):
    conn = get_conn()
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


def set_order_status(order_id: str, status: str):
    conn = get_conn()
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


def get_order(order_id: str):
    conn = get_conn()
    with conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT order_id, customer_id, product_id, quantity, price, status, updated_at
                FROM orders
                WHERE order_id = %s;
                """,
                (order_id,),
            )
            result = cur.fetchone()
    conn.close()
    return result
