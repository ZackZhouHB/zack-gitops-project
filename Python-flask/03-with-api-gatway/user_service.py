# user_service.py
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/users')
def get_users():
    users = [
        {'id': 1, 'name': 'Alice'},
        {'id': 2, 'name': 'Bob'}
    ]
    return jsonify(users)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)