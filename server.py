from flask import Flask, request, jsonify
from threading import Thread
from claude import ask_claude_beta, extract_json
from main import worker
import json

app = Flask(__name__)


@app.route('/response_handler', methods=['POST'])
def response_handler():
    if request.method == 'POST':
        payload_data = json.loads(request.stream.read().decode())
        thread = Thread(target=worker, args=(payload_data['conversations'],))
        thread.start()
    return jsonify({"status": "AI Processing has been Launched..."})


# app.run(host='0.0.0.0', port=7261)
app.run(host='0.0.0.0', port=5836)
