# app.py
import mysql.connector
import os
import datetime
import decimal
from flask import Flask, render_template, request, redirect, url_for, session, g, flash
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

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

SAMPLE_ITEMS = [
    {'id': 1, 'name': 'Espresso', 'price': 150.00},
    {'id': 2, 'name': 'Latte', 'price': 220.00},
    {'id': 3, 'name': 'Cappuccino', 'price': 200.00},
    {'id': 5, 'name': 'Croissant', 'price': 180.00},
    {'id': 6, 'name': 'Muffin', 'price': 120.00},
    {'id': 7, 'name': 'Sandwich', 'price': 300.00},
    {'id': 8, 'name': 'Americano', 'price': 180.00},
    {'id': 9, 'name': 'Mocha', 'price': 250.00},
    {'id': 10, 'name': 'Hot Chocolate', 'price': 230.00},
    {'id': 11, 'name': 'Masala Chai', 'price': 100.00},
    {'id': 12, 'name': 'Iced Latte', 'price': 250.00},
    {'id': 13, 'name': 'Cold Coffee', 'price': 200.00},
    {'id': 14, 'name': 'Iced Tea', 'price': 180.00},
    {'id': 15, 'name': 'Lemonade', 'price': 150.00},
    {'id': 16, 'name': 'Milkshake', 'price': 280.00},
    {'id': 17, 'name': 'Smoothie', 'price': 350.00},
    {'id': 18, 'name': 'Panini', 'price': 350.00},
    {'id': 19, 'name': 'Burger', 'price': 400.00},
    {'id': 20, 'name': 'Pasta', 'price': 450.00},
    {'id': 21, 'name': 'Pizza Slice', 'price': 250.00},
    {'id': 22, 'name': 'Garlic Bread', 'price': 200.00},
    {'id': 23, 'name': 'French Fries', 'price': 150.00},
    {'id': 24, 'name': 'Nachos', 'price': 280.00},
    {'id': 25, 'name': 'Pastry', 'price': 200.00},
    {'id': 26, 'name': 'Cake Slice', 'price': 250.00},
    {'id': 27, 'name': 'Brownie', 'price': 220.00},
    {'id': 28, 'name': 'Cookie', 'price': 100.00},
    {'id': 29, 'name': 'Ginger Tea', 'price': 90.00},
    {'id': 30, 'name': 'Green Tea', 'price': 120.00}
]

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
    return {'current_year': datetime.datetime.now().year}

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
                    SELECT item_name, quantity, price_per_item
                    FROM order_items
                    WHERE order_id = %s
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
        cursor = db.cursor(dictionary=True)
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
                    SELECT item_name, quantity, price_per_item
                    FROM order_items
                    WHERE order_id = %s
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
                    SELECT item_name, quantity, price_per_item
                    FROM order_items
                    WHERE order_id = %s
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
                SELECT item_name, quantity, price_per_item
                FROM order_items
                WHERE order_id = %s
            """, (order_details['id'],))
            order_items = cursor.fetchall()
            current_total = decimal.Decimal(str(order_details['total_amount']))

        cursor.close()

    except mysql.connector.Error as e:
        print(f"MySQL Error fetching reservation/order details for adding items: {e}")
        flash("Could not load order details.", "danger")
        return redirect(url_for('employee_view_reservations'))

    return render_template(
        'employee/add_order.html',
        reservation=reservation,
        menu_items=SAMPLE_ITEMS,
        current_order_items=order_items,
        current_total=current_total,
        order_id=order_details['id'] if order_details else None
    )

@app.route('/employee/order/add_item/<int:reservation_id>', methods=['POST'])
@login_required
@role_required('employee')
def employee_add_item(reservation_id):
    db = get_db()
    employee_id = session['user_id']
    if not db or not db.is_connected():
        flash("Database connection failed.", "danger")
        return redirect(url_for('employee_add_order', reservation_id=reservation_id))

    item_id_str = request.form.get('item_id')
    quantity_str = request.form.get('quantity', '1')

    if not item_id_str:
        flash("No item selected.", "warning")
        return redirect(url_for('employee_add_order', reservation_id=reservation_id))

    try:
        item_id = int(item_id_str)
        quantity = int(quantity_str)
        if quantity <= 0:
            flash("Quantity must be positive.", "warning")
            return redirect(url_for('employee_add_order', reservation_id=reservation_id))

        selected_item = next((item for item in SAMPLE_ITEMS if item['id'] == item_id), None)

        if not selected_item:
            flash("Selected item not found.", "danger")
            return redirect(url_for('employee_add_order', reservation_id=reservation_id))

        item_name = selected_item['name']
        price_per_item = decimal.Decimal(str(selected_item['price']))
        item_subtotal = price_per_item * quantity

        cursor = None
        order_id = None
        customer_id = None

        try:
            cursor = db.cursor()
            cursor.execute("SELECT customer_id FROM reservations WHERE id = %s", (reservation_id,))
            reservation_data = cursor.fetchone()
            if not reservation_data:
                flash("Could not find reservation to link order.", "danger")
                return redirect(url_for('employee_view_reservations'))
            customer_id = reservation_data[0]

            cursor.execute("SELECT id FROM orders WHERE reservation_id = %s LIMIT 1", (reservation_id,))
            existing_order = cursor.fetchone()

            if existing_order:
                order_id = existing_order[0]
            else:
                cursor.execute(
                    "INSERT INTO orders (reservation_id, employee_id, total_amount) VALUES (%s, %s, %s)",
                    (reservation_id, employee_id, '0.00')
                )
                order_id = cursor.lastrowid
                print(f"Created new order ID {order_id} for reservation {reservation_id}")

            cursor.execute(
                "INSERT INTO order_items (order_id, item_name, quantity, price_per_item) VALUES (%s, %s, %s, %s)",
                (order_id, item_name, quantity, str(price_per_item))
            )
            print(f"Added {quantity} x {item_name} to order {order_id}")

            cursor.execute(
                "SELECT SUM(quantity * price_per_item) AS total FROM order_items WHERE order_id = %s",
                (order_id,)
            )
            result = cursor.fetchone()
            new_total = decimal.Decimal(str(result[0])) if result[0] is not None else decimal.Decimal('0.00')

            cursor.execute("UPDATE orders SET total_amount = %s WHERE id = %s", (str(new_total), order_id))
            print(f"Updated order {order_id} total to {new_total}")

            if customer_id:
                points_to_add = int(item_subtotal)
                if points_to_add > 0:
                    cursor.execute(
                        "UPDATE users SET loyalty_points = loyalty_points + %s WHERE id = %s",
                        (points_to_add, customer_id)
                    )
                    print(f"Awarded {points_to_add} loyalty points to customer {customer_id}")

            db.commit()
            flash(f"{quantity} x {item_name} added. {points_to_add if customer_id and points_to_add > 0 else 0} loyalty points awarded.", "success")

        except mysql.connector.Error as e:
            db.rollback()
            print(f"MySQL Error adding item/updating points: {e}")
            flash("Error adding item to order or updating points.", "danger")
        except Exception as e:
            db.rollback()
            print(f"Generic Error adding item/updating points: {e}")
            flash("An unexpected error occurred.", "danger")
        finally:
            if cursor:
                cursor.close()

    except ValueError:
        flash("Invalid item ID or quantity.", "danger")
    except Exception as e:
        print(f"Error processing add item form: {e}")
        flash("An error occurred processing the request.", "danger")

    return redirect(url_for('employee_add_order', reservation_id=reservation_id))

# --- Admin Routes ---

@app.route('/admin/dashboard')
@login_required
@role_required('admin')
def admin_dashboard():
    return render_template('admin/dashboard.html', username=session['username'])

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

# --- Main Execution ---
if __name__ == '__main__':
    # No database file check needed for MySQL; assume DB is set up
    app.run(debug=True)