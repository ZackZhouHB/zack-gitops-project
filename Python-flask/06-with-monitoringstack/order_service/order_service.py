import logging
import requests
from flask import Flask, jsonify
from pygelf import GelfUdpHandler
from prometheus_flask_exporter import PrometheusMetrics
import os

app = Flask(__name__)
metrics = PrometheusMetrics(app)

@app.route('/orders')
def get_orders():
    orders = [
        {'id': 1, 'item': 'Laptop', 'price': 1200},
        {'id': 2, 'item': 'Phone', 'price': 800}
    ]
    app.logger.info("Fetched order data")
    return jsonify(orders)

def register_service():
    payload = {
        "ID": "order-service",
        "Name": "order-service",
        "Address": "order-service",
        "Port": 5002
    }
    response = requests.put('http://consul:8500/v1/agent/service/register', json=payload)
    if response.status_code == 200:
        app.logger.info("Order service registered successfully")
    else:
        app.logger.error("Failed to register order service")

if __name__ == '__main__':
    # Configure logging
    logstash_host = os.getenv('LOGSTASH_HOST', 'localhost')
    handler = GelfUdpHandler(host=logstash_host, port=12201)
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)
    
    register_service()
    app.run(host='0.0.0.0', port=5002)
