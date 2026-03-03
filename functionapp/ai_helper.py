import os
import json
import logging
from datetime import datetime
from openai import AzureOpenAI


def parse_natural_language_order(text: str) -> dict:
    """
    Uses Azure OpenAI to parse natural language into structured order data.
    
    Args:
        text: Natural language order description
        
    Returns:
        dict: Structured order data with order_id, customer_id, product_id, quantity, price
    """
    try:
        # Initialize Azure OpenAI client
        client = AzureOpenAI(
            api_key=os.environ.get("AZURE_OPENAI_API_KEY"),
            api_version="2024-02-15-preview",
            azure_endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT")
        )
        
        # Create the prompt for order extraction
        system_prompt = """You are an order processing assistant. Extract order information from natural language and return ONLY a valid JSON object with these exact fields:
- order_id: generate a unique ID using format "order-{timestamp}" where timestamp is current unix timestamp
- customer_id: extract customer name/id, if not provided use "customer-unknown"
- product_id: extract product name exactly as mentioned
- quantity: extract quantity as integer
- price: extract price per unit as float (just the number, no currency symbols)

Return ONLY the JSON object, no markdown, no code blocks, no other text."""

        user_prompt = f"Extract order information from: {text}"
        
        # Call Azure OpenAI
        response = client.chat.completions.create(
            model=os.environ.get("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=200
        )
        
        # Extract and parse the response
        ai_response = response.choices[0].message.content.strip()
        logging.info(f"AI Response: {ai_response}")
        
        # Remove markdown code blocks if present
        if ai_response.startswith("```"):
            ai_response = ai_response.split("```")[1]
            if ai_response.startswith("json"):
                ai_response = ai_response[4:]
            ai_response = ai_response.strip()
        
        # Parse JSON from response
        order_data = json.loads(ai_response)
        
        # Validate required fields
        required_fields = ["order_id", "customer_id", "product_id", "quantity", "price"]
        for field in required_fields:
            if field not in order_data:
                raise ValueError(f"Missing required field: {field}")
        
        # Ensure correct types
        order_data["quantity"] = int(order_data["quantity"])
        order_data["price"] = float(order_data["price"])
        
        logging.info(f"Parsed order: {order_data}")
        return order_data
        
    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse AI response as JSON: {e}")
        logging.error(f"AI Response was: {ai_response}")
        raise ValueError("AI failed to generate valid order data")
    except Exception as e:
        logging.error(f"Error in AI order parsing: {e}")
        raise