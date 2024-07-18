# order_service.py
import requests
from flask import Flask, jsonify

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
    requests.put('http://consul:8500/v1/agent/service/register', json=payload)

if __name__ == '__main__':
    register_service()
    app.run(host='0.0.0.0', port=5002)