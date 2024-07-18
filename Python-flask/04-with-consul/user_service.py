# user_service.py
import requests
from flask import Flask, jsonify

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
    requests.put('http://consul:8500/v1/agent/service/register', json=payload)

if __name__ == '__main__':
    register_service()
    app.run(host='0.0.0.0', port=5001)