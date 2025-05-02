# app.py
import mysql.connector
import os
import datetime
import decimal
from flask import Flask, render_template, request, redirect, url_for, session, g, flash, Response
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import io
import csv
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = os.urandom(24)

# MySQL configuration
MYSQL_CONFIG = {
    'host': 'localhost',
    'user': 'root',  # Replace with your MySQL username
    'password': '0000',  # Replace with your MySQL password
    'database': 'cafe1',
    'raise_on_warnings': True
}

# Add this at the top of the file with other global variables
trigger_initialized = False

def get_db():
    """Opens a new database connection if there is none yet for the current application context."""
    if 'db' not in g:
        try:
            g.db = mysql.connector.connect(**MYSQL_CONFIG)
            g.db.autocommit = False  # Enable manual commit/rollback
            print("MySQL connection opened.")
        except mysql.connector.Error as e:
            print(f"MySQL connection error: {e}")
            flash("Database connection error. Please try again later.", "danger")
            g.db = None
    return g.db

@app.context_processor
def inject_current_year():
    """Inject current year into templates."""
    return {'current_year': datetime.now().year}

@app.teardown_appcontext
def close_db(error):
    """Closes the database again at the end of the request."""
    db = g.pop('db', None)
    if db is not None:
        if db.is_connected():
            db.close()
            print("MySQL connection closed.")
    if error:
        print(f"Application context teardown error: {error}")

# --- Decorators for Access Control ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(required_role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('login'))
            if session.get('role') != required_role:
                flash(f'You do not have permission to access this page. Requires {required_role} role.', 'danger')
                if 'role' in session:
                    return redirect(url_for(f"{session['role']}_dashboard"))
                else:
                    return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# --- Routes ---

@app.route('/employee/reservations')
@login_required
@role_required('employee')
def employee_view_reservations():
    reservations = []
    db = get_db()
    if not db or not db.is_connected():
        return render_template('employee/view_reservations.html', reservations=[], error="Database connection failed")

    try:
        cursor = db.cursor(dictionary=True)  # Return rows as dictionaries
        cursor.execute("""
            SELECT r.id, r.reservation_time, r.num_guests, r.status, u.username AS customer_username
            FROM reservations r
            JOIN users u ON r.customer_id = u.id
            ORDER BY r.reservation_time DESC
        """)
        reservations_data = cursor.fetchall()

        for reservation in reservations_data:
            reservation_id = reservation['id']
            orders = []
            cursor.execute("""
                SELECT o.id AS order_id, o.order_time, o.total_amount, u.username AS employee_username
                FROM orders o
                JOIN users u ON o.employee_id = u.id
                WHERE o.reservation_id = %s
                ORDER BY o.order_time
            """, (reservation_id,))
            orders_data = cursor.fetchall()

            for order in orders_data:
                order_id = order['order_id']
                cursor.execute("""
                    SELECT oi.menu_item_id, oi.quantity, oi.price_per_item, mi.name as item_name
                    FROM order_items oi
                    JOIN menu_items mi ON oi.menu_item_id = mi.id
                    WHERE oi.order_id = %s
                """, (order_id,))
                order['items'] = cursor.fetchall()
                orders.append(order)

            reservation['orders'] = orders
            reservations.append(reservation)

    except mysql.connector.Error as e:
        print(f"MySQL Error fetching reservations with orders for employee: {e}")
        flash("Could not fetch reservation list with order details.", "danger")
    finally:
        cursor.close()

    return render_template('employee/view_reservations.html', reservations=reservations)

@app.route('/employee/customers')
@login_required
@role_required('employee')
def employee_view_customers():
    customers = []
    db = get_db()
    if not db or not db.is_connected():
        return render_template('employee/view_customers.html', customers=[], error="Database connection failed")

    try:
        cursor = db.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, username, loyalty_points, created_at
            FROM users
            WHERE role = 'customer'
            ORDER BY username ASC
        """)
        customers = cursor.fetchall()
    except mysql.connector.Error as e:
        print(f"MySQL Error fetching customers for employee: {e}")
        flash("Could not fetch customer list.", "danger")
    finally:
        cursor.close()

    return render_template('employee/view_customers.html', customers=customers)

@app.route('/admin/users')
@login_required
@role_required('admin')
def admin_view_users():
    users = []
    db = get_db()
    if not db or not db.is_connected():
        return render_template('admin/view_users.html', users=[], error="Database connection failed")

    try:
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT id, username, role, created_at FROM users ORDER BY role, username")
        users = cursor.fetchall()
    except mysql.connector.Error as e:
        print(f"MySQL Error fetching users for admin: {e}")
        flash("Could not fetch user list.", "danger")
    finally:
        cursor.close()

    return render_template('admin/view_users.html', users=users)

@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@login_required
@role_required('admin')
def admin_delete_user(user_id):
    db = get_db()
    if not db or not db.is_connected():
        flash("Database connection failed.", "danger")
        return redirect(url_for('admin_view_users'))

    cursor = None
    try:
        cursor = db.cursor()
        # Prevent self-deletion
        if user_id == session.get('user_id'):
            flash("You cannot delete your own account.", "danger")
            return redirect(url_for('admin_view_users'))

        # Check if user is the only admin
        cursor.execute("SELECT COUNT(*) AS admin_count FROM users WHERE role = 'admin'")
        admin_count = cursor.fetchone()[0]
        cursor.execute("SELECT role FROM users WHERE id = %s", (user_id,))
        user_to_delete = cursor.fetchone()

        if user_to_delete and user_to_delete[0] == 'admin' and admin_count <= 1:
            flash("Cannot delete the only admin account.", "danger")
            return redirect(url_for('admin_view_users'))

        # Check for related records
        cursor.execute("SELECT COUNT(*) FROM reservations WHERE customer_id = %s", (user_id,))
        if cursor.fetchone()[0] > 0:
            flash(f"Cannot delete user ID {user_id}. They have existing reservations. Delete reservations first.", "warning")
            return redirect(url_for('admin_view_users'))

        cursor.execute("SELECT COUNT(*) FROM orders WHERE employee_id = %s", (user_id,))
        if cursor.fetchone()[0] > 0:
            flash(f"Cannot delete user ID {user_id}. They have existing orders recorded.", "warning")
            return redirect(url_for('admin_view_users'))

        # Proceed with deletion
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        db.commit()
        if cursor.rowcount > 0:
            flash(f"User ID {user_id} deleted successfully.", "success")
        else:
            flash(f"User ID {user_id} not found.", "warning")

    except mysql.connector.IntegrityError as e:
        db.rollback()
        print(f"MySQL IntegrityError deleting user {user_id}: {e}")
        flash(f"Could not delete user ID {user_id}. They might be linked to other records.", "danger")
    except mysql.connector.Error as e:
        db.rollback()
        print(f"MySQL Error deleting user {user_id}: {e}")
        flash(f"An error occurred while deleting user ID {user_id}.", "danger")
    finally:
        if cursor:
            cursor.close()

    return redirect(url_for('admin_view_users'))

@app.route('/admin/reservations')
@login_required
@role_required('admin')
def admin_view_reservations():
    reservations = []
    db = get_db()
    if not db or not db.is_connected():
        return render_template('admin/view_reservations.html', reservations=[], error="Database connection failed")

    try:
        cursor = db.cursor(dictionary=True)  # Return rows as dictionaries
        cursor.execute("""
            SELECT r.id, r.reservation_time, r.num_guests, r.status, u.username AS customer_username
            FROM reservations r
            JOIN users u ON r.customer_id = u.id
            ORDER BY r.reservation_time DESC
        """)
        reservations_data = cursor.fetchall()

        for reservation in reservations_data:
            reservation_id = reservation['id']
            orders = []
            cursor.execute("""
                SELECT o.id AS order_id, o.order_time, o.total_amount, u.username AS employee_username
                FROM orders o
                JOIN users u ON o.employee_id = u.id
                WHERE o.reservation_id = %s
                ORDER BY o.order_time
            """, (reservation_id,))
            orders_data = cursor.fetchall()

            for order in orders_data:
                order_id = order['order_id']
                cursor.execute("""
                    SELECT oi.menu_item_id, oi.quantity, oi.price_per_item, mi.name as item_name
                    FROM order_items oi
                    JOIN menu_items mi ON oi.menu_item_id = mi.id
                    WHERE oi.order_id = %s
                """, (order_id,))
                order['items'] = cursor.fetchall()
                orders.append(order)

            reservation['orders'] = orders
            reservations.append(reservation)

    except mysql.connector.Error as e:
        print(f"MySQL Error fetching reservations with orders for admin: {e}")
        flash("Could not fetch reservation list with order details.", "danger")
    finally:
        cursor.close()

    return render_template('admin/view_reservations.html', reservations=reservations)

@app.route('/admin/delete_reservation/<int:res_id>', methods=['POST'])
@login_required
@role_required('admin')
def admin_delete_reservation(res_id):
    db = get_db()
    if not db or not db.is_connected():
        flash("Database connection failed.", "danger")
        return redirect(url_for('admin_view_reservations'))

    cursor = None
    try:
        cursor = db.cursor()
        # Delete associated orders (relies on ON DELETE CASCADE for order_items)
        cursor.execute("DELETE FROM orders WHERE reservation_id = %s", (res_id,))
        print(f"Deleted {cursor.rowcount} orders linked to reservation {res_id}")

        cursor.execute("DELETE FROM reservations WHERE id = %s", (res_id,))
        db.commit()
        if cursor.rowcount > 0:
            flash(f"Reservation ID {res_id} deleted successfully.", "success")
        else:
            flash(f"Reservation ID {res_id} not found.", "warning")

    except mysql.connector.Error as e:
        db.rollback()
        print(f"MySQL Error deleting reservation {res_id}: {e}")
        flash(f"An error occurred while deleting reservation ID {res_id}.", "danger")
    finally:
        if cursor:
            cursor.close()

    return redirect(url_for('admin_view_reservations'))

@app.route('/')
def index():
    if 'user_id' in session:
        role = session.get('role')
        if role == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif role == 'employee':
            return redirect(url_for('employee_dashboard'))
        elif role == 'customer':
            return redirect(url_for('customer_dashboard'))
    return redirect(url_for('login'))

# --- Authentication Routes ---

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        error = None
        db = get_db()
        if not db or not db.is_connected():
            return render_template('login.html', error="Database connection failed")

        user = None
        try:
            cursor = db.cursor(dictionary=True)
            cursor.execute('SELECT * FROM users WHERE username = %s', (username,))
            user = cursor.fetchone()
            cursor.close()
        except mysql.connector.Error as e:
            print(f"MySQL Error during login select: {e}")
            error = "An error occurred during login. Please try again."

        if user is None:
            error = 'Incorrect username.'
        elif not check_password_hash(user['password_hash'], password):
            error = 'Incorrect password.'

        if error is None and user:
            session.clear()
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            flash(f'Welcome back, {user["username"]}!', 'success')
            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user['role'] == 'employee':
                return redirect(url_for('employee_dashboard'))
            elif user['role'] == 'customer':
                return redirect(url_for('customer_dashboard'))
            else:
                flash('Unknown user role.', 'danger')
                return redirect(url_for('login'))
        else:
            flash(error, 'danger')

    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if 'user_id' in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        error = None
        db = get_db()
        if not db or not db.is_connected():
            return render_template('signup.html', error="Database connection failed")

        if not username:
            error = 'Username is required.'
        elif not password:
            error = 'Password is required.'
        elif password != confirm_password:
            error = 'Passwords do not match.'
        else:
            try:
                cursor = db.cursor()
                cursor.execute('SELECT id FROM users WHERE username = %s', (username,))
                if cursor.fetchone() is not None:
                    error = f"Username '{username}' is already taken."
                cursor.close()
            except mysql.connector.Error as e:
                print(f"MySQL Error during signup check: {e}")
                error = "An error occurred checking username availability."

        if error is None:
            password_hash = generate_password_hash(password, method='pbkdf2:sha256')
            try:
                cursor = db.cursor()
                cursor.execute(
                    'INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)',
                    (username, password_hash, 'customer')
                )
                db.commit()
                flash('Account created successfully! Please log in.', 'success')
                cursor.close()
                return redirect(url_for('login'))
            except mysql.connector.IntegrityError:
                error = f"Username '{username}' is already taken."
                flash(error, 'danger')
            except mysql.connector.Error as e:
                print(f"MySQL Error during signup insert: {e}")
                error = "An error occurred creating the account."
                flash(error, 'danger')
                db.rollback()
            finally:
                cursor.close()
        else:
            flash(error, 'danger')

    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# --- Customer Routes ---

@app.route('/customer/dashboard')
@login_required
@role_required('customer')
def customer_dashboard():
    return render_template('customer/dashboard.html', username=session['username'])

@app.route('/customer/reserve', methods=['GET', 'POST'])
@login_required
@role_required('customer')
def customer_make_reservation():
    if request.method == 'POST':
        reservation_time = request.form['reservation_time']
        num_guests = request.form['num_guests']
        customer_id = session['user_id']
        error = None
        db = get_db()
        if not db or not db.is_connected():
            return render_template('customer/make_reservation.html', error="Database connection failed")

        if not reservation_time or not num_guests:
            error = "Please fill in all fields."
        elif int(num_guests) <= 0:
            error = "Number of guests must be positive."

        if error is None:
            try:
                cursor = db.cursor()
                cursor.execute(
                    'INSERT INTO reservations (customer_id, reservation_time, num_guests) VALUES (%s, %s, %s)',
                    (customer_id, reservation_time, num_guests)
                )
                db.commit()
                flash('Reservation made successfully!', 'success')
                cursor.close()
                return redirect(url_for('customer_view_reservations'))
            except mysql.connector.Error as e:
                print(f"MySQL Error during reservation insert: {e}")
                error = "An error occurred making the reservation."
                flash(error, 'danger')
                db.rollback()
            finally:
                cursor.close()
        else:
            flash(error, 'danger')

    return render_template('customer/make_reservation.html')

@app.route('/customer/reservations')
@login_required
@role_required('customer')
def customer_view_reservations():
    reservations = []
    loyalty_points = 0
    db = get_db()
    if not db or not db.is_connected():
        return render_template('customer/view_reservations.html', reservations=[], loyalty_points=0, error="Database connection failed")

    customer_id = session['user_id']
    try:
        cursor = db.cursor(dictionary=True)
        cursor.execute(
            'SELECT id, reservation_time, num_guests, status FROM reservations WHERE customer_id = %s ORDER BY reservation_time DESC',
            (customer_id,)
        )
        reservations = cursor.fetchall()

        cursor.execute('SELECT loyalty_points FROM users WHERE id = %s', (customer_id,))
        user_data = cursor.fetchone()
        if user_data:
            loyalty_points = user_data['loyalty_points']
        cursor.close()

    except mysql.connector.Error as e:
        print(f"MySQL Error fetching reservations/loyalty: {e}")
        flash("Could not fetch reservation history.", "danger")
    finally:
        cursor.close()

    return render_template('customer/view_reservations.html', reservations=reservations, loyalty_points=loyalty_points)

@app.route('/customer/reservation/<int:res_id>/orders')
@login_required
@role_required('customer')
def customer_view_orders(res_id):
    orders = []
    reservation_details = None
    db = get_db()
    customer_id = session['user_id']
    if not db or not db.is_connected():
        return render_template('customer/view_orders.html', orders=[], reservation=None, error="Database connection failed")

    try:
        cursor = db.cursor(dictionary=True)
        cursor.execute('SELECT * FROM reservations WHERE id = %s AND customer_id = %s', (res_id, customer_id))
        reservation_row = cursor.fetchone()
        if reservation_row:
            reservation_details = reservation_row
            cursor.execute("""
                SELECT o.id AS order_id, o.order_time, o.total_amount, u.username AS employee_username
                FROM orders o
                JOIN users u ON o.employee_id = u.id
                WHERE o.reservation_id = %s
                ORDER BY o.order_time
            """, (res_id,))
            orders_data = cursor.fetchall()

            orders = []
            for order in orders_data:
                cursor.execute("""
                    SELECT oi.menu_item_id, oi.quantity, oi.price_per_item, mi.name as item_name
                    FROM order_items oi
                    JOIN menu_items mi ON oi.menu_item_id = mi.id
                    WHERE oi.order_id = %s
                """, (order['order_id'],))
                order['items'] = cursor.fetchall()
                orders.append(order)
        else:
            flash("Reservation not found or access denied.", "warning")
            return redirect(url_for('customer_view_reservations'))
        cursor.close()

    except mysql.connector.Error as e:
        print(f"MySQL Error fetching orders for reservation {res_id}: {e}")
        print(f"Error number: {e.errno}, SQLSTATE: {e.sqlstate}")
        flash("Could not fetch order history for this reservation. Please contact support.", "danger")
    finally:
        cursor.close()

    return render_template('customer/view_orders.html', orders=orders, reservation=reservation_details)

# --- Employee Routes ---

@app.route('/employee/dashboard')
@login_required
@role_required('employee')
def employee_dashboard():
    return render_template('employee/dashboard.html', username=session['username'])

@app.route('/employee/add_customer', methods=['GET', 'POST'])
@login_required
@role_required('employee')
def employee_add_customer():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        error = None
        db = get_db()
        if not db or not db.is_connected():
            return render_template('employee/add_customer.html', error="Database connection failed")

        if not username or not password:
            error = 'Username and password are required.'
        else:
            try:
                cursor = db.cursor()
                cursor.execute('SELECT id FROM users WHERE username = %s', (username,))
                if cursor.fetchone() is not None:
                    error = f"Username '{username}' is already taken."
                cursor.close()
            except mysql.connector.Error as e:
                print(f"MySQL Error checking username (emp add cust): {e}")
                error = "Error checking username availability."

        if error is None:
            password_hash = generate_password_hash(password, method='pbkdf2:sha256')
            try:
                cursor = db.cursor()
                cursor.execute(
                    'INSERT INTO users (username, password_hash, role, loyalty_points) VALUES (%s, %s, %s, %s)',
                    (username, password_hash, 'customer', 0)
                )
                db.commit()
                flash(f'Customer account "{username}" created successfully!', 'success')
                cursor.close()
                return redirect(url_for('employee_dashboard'))
            except mysql.connector.IntegrityError:
                error = f"Username '{username}' is already taken."
                flash(error, 'danger')
            except mysql.connector.Error as e:
                print(f"MySQL Error inserting customer (emp add cust): {e}")
                error = "An error occurred creating the customer account."
                flash(error, 'danger')
                db.rollback()
            finally:
                cursor.close()
        else:
            flash(error, 'danger')

    return render_template('employee/add_customer.html')

@app.route('/employee/add_reservation', methods=['GET', 'POST'])
@login_required
@role_required('employee')
def employee_add_reservation():
    customers = []
    db = get_db()
    if not db or not db.is_connected():
        return render_template('employee/add_reservation.html', customers=[], error="Database connection failed")

    try:
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT id, username FROM users WHERE role = 'customer' ORDER BY username")
        customers = cursor.fetchall()
        cursor.close()
    except mysql.connector.Error as e:
        print(f"MySQL Error fetching customers for emp reservation: {e}")
        flash("Could not load customer list.", "warning")

    if request.method == 'POST':
        customer_id = request.form['customer_id']
        reservation_time = request.form['reservation_time']
        num_guests = request.form['num_guests']
        error = None

        if not customer_id or not reservation_time or not num_guests:
            error = "Please select a customer and fill in all fields."
        elif int(num_guests) <= 0:
            error = "Number of guests must be positive."

        if error is None:
            try:
                cursor = db.cursor()
                cursor.execute(
                    'INSERT INTO reservations (customer_id, reservation_time, num_guests) VALUES (%s, %s, %s)',
                    (customer_id, reservation_time, num_guests)
                )
                db.commit()
                flash('Reservation added successfully for customer!', 'success')
                cursor.close()
                return redirect(url_for('employee_dashboard'))
            except mysql.connector.Error as e:
                print(f"MySQL Error employee adding reservation: {e}")
                error = "An error occurred adding the reservation."
                flash(error, 'danger')
                db.rollback()
            finally:
                cursor.close()
        else:
            flash(error, 'danger')

    return render_template('employee/add_reservation.html', customers=customers)

@app.route('/employee/order/add/<int:reservation_id>', methods=['GET'])
@login_required
@role_required('employee')
def employee_add_order(reservation_id):
    db = get_db()
    if not db or not db.is_connected():
        flash("Database connection failed.", "danger")
        return redirect(url_for('employee_view_reservations'))

    reservation = None
    order_details = None
    order_items = []
    current_total = decimal.Decimal('0.00')
    menu_items = []

    try:
        cursor = db.cursor(dictionary=True)
        cursor.execute("""
            SELECT r.id, r.reservation_time, r.num_guests, r.status, u.username AS customer_username
            FROM reservations r
            JOIN users u ON r.customer_id = u.id
            WHERE r.id = %s
        """, (reservation_id,))
        reservation = cursor.fetchone()

        if not reservation:
            flash("Reservation not found.", "warning")
            return redirect(url_for('employee_view_reservations'))

        cursor.execute("""
            SELECT id, total_amount FROM orders WHERE reservation_id = %s ORDER BY order_time DESC LIMIT 1
        """, (reservation_id,))
        order_details = cursor.fetchone()

        if order_details:
            cursor.execute("""
                SELECT oi.menu_item_id, oi.quantity, oi.price_per_item, mi.name as item_name
                FROM order_items oi
                JOIN menu_items mi ON oi.menu_item_id = mi.id
                WHERE oi.order_id = %s
            """, (order_details['id'],))
            order_items = cursor.fetchall()
            current_total = decimal.Decimal(str(order_details['total_amount']))

        # Get all available menu items, ordered by category and name
        cursor.execute("""
            SELECT id, name, price, category 
            FROM menu_items 
            WHERE is_available = TRUE 
            ORDER BY category, name
        """)
        menu_items = cursor.fetchall()

        cursor.close()

    except mysql.connector.Error as e:
        print(f"MySQL Error fetching reservation/order details for adding items: {e}")
        flash("Could not load order details.", "danger")
        return redirect(url_for('employee_view_reservations'))

    return render_template(
        'employee/add_order.html',
        reservation=reservation,
        menu_items=menu_items,
        current_order_items=order_items,
        current_total=current_total,
        order_id=order_details['id'] if order_details else None
    )

@app.route('/employee/order/add_item/<int:reservation_id>', methods=['POST'])
@login_required
@role_required('employee')
def employee_add_item(reservation_id):
    try:
        cursor = get_db().cursor()
        employee_id = session['user_id']  # Get current employee's ID
        
        # Get the customer_id from the reservation
        cursor.execute("SELECT customer_id FROM reservations WHERE id = %s", (reservation_id,))
        reservation = cursor.fetchone()
        if not reservation:
            flash('Reservation not found', 'error')
            return redirect(url_for('employee_reservations'))
        
        customer_id = reservation[0]  # Access first column of tuple
        
        # Check if an order exists for this reservation
        cursor.execute("SELECT id FROM orders WHERE reservation_id = %s", (reservation_id,))
        order = cursor.fetchone()
        
        if not order:
            # Create a new order with all required fields
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute(
                """INSERT INTO orders 
                   (reservation_id, customer_id, employee_id, status, order_time, total_amount) 
                   VALUES (%s, %s, %s, 'pending', %s, 0.00)""",
                (reservation_id, customer_id, employee_id, current_time)
            )
            order_id = cursor.lastrowid
            print(f"Created new order ID {order_id} for reservation {reservation_id}")
        else:
            order_id = order[0]  # Access first column of tuple
        
        # Get the item details
        item_id = request.form.get('item_id')
        quantity = int(request.form.get('quantity', 1))
        
        # Check if the menu item exists
        cursor.execute("SELECT id, price FROM menu_items WHERE id = %s", (item_id,))
        menu_item = cursor.fetchone()
        if not menu_item:
            flash('Menu item not found', 'error')
            return redirect(url_for('employee_add_order', reservation_id=reservation_id))
        
        # Add the item to the order
        cursor.execute(
            "INSERT INTO order_items (order_id, menu_item_id, quantity, price_per_item) VALUES (%s, %s, %s, %s)",
            (order_id, item_id, quantity, menu_item[1])  # Access second column (price) of tuple
        )
        
        # Update the order total
        cursor.execute(
            "UPDATE orders SET total_amount = (SELECT SUM(quantity * price_per_item) FROM order_items WHERE order_id = %s) WHERE id = %s",
            (order_id, order_id)
        )
        
        get_db().commit()
        flash('Item added to order successfully', 'success')
        
    except Exception as e:
        get_db().rollback()
        print(f"MySQL Error adding item: {e}")
        flash('Error adding item to order', 'error')
    finally:
        cursor.close()
    
    return redirect(url_for('employee_add_order', reservation_id=reservation_id))

@app.route('/employee/order/complete/<int:reservation_id>', methods=['POST'])
@login_required
@role_required('employee')
def complete_order(reservation_id):
    try:
        cursor = get_db().cursor()
        
        # Get the order details
        cursor.execute("""
            SELECT o.id, o.customer_id, o.total_amount, r.status
            FROM orders o
            JOIN reservations r ON o.reservation_id = r.id
            WHERE o.reservation_id = %s
        """, (reservation_id,))
        order_data = cursor.fetchone()
        
        if not order_data:
            flash('Order not found', 'error')
            return redirect(url_for('employee_view_reservations'))
            
        order_id, customer_id, total_amount, reservation_status = order_data
        
        if reservation_status == 'completed':
            flash('This order has already been completed', 'warning')
            return redirect(url_for('employee_view_reservations'))
        
        # Calculate loyalty points (10% of total amount)
        points = decimal.Decimal(str(total_amount)) * decimal.Decimal('0.10')
        
        # Update loyalty points
        cursor.execute(
            "UPDATE users SET loyalty_points = loyalty_points + %s WHERE id = %s",
            (points, customer_id)
        )
        
        # Mark reservation as completed
        cursor.execute(
            "UPDATE reservations SET status = 'completed' WHERE id = %s",
            (reservation_id,)
        )
        
        # Mark order as delivered (using the correct ENUM value)
        cursor.execute(
            "UPDATE orders SET status = 'delivered' WHERE id = %s",
            (order_id,)
        )
        
        get_db().commit()
        flash(f'Order completed successfully! Awarded {points:.2f} loyalty points to customer.', 'success')
        
    except Exception as e:
        get_db().rollback()
        print(f"MySQL Error completing order: {e}")
        flash('Error completing order', 'error')
    finally:
        cursor.close()
    
    return redirect(url_for('employee_view_reservations'))

def init_loyalty_points_trigger():
    """Initialize the loyalty points trigger."""
    global trigger_initialized
    if trigger_initialized:
        return
        
    try:
        cursor = get_db().cursor()
        # Drop the old trigger if it exists
        cursor.execute("DROP TRIGGER IF EXISTS update_loyalty_points")
        # Create the new trigger
        cursor.execute("""
            CREATE TRIGGER update_loyalty_points
            AFTER INSERT ON orders
            FOR EACH ROW
            BEGIN
                UPDATE users
                SET loyalty_points = loyalty_points + (NEW.total_amount * 0.10)
                WHERE id = NEW.customer_id;
            END
        """)
        get_db().commit()
        print("Loyalty points trigger created successfully")
        trigger_initialized = True
    except Exception as e:
        print(f"Error creating loyalty points trigger: {e}")
        get_db().rollback()
    finally:
        if 'cursor' in locals():
            cursor.close()

# --- Admin Routes ---

@app.route('/admin/dashboard')
@login_required
@role_required('admin')
def admin_dashboard():
    db = get_db()
    if not db or not db.is_connected():
        flash("Database connection failed.", "danger")
        return redirect(url_for('login'))

    try:
        cursor = db.cursor(dictionary=True)
        
        # Get total revenue
        cursor.execute("SELECT COALESCE(SUM(total_amount), 0) as total FROM orders")
        total_revenue = cursor.fetchone()['total']
        
        # Get active customers (customers with orders in last 30 days)
        cursor.execute("""
            SELECT COUNT(DISTINCT customer_id) as count 
            FROM orders 
            WHERE order_time >= DATE_SUB(NOW(), INTERVAL 30 DAY)
        """)
        active_customers = cursor.fetchone()['count']
        
        # Get pending orders
        cursor.execute("SELECT COUNT(*) as count FROM orders WHERE status = 'pending'")
        pending_orders = cursor.fetchone()['count']
        
        # Get recent orders
        cursor.execute("""
            SELECT o.id, o.total_amount, o.order_time, u.username as customer_username
            FROM orders o
            JOIN users u ON o.customer_id = u.id
            ORDER BY o.order_time DESC
            LIMIT 5
        """)
        recent_orders = cursor.fetchall()
        
        # Get recent reservations
        cursor.execute("""
            SELECT r.id, r.reservation_time, r.num_guests, u.username as customer_username
            FROM reservations r
            JOIN users u ON r.customer_id = u.id
            ORDER BY r.reservation_time DESC
            LIMIT 5
        """)
        recent_reservations = cursor.fetchall()
        
        return render_template('admin/dashboard.html',
                             username=session['username'],
                             total_revenue=total_revenue,
                             active_customers=active_customers,
                             pending_orders=pending_orders,
                             recent_orders=recent_orders,
                             recent_reservations=recent_reservations)
                             
    except mysql.connector.Error as e:
        print(f"MySQL Error fetching dashboard data: {e}")
        flash("Could not load dashboard data.", "danger")
        return redirect(url_for('login'))
    finally:
        cursor.close()

@app.route('/admin/add_employee', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def admin_add_employee():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        error = None
        db = get_db()
        if not db or not db.is_connected():
            return render_template('admin/add_employee.html', error="Database connection failed")

        if not username:
            error = 'Username is required.'
        elif not password:
            error = 'Password is required.'
        elif password != confirm_password:
            error = 'Passwords do not match.'
        else:
            try:
                cursor = db.cursor()
                cursor.execute('SELECT id FROM users WHERE username = %s', (username,))
                if cursor.fetchone() is not None:
                    error = f"Username '{username}' is already taken."
                cursor.close()
            except mysql.connector.Error as e:
                print(f"MySQL Error checking username (admin add emp): {e}")
                error = "Error checking username availability."

        if error is None:
            password_hash = generate_password_hash(password, method='pbkdf2:sha256')
            try:
                cursor = db.cursor()
                cursor.execute(
                    'INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)',
                    (username, password_hash, 'employee')
                )
                db.commit()
                flash(f'Employee account "{username}" created successfully!', 'success')
                cursor.close()
                return redirect(url_for('admin_dashboard'))
            except mysql.connector.IntegrityError:
                error = f"Username '{username}' is already taken."
                flash(error, 'danger')
            except mysql.connector.Error as e:
                print(f"MySQL Error inserting employee (admin add emp): {e}")
                error = "An error occurred creating the employee account."
                flash(error, 'danger')
                db.rollback()
            finally:
                cursor.close()
        else:
            flash(error, 'danger')

    return render_template('admin/add_employee.html')

@app.route('/admin/reports')
@login_required
@role_required('admin')
def admin_reports():
    # Get date range for the report
    start_date = request.args.get('start_date', (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'))
    end_date = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))
    
    try:
        cursor = get_db().cursor(dictionary=True)
        
        # Get daily sales data
        cursor.execute("""
            SELECT 
                DATE(order_time) as date,
                COUNT(DISTINCT id) as total_orders,
                SUM(total_amount) as total_revenue,
                COUNT(DISTINCT customer_id) as unique_customers
            FROM orders
            WHERE DATE(order_time) BETWEEN %s AND %s
            GROUP BY DATE(order_time)
            ORDER BY date DESC
        """, (start_date, end_date))
        daily_sales = cursor.fetchall()
        
        # Get top selling items
        cursor.execute("""
            SELECT 
                mi.name,
                mi.category,
                SUM(oi.quantity) as total_quantity,
                SUM(oi.quantity * oi.price_per_item) as total_revenue
            FROM order_items oi
            JOIN menu_items mi ON oi.menu_item_id = mi.id
            JOIN orders o ON oi.order_id = o.id
            WHERE DATE(o.order_time) BETWEEN %s AND %s
            GROUP BY mi.id
            ORDER BY total_quantity DESC
            LIMIT 10
        """, (start_date, end_date))
        top_items = cursor.fetchall()
        
        # Get customer loyalty data
        cursor.execute("""
            SELECT 
                u.username,
                COUNT(DISTINCT o.id) as total_orders,
                SUM(o.total_amount) as total_spent,
                u.loyalty_points
            FROM users u
            JOIN orders o ON u.id = o.customer_id
            WHERE DATE(o.order_time) BETWEEN %s AND %s
            GROUP BY u.id
            ORDER BY total_spent DESC
            LIMIT 10
        """, (start_date, end_date))
        top_customers = cursor.fetchall()
        
        return render_template('admin/reports.html',
                             daily_sales=daily_sales,
                             top_items=top_items,
                             top_customers=top_customers,
                             start_date=start_date,
                             end_date=end_date)
        
    except mysql.connector.Error as e:
        flash(f'Database error: {str(e)}', 'danger')
        return redirect(url_for('index'))
    finally:
        cursor.close()

@app.route('/admin/reports/download')
@login_required
@role_required('admin')
def download_report():
    report_date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    
    try:
        cursor = get_db().cursor()
        
        # Get daily sales data
        cursor.execute("""
            SELECT 
                o.id as order_id,
                o.total_amount,
                o.customer_id,
                u.username as customer_username,
                o.order_time
            FROM orders o
            JOIN users u ON o.customer_id = u.id
            WHERE DATE(o.order_time) = %s
            ORDER BY o.order_time DESC
        """, (report_date,))
        
        # Create CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['Order ID', 'Total Amount', 'Customer ID', 'Customer Username', 'Order Time'])
        
        # Write data
        for row in cursor.fetchall():
            # Format the order time
            formatted_row = list(row)
            formatted_row[-1] = formatted_row[-1].strftime('%Y-%m-%d %H:%M:%S')
            writer.writerow(formatted_row)
        
        # Prepare response
        output.seek(0)
        return Response(
            output,
            mimetype="text/csv",
            headers={"Content-disposition": f"attachment; filename=daily_report_{report_date}.csv"}
        )
        
    except mysql.connector.Error as e:
        flash(f'Database error: {str(e)}', 'danger')
        return redirect(url_for('admin_reports'))
    finally:
        cursor.close()

@app.route('/admin/database/views')
@login_required
@role_required('admin')
def admin_database_views():
    try:
        cursor = get_db().cursor(dictionary=True)
        
        # Get all views
        cursor.execute("SHOW FULL TABLES WHERE TABLE_TYPE LIKE 'VIEW'")
        views = cursor.fetchall()
        
        view_data = {}
        for view in views:
            view_name = list(view.values())[0]
            
            # Get view definition
            cursor.execute(f"SHOW CREATE VIEW {view_name}")
            create_view = cursor.fetchone()
            
            # Get view data
            cursor.execute(f"SELECT * FROM {view_name}")
            columns = [desc[0] for desc in cursor.description]
            data = cursor.fetchall()
            
            view_data[view_name] = {
                'definition': create_view['Create View'],
                'columns': columns,
                'data': data
            }
        
        return render_template('admin/database_views.html', views=view_data)
        
    except mysql.connector.Error as e:
        flash(f'Database error: {str(e)}', 'danger')
        return redirect(url_for('admin_dashboard'))
    finally:
        cursor.close()

@app.route('/admin/triggers')
@login_required
@role_required('admin')
def admin_triggers():
    try:
        cursor = get_db().cursor(dictionary=True)
        
        # Get all triggers
        cursor.execute("""
            SELECT 
                TRIGGER_NAME,
                EVENT_MANIPULATION,
                EVENT_OBJECT_TABLE,
                ACTION_STATEMENT,
                ACTION_TIMING
            FROM information_schema.TRIGGERS 
            WHERE TRIGGER_SCHEMA = %s
        """, (MYSQL_CONFIG['database'],))
        triggers = cursor.fetchall()
        
        # Get trigger effects (example: show loyalty points changes)
        cursor.execute("""
            SELECT 
                u.username,
                u.loyalty_points,
                COUNT(o.id) as total_orders,
                SUM(o.total_amount) as total_spent
            FROM users u
            LEFT JOIN orders o ON u.id = o.customer_id
            WHERE u.role = 'customer'
            GROUP BY u.id
        """)
        trigger_effects = cursor.fetchall()
        
        return render_template('admin/triggers.html', 
                             triggers=triggers,
                             trigger_effects=trigger_effects)
        
    except mysql.connector.Error as e:
        flash(f'Database error: {str(e)}', 'danger')
        return redirect(url_for('admin_dashboard'))
    finally:
        cursor.close()

@app.route('/admin/cursors')
@login_required
@role_required('admin')
def admin_cursors():
    try:
        cursor = get_db().cursor()
        
        # Call the stored procedure that uses cursors
        cursor.callproc('generate_daily_report', [datetime.now().strftime('%Y-%m-%d')])
        
        # Get the results
        results = []
        for result in cursor.stored_results():
            results = result.fetchall()
        
        # Get procedure information
        cursor.execute("""
            SELECT 
                ROUTINE_NAME,
                ROUTINE_DEFINITION
            FROM information_schema.ROUTINES 
            WHERE ROUTINE_SCHEMA = %s 
            AND ROUTINE_TYPE = 'PROCEDURE'
        """, (MYSQL_CONFIG['database'],))
        procedures = cursor.fetchall()
        
        return render_template('admin/cursors.html',
                             cursor_results=results,
                             procedures=procedures)
        
    except mysql.connector.Error as e:
        flash(f'Database error: {str(e)}', 'danger')
        return redirect(url_for('admin_dashboard'))
    finally:
        cursor.close()

# Replace the @app.before_first_request with @app.before_request
@app.before_request
def initialize_database():
    """Initialize database components when the app starts."""
    init_loyalty_points_trigger()

# --- Main Execution ---
if __name__ == '__main__':
    # No database file check needed for MySQL; assume DB is set up
    app.run(debug=True)