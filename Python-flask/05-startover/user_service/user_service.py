import requests
from flask import Flask, jsonify
import time

app = Flask(__name__)

@app.route('/users')
def get_users():
    users = [
        {'id': 1, 'name': 'Alice'},
        {'id': 2, 'name': 'Bob'}
    ]
    return jsonify(users)

def register_service():
    payload = {
        "ID": "user-service",
        "Name": "user-service",
        "Address": "user-service",
        "Port": 5001
    }
    while True:
        try:
            response = requests.put('http://consul:8500/v1/agent/service/register', json=payload)
            if response.status_code == 200:
                print("Successfully registered user-service with Consul")
                break
            else:
                print(f"Failed to register user-service with Consul, status code: {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"Error registering user-service with Consul: {e}")
        time.sleep(5)

if __name__ == '__main__':
    print("Registering user-service with Consul")
    register_service()
    app.run(host='0.0.0.0', port=5001)
