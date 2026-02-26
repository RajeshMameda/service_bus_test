import os
import json
from azure.servicebus import ServiceBusClient, ServiceBusMessage
from dotenv import load_dotenv

load_dotenv()

connection_str = os.getenv("SERVICEBUS_CONNECTION_STRING")
queue_name = os.getenv("SERVICEBUS_QUEUE_NAME", "orders")

if not connection_str or not queue_name:
    raise ValueError("Missing environment variables")
    
payload = {
    "order_id": "123",
    "customer_id": "456",
    "product_id": "789",
    "quantity": 2,
    "price": 19.99
}

body = json.dumps(payload)

with ServiceBusClient.from_connection_string(connection_str) as client:
    sender = client.get_queue_sender(queue_name=queue_name)
    with sender:
        message = ServiceBusMessage(body)
        sender.send_messages(message)
print("Message sent successfully:", body)