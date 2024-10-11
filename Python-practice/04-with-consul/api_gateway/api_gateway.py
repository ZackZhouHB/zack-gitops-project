from flask import Flask, jsonify
import requests

app = Flask(__name__)

@app.route('/users')
def get_users():
    response = requests.get('http://user-service:5001/users')
    return jsonify(response.json())

@app.route('/orders')
def get_orders():
    response = requests.get('http://order-service:5002/orders')
    return jsonify(response.json())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
