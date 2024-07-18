from flask import Flask, jsonify
import requests
import time

app = Flask(__name__)

def get_service_address(service_name):
    while True:
        try:
            response = requests.get(f'http://consul:8500/v1/catalog/service/{service_name}')
            if response.status_code == 200 and len(response.json()) > 0:
                service_info = response.json()[0]
                return f"http://{service_info['ServiceAddress']}:{service_info['ServicePort']}"
            else:
                print(f"Service {service_name} not found. Retrying...")
        except Exception as e:
            print(f"Error: {e}. Retrying...")
        time.sleep(5)

@app.route('/users')
def get_users():
    user_service_url = get_service_address('user-service')
    response = requests.get(f'{user_service_url}/users')
    return jsonify(response.json())

@app.route('/orders')
def get_orders():
    order_service_url = get_service_address('order-service')
    response = requests.get(f'{order_service_url}/orders')
    return jsonify(response.json())

if __name__ == '__main__':
    time.sleep(15)  # Ensure other services are registered
    app.run(host='0.0.0.0', port=5000)
