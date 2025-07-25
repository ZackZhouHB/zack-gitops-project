import logging
import requests
from flask import Flask, jsonify
from pygelf import GelfUdpHandler
from prometheus_flask_exporter import PrometheusMetrics
import os

app = Flask(__name__)
metrics = PrometheusMetrics(app)

@app.route('/users')
def get_users():
    users = [
        {'id': 1, 'name': 'Alice'},
        {'id': 2, 'name': 'Bob'}
    ]
    app.logger.info("Fetched user data")
    return jsonify(users)

def register_service():
    payload = {
        "ID": "user-service",
        "Name": "user-service",
        "Address": "user-service",
        "Port": 5001
    }
    response = requests.put('http://consul:8500/v1/agent/service/register', json=payload)
    if response.status_code == 200:
        app.logger.info("User service registered successfully")
    else:
        app.logger.error("Failed to register user service")

if __name__ == '__main__':
    # Configure logging
    logstash_host = os.getenv('LOGSTASH_HOST', 'localhost')
    handler = GelfUdpHandler(host=logstash_host, port=12201)
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)
    
    register_service()
    app.run(host='0.0.0.0', port=5001)
