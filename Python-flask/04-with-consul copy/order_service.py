# order_service.py
import requests
from flask import Flask, jsonify
import time

app = Flask(__name__)

@app.route('/orders')
def get_orders():
    orders = [
        {'id': 1, 'item': 'Laptop', 'price': 1200},
        {'id': 2, 'item': 'Phone', 'price': 800}
    ]
    return jsonify(orders)

def register_service():
    payload = {
        "ID": "order-service",
        "Name": "order-service",
        "Address": "order-service",
        "Port": 5002
    }
    while True:
        try:
            response = requests.put('http://consul:8500/v1/agent/service/register', json=payload)
            if response.status_code == 200:
                print("Order service registered successfully.")
                break
            else:
                print("Failed to register order service. Retrying...")
        except Exception as e:
            print(f"Error: {e}. Retrying...")
        time.sleep(5)

if __name__ == '__main__':
    register_service()
    app.run(host='0.0.0.0', port=5002)
