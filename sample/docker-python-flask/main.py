from flask import Flask, jsonify, request

app = Flask(__name__)


@app.route("/perform", methods=['POST'])
def perform_endpoint():
    request_data = request.get_json()
    numbers = request_data.get('numbers', [])
    return jsonify(sum(numbers))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=7004)
