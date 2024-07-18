# user_service.py
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
                print("User service registered successfully.")
                break
            else:
                print("Failed to register user service. Retrying...")
        except Exception as e:
            print(f"Error: {e}. Retrying...")
        time.sleep(5)

if __name__ == '__main__':
    register_service()
    app.run(host='0.0.0.0', port=5001)
