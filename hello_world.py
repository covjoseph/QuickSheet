from flask import Flask, request, jsonify
import json

app = Flask(__name__)

# Endpoint to handle form submission
@app.route('/submit-order', methods=['POST'])
def submit_order():
    try:
        # Get the order data from the request
        order_data = request.json

        # Read the existing orders from the JSON file
        with open('orders.json', 'r') as file:
            orders = json.load(file)

        # Append the new order to the list
        orders.append(order_data)

        # Write the updated orders back to the JSON file
        with open('orders.json', 'w') as file:
            json.dump(orders, file, indent=4)

        return jsonify({"message": "Order submitted successfully!"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)