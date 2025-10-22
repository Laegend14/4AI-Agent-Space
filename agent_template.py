"""
Agent Template for 4AI Agent Space
-----------------------------------
This is a simple Flask-based template for creating a new AI Agent.
To use it:
1. Edit the AGENT_NAME and PORT values.
2. Implement your task logic inside the `handle_task()` function.
3. Run: python agent_template.py
4. Register the agent URL and tags in your cluster configuration.
"""

from flask import Flask, request, jsonify

# ====== Agent Configuration ======
AGENT_NAME = "Sample Agent"
PORT = 5001  # Change if running multiple agents on one machine

# ====== Flask App ======
app = Flask(__name__)

@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": f"{AGENT_NAME} is running and ready to receive tasks!"})

@app.route("/task", methods=["POST"])
def handle_task():
    """
    Handle incoming tasks from the Root Agent.
    Modify this logic to match your agent’s purpose.
    """
    data = request.get_json()
    task = data.get("task", "")

    # Example: Simple echo agent
    result = f"{AGENT_NAME} received task: {task}"

    return jsonify({"result": result})

if __name__ == "__main__":
    print(f"🚀 Starting {AGENT_NAME} on port {PORT}...")
    app.run(host="0.0.0.0", port=PORT)
