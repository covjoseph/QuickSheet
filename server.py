from flask import Flask, request, jsonify, send_from_directory, session, redirect, url_for, render_template, flash
import json
import uuid
import datetime
import os
import secrets
import config  # Import the new config file

app = Flask(__name__)
# Apply configuration from config.py
app.secret_key = config.APP['secret_key']
app.config['SESSION_TYPE'] = config.APP['session_type']
app.config['SESSION_COOKIE_HTTPONLY'] = config.APP['session_cookie_httponly']
app.config['SESSION_COOKIE_SECURE'] = config.APP['session_cookie_secure']
app.config['PERMANENT_SESSION_LIFETIME'] = config.APP['permanent_session_lifetime']

# Define path to data directory from config
DATA_DIR = config.DATA['dir']

# Ensure data directory exists
if not os.path.exists(DATA_DIR):
    print(f"Creating data directory: {DATA_DIR}")
    os.makedirs(DATA_DIR)

# Create empty JSON files if they don't exist
def initialize_data_files():
    orders_file_path = os.path.join(DATA_DIR, config.DATA['orders_file'])
    topics_file_path = os.path.join(DATA_DIR, config.DATA['topics_file'])
    
    # Create empty orders.json if it doesn't exist
    if not os.path.exists(orders_file_path):
        print(f"Creating empty orders.json file")
        with open(orders_file_path, 'w') as f:
            json.dump({}, f, indent=4)
    
    # Create empty topics.json if it doesn't exist
    if not os.path.exists(topics_file_path):
        print(f"Creating empty topics.json file")
        with open(topics_file_path, 'w') as f:
            json.dump({}, f, indent=4)

# Call initialization function
initialize_data_files()

# Middleware function to check if user is logged in
def admin_login_required(route_function):
    def wrapper(*args, **kwargs):
        if not session.get('admin_logged_in'):
            # Redirect to login page if not logged in
            return redirect(url_for('admin'))
        return route_function(*args, **kwargs)
    wrapper.__name__ = route_function.__name__
    return wrapper

def load_orders_data():
    try:
        with open(os.path.join(DATA_DIR, config.DATA['orders_file']), 'r') as file:
            data = json.load(file)
            if isinstance(data, list) and len(data) == 1 and isinstance(data[0], dict):
                return data[0]
            elif isinstance(data, dict):
                return data
            else:
                print("Warning: orders.json has unexpected format. Starting fresh.")
                return {}
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError:
        print("Warning: orders.json is corrupted or empty. Starting fresh.")
        return {}

def save_orders_data(data):
    if not isinstance(data, dict):
        print("Error: Attempting to save non-dictionary data to orders.json.")
        if isinstance(data, list) and len(data) == 1 and isinstance(data[0], dict):
            data = data[0]
        else:
            raise TypeError("Data to be saved must be a dictionary.")
    with open(os.path.join(DATA_DIR, config.DATA['orders_file']), 'w') as file:
        json.dump(data, file, indent=4)

def load_topics_data():
    try:
        with open(os.path.join(DATA_DIR, config.DATA['topics_file']), 'r') as file:
            print("DEBUG: Loading topics.json file")
            
            # Capture file content for logging
            file_content = file.read()
            print(f"DEBUG: topics.json raw content length: {len(file_content)}")
            print(f"DEBUG: topics.json first 100 chars: {file_content[:100] if file_content else 'EMPTY'}")
            
            # Attempt to parse JSON
            if not file_content.strip():
                print("DEBUG: topics.json is empty")
                return {}
                
            data = json.loads(file_content)
            
            print(f"DEBUG: topics.json parsed successfully: {type(data)}")
            print(f"DEBUG: topics.json contains {len(data)} topics: {list(data.keys())}")
            
            if isinstance(data, dict):
                return data
            else:
                print(f"DEBUG WARNING: topics.json has unexpected format: {type(data)}. Starting fresh.")
                return {}
    except FileNotFoundError:
        print("DEBUG: topics.json file not found, creating new empty dictionary")
        return {}
    except json.JSONDecodeError as e:
        print(f"DEBUG ERROR: topics.json JSON decode error: {str(e)}")
        print("DEBUG: topics.json is corrupted or empty. Starting fresh.")
        return {}
    except Exception as e:
        print(f"DEBUG CRITICAL ERROR loading topics.json: {str(e)}")
        return {}

def save_topics_data(data):
    if not isinstance(data, dict):
        print("Error: Attempting to save non-dictionary data to topics.json.")
        raise TypeError("Data to be saved must be a dictionary.")
    with open(os.path.join(DATA_DIR, config.DATA['topics_file']), 'w') as file:
        json.dump(data, file, indent=4)

# Helper function to get topic ID by name
def get_topic_id_by_name(topic_name):
    topics_data = load_topics_data()
    for topic_id, topic_info in topics_data.items():
        if topic_info.get('name') == topic_name:
            return topic_id
    return None

# Helper function to get topic name by ID
def get_topic_name_by_id(topic_id):
    topics_data = load_topics_data()
    if topic_id in topics_data:
        return topics_data[topic_id].get('name')
    return None

# Function to migrate topic data from orders.json to topics.json (run once)
def migrate_topics_from_orders():
    try:
        orders_data = load_orders_data()
        topics_data = load_topics_data()
        
        # If topics.json already has data, don't overwrite it
        if topics_data:
            return
        
        # Extract topics from orders.json
        for key in list(orders_data.keys()):
            if key.endswith('_meta'):
                topic_name = key[:-5]  # Remove "_meta" suffix
                if topic_name in orders_data:
                    # Create topic entry in topics_data
                    topic_metadata = orders_data[key]
                    
                    # Generate ID if not present
                    if 'id' not in topic_metadata:
                        topic_metadata['id'] = str(uuid.uuid4())
                        
                    topics_data[topic_metadata['id']] = {
                        'name': topic_name,
                        'description': topic_metadata.get('description', ''),
                        'created_at': topic_metadata.get('created_at', datetime.datetime.now().isoformat()),
                        'id': topic_metadata['id']
                    }
                    
                    # Remove topic metadata from orders.json (keeping the orders array)
                    del orders_data[key]
        
        # Save both files
        save_topics_data(topics_data)
        save_orders_data(orders_data)
        
        print(f"Topic migration complete. {len(topics_data)} topics migrated.")
    except Exception as e:
        print(f"Error during topic migration: {str(e)}")

# Run migration on startup
migrate_topics_from_orders()

@app.route('/admin-login', methods=['POST'])
def admin_login():
    auth_data = request.json
    if auth_data.get('username') == config.ADMIN['username'] and auth_data.get('password') == config.ADMIN['password']:
        session['admin_logged_in'] = True
        session.permanent = True  # Use the permanent session lifetime
        return jsonify({"success": True}), 200
    else:
        return jsonify({"success": False, "error": "Invalid credentials"}), 401

@app.route('/admin-logout', methods=['POST'])
def admin_logout():
    session.pop('admin_logged_in', None)
    session.pop('admin_username', None)  # Also remove username from session
    return jsonify({"success": True}), 200

@app.route('/check-auth', methods=['GET'])
def check_auth():
    if session.get('admin_logged_in'):
        return jsonify({"authenticated": True}), 200
    return jsonify({"authenticated": False}), 401

@app.route('/create-topic', methods=['POST'])
@admin_login_required
def create_topic():
    topic_data = request.json
    topic_name = topic_data.get('name', '').strip()
    topic_description = topic_data.get('description', '').strip()
    topic_items = topic_data.get('items', [])
    topic_date = topic_data.get('date', '')

    if not topic_name:
        return jsonify({"success": False, "error": "Topic name is required"}), 400

    try:
        # Load topics
        topics_data = load_topics_data()
        
        # Check if topic already exists
        for _, topic_info in topics_data.items():
            if topic_info.get('name') == topic_name:
                return jsonify({"success": False, "error": "Topic with this name already exists"}), 400
        
        # Generate topic ID
        topic_id = str(uuid.uuid4())
        
        # Create new topic - default state is "draft"
        topics_data[topic_id] = {
            'name': topic_name,
            'description': topic_description,
            'items': topic_items,
            'created_at': datetime.datetime.now().isoformat(),
            'topic_date': topic_date,
            'id': topic_id,
            'state': 'draft'  # Default state is draft
        }
        
        save_topics_data(topics_data)
        
        return jsonify({"success": True, "topic_id": topic_id}), 201
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/admin/data', methods=['GET'])
@admin_login_required
def get_admin_data():
    try:
        print("\nDEBUG: Starting admin data retrieval...")
        
        # Load both data sources
        orders_data = load_orders_data()
        topics_data = load_topics_data()
        
        # Print debug info to server console
        print(f"DEBUG: Topics data loaded: {len(topics_data)} topics")
        print(f"DEBUG: Orders data loaded: {len(orders_data)} topic IDs with orders")
        
        # Print topic names and IDs for debugging
        print("DEBUG: Topics available:")
        for topic_id, topic_info in topics_data.items():
            topic_name = topic_info.get('name', 'NO_NAME')
            print(f"DEBUG:   - Topic: '{topic_name}', ID: '{topic_id}'")
        
        # Create a combined data structure that uses topic names as keys for backwards compatibility with the frontend
        combined_data = {}
        
        # Process each topic in topics.json
        for topic_id, topic_info in topics_data.items():
            topic_name = topic_info.get('name')
            if not topic_name:
                print(f"DEBUG: WARNING: Topic ID {topic_id} has no name - skipping")
                continue
                
            # Store the metadata with the _meta suffix
            combined_data[topic_name + "_meta"] = {
                "description": topic_info.get("description", ""),
                "created_at": topic_info.get("created_at", ""),
                "id": topic_id,
                "items": topic_info.get("items", []),  # Include items in the meta data
                "topic_date": topic_info.get("topic_date", ""),  # Include topic date
                "state": topic_info.get("state", "draft")  # Include topic state, default to draft
            }
            
            # Get orders for this topic ID from orders.json
            if topic_id in orders_data:
                print(f"DEBUG: Topic '{topic_name}' has {len(orders_data[topic_id])} orders in orders.json")
                combined_data[topic_name] = orders_data[topic_id]
            else:
                print(f"DEBUG: Topic '{topic_name}' has no orders in orders.json, adding empty list")
                combined_data[topic_name] = []
        
        print(f"DEBUG: Combined data created with {len(combined_data)} keys")
        print(f"DEBUG: Combined data keys: {list(combined_data.keys())}")
        
        # Final verification check
        for key in combined_data.keys():
            if key.endswith('_meta'):
                topic_name = key[:-5]
                if topic_name not in combined_data:
                    print(f"DEBUG: ERROR: Topic '{topic_name}' meta exists but main data missing!")
        
        return jsonify(combined_data), 200
    except Exception as e:
        print(f"DEBUG: CRITICAL ERROR in get_admin_data: {str(e)}")
        import traceback
        print(f"DEBUG: Traceback: {traceback.format_exc()}")
        return jsonify({"error": f"Failed to load admin data: {str(e)}"}), 500

# New function to get topic details for rendering
def get_topic_details_by_id(topic_id):
    topics_data = load_topics_data()
    if topic_id in topics_data:
        topic_info = topics_data[topic_id]
        items = topic_info.get('items', [])
        # Ensure items is always a list
        if not isinstance(items, list):
            items = []
        return {
            "name": topic_info.get("name"),
            "description": topic_info.get("description", ""),
            "id": topic_id,
            "created_at": topic_info.get("created_at", ""),
            "items": items
        }
    return None

@app.route('/order/<topic_id>')
def order_form_with_topic(topic_id):
    topic_details = get_topic_details_by_id(topic_id)
    if topic_details:
        # Pass items separately to avoid the TypeError
        topic_items = topic_details.get('items', [])
        if not isinstance(topic_items, list):
            topic_items = []
            
        return render_template('order_form.html', topic=topic_details, topic_items=topic_items)
    else:
        return "Topic not found", 404

@app.route('/submit-order', methods=['POST'])
def submit_order():
    try:
        # Extract data from form submission
        customer_name = request.form.get('name')
        division = request.form.get('division')
        email = request.form.get('email')
        phone = request.form.get('phone')
        topic_id = request.form.get('topic_id')  # Get topic_id from hidden input

        if not all([customer_name, division, email, phone, topic_id]):
            return redirect(url_for('failure', message="Missing required customer information or topic ID."))

        # Get topic details to find topic name and validate items
        topic_details = get_topic_details_by_id(topic_id)
        if not topic_details:
            return redirect(url_for('failure', message="Invalid Topic ID."))
        
        topic_name = topic_details['name']
        topic_items_map = {item['name']: item['price'] for item in topic_details.get('items', [])}

        # Process ordered items from the form
        ordered_items = []
        total = 0.0
        for key in request.form:
            if key.startswith('quantity_'):
                item_name = key[len('quantity_'):]
                try:
                    quantity = int(request.form[key])
                    # Modified to include zero quantity items
                    if quantity >= 0 and item_name in topic_items_map:
                        price = topic_items_map[item_name]
                        subtotal = price * quantity
                        ordered_items.append({
                            "name": item_name,
                            "price": price,
                            "quantity": quantity,
                            "subtotal": subtotal
                        })
                        total += subtotal
                    elif quantity < 0:
                        print(f"Warning: Ignoring item '{item_name}' with negative quantity.")
                    else:
                        print(f"Warning: Item '{item_name}' submitted but not found in topic definition.")
                except ValueError:
                    print(f"Warning: Invalid quantity submitted for item '{item_name}'.")
                except Exception as e:
                    print(f"Error processing item {item_name}: {e}")

        if not ordered_items:
            return redirect(url_for('failure', message="No valid items were ordered."))

        # Generate a unique order ID
        order_id = str(uuid.uuid4())
        
        # Capture browser and IP information
        user_meta = {
            'ip': request.remote_addr,
            'browser': request.headers.get('User-Agent', 'Unknown'),
            'referrer': request.referrer,
            'timestamp': datetime.datetime.now().isoformat()
        }
        
        # Create order data structure
        order_data = {
            'id': order_id,
            'created_at': datetime.datetime.now().isoformat(),
            'name': customer_name,
            'division': division,
            'email': email,
            'phone': phone,
            'topic': topic_name,  # Store topic name for reference
            'topic_id': topic_id,  # Store topic ID
            'items': ordered_items,
            'total': total,
            'user_meta': user_meta  # Add user metadata
        }

        # Load orders data
        orders_data = load_orders_data()

        # Add the order to the appropriate topic ID in orders.json
        if topic_id not in orders_data:
            orders_data[topic_id] = []
        
        orders_data[topic_id].append(order_data)
        
        # Save orders data
        save_orders_data(orders_data)
        
        # Redirect to the success page with the new order ID
        return redirect(url_for('success', order_id=order_id))
        
    except Exception as e:
        print(f"Error submitting order: {str(e)}")
        return redirect(url_for('failure', message="An unexpected error occurred."))

@app.route('/success/<order_id>')
def success(order_id):
    """Render the order success page with order details as an invoice"""
    # Find the order in orders.json
    orders_data = load_orders_data()
    
    # Variables to store our data
    order_info = None
    topic_info = None
    
    # Debug information
    print(f"Looking for order with ID: {order_id}")
    
    # This section of code is modified to handle deeper debugging
    for topic_id, orders_list in orders_data.items():
        if not isinstance(orders_list, list):
            print(f"Warning: Orders for topic {topic_id} is not a list: {type(orders_list)}")
            continue
        
        print(f"Checking topic ID: {topic_id} with {len(orders_list)} orders")
        
        # Print first few order IDs from this topic for debugging
        if orders_list:
            sample_ids = [order.get('id', 'unknown') for order in orders_list[:3]]
            print(f"Sample order IDs in this topic: {sample_ids}")
        
        # Find the order in this topic's orders
        for order in orders_list:
            if not isinstance(order, dict):
                print(f"Warning: Order is not a dictionary: {type(order)}")
                continue
                
            # Get the order ID (handle potential missing or different field names)
            current_id = order.get('id')
            
            # Debug comparison
            if current_id:
                match = current_id == order_id
                print(f"Comparing: '{current_id}' to '{order_id}' - Match: {match}")
            
            if current_id == order_id:
                print(f"Found matching order: {order.get('id')}")
                order_info = order
                topic_info = get_topic_details_by_id(topic_id)
                break
        
        if order_info:
            break
    
    if not order_info:
        print(f"ERROR: Order ID '{order_id}' not found in any topic!")
        return redirect(url_for('failure', message="Order not found. Please contact support."))
    
    # Format the date for a more readable display
    if 'created_at' in order_info:
        try:
            date_obj = datetime.datetime.fromisoformat(order_info['created_at'])
            order_info['created_at'] = date_obj.strftime('%B %d, %Y at %I:%M %p')
        except Exception as e:
            print(f"Error formatting date: {e}")
    
    # Explicitly check if items is a list, convert if needed
    if 'items' in order_info and not isinstance(order_info['items'], list):
        print(f"Warning: order.items is not a list, it's a {type(order_info['items'])}")
        # Try to convert to list if possible
        try:
            order_info['items'] = list(order_info['items'])
        except:
            # If conversion fails, set to empty list
            order_info['items'] = []
    
    # Extra debugging for items
    if 'items' in order_info:
        print(f"Items count: {len(order_info['items'])}")
        print(f"First few items: {order_info['items'][:2]}")
        if order_info['items'] and isinstance(order_info['items'][0], dict):
            print(f"Sample item keys: {list(order_info['items'][0].keys())}")
    else:
        print("No 'items' key found in order_info")
        
    print(f"Rendering success template with order data: {order_info}")
    
    # Render the template with our data
    return render_template('success.html', 
                         order_id=order_id, 
                         order=order_info, 
                         topic=topic_info)

@app.route('/')
def index():
    # Check if we're coming from a successful order submission
    if request.args.get('order_success') == 'True':
        # If the user just successfully submitted an order, show a message
        flash("Your order has been submitted successfully! Thank you for your business.")
    return redirect(url_for('admin'))

@app.route('/admin')
def admin():
    return send_from_directory('templates', 'admin_login.html')

@app.route('/dashboard')
@admin_login_required
def dashboard():
    return send_from_directory('templates', 'admin_dashboard.html')

@app.route('/failure')
def failure():
    message = request.args.get('message', 'An error occurred.')
    return render_template('failure.html', error_message=message)

@app.route('/favicon.ico')
def favicon():
    try:
        # Get absolute path to the static directory
        static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
        print(f"DEBUG: Favicon request received. Looking for file at: {os.path.join(static_dir, 'favicon.ico')}")
        print(f"DEBUG: Current working directory: {os.getcwd()}")
        print(f"DEBUG: App root path: {app.root_path}")
        print(f"DEBUG: File exists: {os.path.exists(os.path.join(static_dir, 'favicon.ico'))}")
        
        # Serve the file directly using send_file instead of send_from_directory
        return send_from_directory(static_dir, 'favicon.ico', mimetype='image/x-icon')
    except Exception as e:
        print(f"ERROR: Failed to serve favicon: {str(e)}")
        # Try alternative static directory path as fallback
        try:
            return send_from_directory('static', 'favicon.ico', mimetype='image/x-icon')
        except Exception as e2:
            print(f"ERROR: Fallback failed: {str(e2)}")
            return "", 404

@app.route('/static/<path:path>')
def static_files(path):
    return send_from_directory('static', path)

@app.route('/delete-topic', methods=['POST'])
@admin_login_required
def delete_topic():
    """Delete a topic and its associated data"""
    try:
        # Get the topic name from the request
        data = request.json
        topic_name = data.get('name')
        
        if not topic_name:
            return jsonify({"success": False, "error": "Topic name is required"}), 400
            
        # Load data files
        topics_data = load_topics_data()
        orders_data = load_orders_data()
        
        # Find the topic ID
        topic_id = get_topic_id_by_name(topic_name)
        if not topic_id:
            return jsonify({"success": False, "error": "Topic not found"}), 404
            
        # Check if there are orders for this topic
        if topic_id in orders_data and orders_data[topic_id]:
            return jsonify({
                "success": False, 
                "error": "Cannot delete topic with existing orders. Please delete the orders first."
            }), 400
            
        # Delete topic from topics.json
        del topics_data[topic_id]
        
        # Delete the empty orders array from orders.json if it exists
        if topic_id in orders_data:
            del orders_data[topic_id]
            
        # Save both data files
        save_topics_data(topics_data)
        save_orders_data(orders_data)
        
        return jsonify({"success": True, "message": "Topic deleted successfully"}), 200
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/delete-order', methods=['POST'])
@admin_login_required
def delete_order():
    """Delete an order by its ID"""
    try:
        # Get order ID from the request
        data = request.json
        order_id = data.get('order_id')
        
        if not order_id:
            return jsonify({"success": False, "error": "Order ID is required"}), 400
            
        # Load orders data
        orders_data = load_orders_data()
        
        # Variables to track if we found and deleted the order
        found_topic_id = None
        deleted = False
        
        # Search for the order in all topics
        for topic_id, orders_list in orders_data.items():
            if not isinstance(orders_list, list):
                continue
                
            # Look for the order in this topic's list
            for i, order in enumerate(orders_list):
                if not isinstance(order, dict):
                    continue
                    
                # Check if this is the order we want to delete
                if order.get('id') == order_id:
                    # Remove the order from the list
                    orders_data[topic_id].pop(i)
                    found_topic_id = topic_id
                    deleted = True
                    break
            
            if deleted:
                break
        
        if not deleted:
            return jsonify({"success": False, "error": "Order not found"}), 404
            
        # Save the updated orders data
        save_orders_data(orders_data)
        
        return jsonify({"success": True, "message": "Order deleted successfully"}), 200
        
    except Exception as e:
        print(f"Error deleting order: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/update-order', methods=['POST'])
@admin_login_required
def update_order():
    """Update an order by its ID"""
    try:
        # Get order data from the request
        data = request.json
        order_id = data.get('order_id')
        
        if not order_id:
            return jsonify({"success": False, "error": "Order ID is required"}), 400
            
        # Load orders data
        orders_data = load_orders_data()
        
        # Variables to track if we found and updated the order
        found = False
        
        # Search for the order in all topics
        for topic_id, orders_list in orders_data.items():
            if not isinstance(orders_list, list):
                continue
                
            # Look for the order in this topic's list
            for i, order in enumerate(orders_list):
                if not isinstance(order, dict):
                    continue
                    
                # Check if this is the order we want to update
                if order.get('id') == order_id:
                    # Update the order data while preserving the original creation data
                    original_created_at = order.get('created_at')
                    original_topic = order.get('topic')
                    original_topic_id = order.get('topic_id')
                    
                    # Update customer details
                    orders_data[topic_id][i]['name'] = data.get('name', order.get('name'))
                    orders_data[topic_id][i]['division'] = data.get('division', order.get('division'))
                    orders_data[topic_id][i]['email'] = data.get('email', order.get('email'))
                    orders_data[topic_id][i]['phone'] = data.get('phone', order.get('phone'))
                    
                    # Update status
                    orders_data[topic_id][i]['status'] = data.get('status', order.get('status'))
                    
                    # Update items and total
                    if 'items' in data and isinstance(data['items'], list):
                        orders_data[topic_id][i]['items'] = data['items']
                        orders_data[topic_id][i]['total'] = data.get('total', sum(item.get('subtotal', 0) for item in data['items']))
                    
                    # Preserve original creation data
                    orders_data[topic_id][i]['created_at'] = original_created_at
                    orders_data[topic_id][i]['topic'] = original_topic
                    orders_data[topic_id][i]['topic_id'] = original_topic_id
                    
                    found = True
                    break
            
            if found:
                break
        
        if not found:
            return jsonify({"success": False, "error": "Order not found"}), 404
            
        # Save the updated orders data
        save_orders_data(orders_data)
        
        return jsonify({"success": True, "message": "Order updated successfully"}), 200
        
    except Exception as e:
        print(f"Error updating order: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/update-topic', methods=['POST'])
@admin_login_required
def update_topic():
    topic_data = request.json
    topic_name = topic_data.get('name', '').strip()
    topic_description = topic_data.get('description', '').strip()
    original_topic_name = topic_data.get('originalName', '').strip()
    topic_items = topic_data.get('items', [])
    topic_date = topic_data.get('date', '')

    if not topic_name or not original_topic_name:
        return jsonify({"success": False, "error": "Topic name is required"}), 400

    try:
        # Load topics
        topics_data = load_topics_data()
        
        # Check if topic exists
        found = False
        topic_id = None
        for tid, topic_info in topics_data.items():
            if topic_info.get('name') == original_topic_name:
                found = True
                topic_id = tid
                break
                
        if not found:
            return jsonify({"success": False, "error": "Original topic not found"}), 404
        
        # Check if topic is in launched state and reject edits
        # We don't check for this if the request is specifically to change the state
        if topics_data[topic_id].get('state') == 'launched' and not topic_data.get('stateChange'):
            return jsonify({"success": False, "error": "Cannot edit a launched topic. Unlaunch the topic first."}), 400
            
        # Check if new name already exists (only if name is changing)
        if topic_name != original_topic_name:
            name_exists = any(topic_info.get('name') == topic_name for _, topic_info in topics_data.items())
            if name_exists:
                return jsonify({"success": False, "error": "Topic with this name already exists"}), 400
        
        # Update topic info
        topics_data[topic_id]['name'] = topic_name
        topics_data[topic_id]['description'] = topic_description
        topics_data[topic_id]['items'] = topic_items
        topics_data[topic_id]['topic_date'] = topic_date
        
        save_topics_data(topics_data)
        
        return jsonify({"success": True}), 200
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/launch-topic', methods=['POST'])
@admin_login_required
def launch_topic():
    """Change a topic's state to 'launched'"""
    try:
        # Get topic data from request
        data = request.json
        topic_id = data.get('topic_id')
        
        if not topic_id:
            return jsonify({"success": False, "error": "Topic ID is required"}), 400
            
        # Load topics data
        topics_data = load_topics_data()
        
        # Check if topic exists
        if topic_id not in topics_data:
            return jsonify({"success": False, "error": "Topic not found"}), 404
            
        # Update topic state
        topics_data[topic_id]['state'] = 'launched'
        
        # Save topic data
        save_topics_data(topics_data)
        
        return jsonify({"success": True, "message": "Topic launched successfully"}), 200
        
    except Exception as e:
        print(f"Error launching topic: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/unlaunch-topic', methods=['POST'])
@admin_login_required
def unlaunch_topic():
    """Change a topic's state back to 'draft'"""
    try:
        # Get topic data from request
        data = request.json
        topic_id = data.get('topic_id')
        
        if not topic_id:
            return jsonify({"success": False, "error": "Topic ID is required"}), 400
            
        # Load topics data
        topics_data = load_topics_data()
        
        # Check if topic exists
        if topic_id not in topics_data:
            return jsonify({"success": False, "error": "Topic not found"}), 404
            
        # Update topic state
        topics_data[topic_id]['state'] = 'draft'
        
        # Save topic data
        save_topics_data(topics_data)
        
        return jsonify({"success": True, "message": "Topic unlaunched successfully"}), 200
        
    except Exception as e:
        print(f"Error unlaunching topic: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    app.run(
        host=config.SERVER['host'], 
        port=config.SERVER['port'], 
        debug=config.SERVER['debug']
    )