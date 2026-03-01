import os
import json

from azure.servicebus import ServiceBusClient, ServiceBusMessage


def send_order(order_data: dict):
    conn_str = os.environ["ServiceBusConnection"]
    queue_name = os.getenv("ORDERS_QUEUE_NAME", "orders")

    with ServiceBusClient.from_connection_string(conn_str) as client:
        sender = client.get_queue_sender(queue_name=queue_name)
        with sender:
            sender.send_messages(ServiceBusMessage(json.dumps(order_data)))


def send_confirmation(order_id: str, status: str = "confirmed"):
    conn_str = os.environ["ServiceBusConnection"]
    queue_name = os.getenv("CONFIRMATIONS_QUEUE_NAME", "order-confirmations")

    payload = {"order_id": order_id, "status": status}

    with ServiceBusClient.from_connection_string(conn_str) as client:
        sender = client.get_queue_sender(queue_name=queue_name)
        with sender:
            sender.send_messages(ServiceBusMessage(json.dumps(payload)))
