# Cafe Management System

A simple, local web application built with Flask and SQLite to manage basic cafe operations like user roles (Admin, Employee, Customer), reservations, and orders.

## Features

* **User Roles:**
    * **Customer:** Can sign up, log in, make reservations, view past reservations, and view associated orders & loyalty points.
    * **Employee:** Can log in, add new customer accounts, add reservations for customers, and create orders (optionally linked to reservations).
    * **Admin:** Can log in and add new employee accounts.
* **Authentication:** Secure login/signup using password hashing.
* **Reservations:** Customers can book tables, and employees can manage reservations.
* **Orders:** Employees can create orders, optionally linking them to reservations. Basic loyalty points are awarded upon order completion if linked to a reservation.
* **Database:** Uses SQLite for simple, file-based data storage.
* **Local Deployment:** Runs entirely on your local machine using Flask's development server.

## Technology Stack

* **Backend:** Python, Flask
* **Database:** SQLite3
* **Frontend:** HTML, CSS
* **Environment Management:** venv

## Setup and Installation

1.  **Clone the Repository:**
    ```bash
    git clone <your-repository-url>
    cd cafe_management_system
    ```
    *(Replace `<your-repository-url>` with the actual URL of your GitHub repository)*

2.  **Create and Activate Virtual Environment (Command Prompt):**
    ```bash
    python -m venv venv
    venv\Scripts\activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Initialize the Database (Integrated Terminal):**
    *(This creates the `cafe.db` file and sets up the necessary tables and default users. It's recommended to run this in your IDE's integrated terminal if available, ensuring the virtual environment is active.)*
    ```bash
    python init_db.py
    ```
    *Alternatively, you can run this command in the Command Prompt after activating the virtual environment.*

## Running the Application (Command Prompt)

1.  **Ensure your virtual environment is activated (see step 2 above).**
2.  **Navigate to the project directory:**
    ```bash
    cd cafe_management_system
    ```
3.  **Run the Flask app:**
    ```bash
    python app.py
    ```
4.  Open your web browser and navigate to: `http://127.0.0.1:5000` or `http://localhost:5000`

## Usage

* **Sign Up:** New users can sign up via the "Sign Up" link (they are created as 'customer' role).
* **Log In:** Use the login form. Default credentials (created by `init_db.py`):
    * **Admin:** `admin` / `adminpass`
    * **Employee:** `employee1` / `emppass`
    * **Customer:** `customer1` / `custpass`
* Navigate through the dashboard specific to your user role to access available features.

## Committing and Pushing Changes (Branch: master)

If you've made changes to the code and want to save them locally and share them with a remote repository (like GitHub), follow these steps in your Command Prompt or integrated terminal (ensure you are in the `cafe_management_system` directory):

1.  **Stage your changes:**
    ```bash
    git add .
    ```
    *(This adds all modified and new files to the staging area. To add specific files, use `git add <filename>`)*

2.  **Commit your changes:**
    ```bash
    git commit -m "Your descriptive commit message here"
    ```
    *(Replace `"Your descriptive commit message here"` with a clear and concise summary of the changes you've made.)*

3.  **Push your local commits to the remote repository (assuming your remote is named `origin` and your branch is `master`):**
    ```bash
    git push origin master
    ```
    *(You might be prompted for your username and password or a personal access token depending on your Git setup.)*

---

*Project created on April 15, 2025, in Chennai, Tamil Nadu, India.*

# Cafe Management System - Database Documentation

## Database Design and Implementation

### Entity-Relationship Model
The system implements a comprehensive ER model with the following entities and relationships:

1. **Users** (1NF - Atomic values)
   - Primary Key: id
   - Attributes: username, password_hash, role, loyalty_points, created_at
   - Relationships: One-to-many with Orders, Reservations

2. **Menu Items** (2NF - No partial dependencies)
   - Primary Key: id
   - Attributes: name, description, price, category, is_available, created_at, updated_at
   - Relationships: One-to-many with Order Items

3. **Reservations** (3NF - No transitive dependencies)
   - Primary Key: id
   - Attributes: customer_id, reservation_time, num_guests, status, created_at
   - Foreign Key: customer_id references Users(id)
   - Relationships: One-to-many with Orders

4. **Orders** (4NF - No multi-valued dependencies)
   - Primary Key: id
   - Attributes: reservation_id, customer_id, employee_id, order_time, total_amount, status
   - Foreign Keys: 
     - reservation_id references Reservations(id)
     - customer_id references Users(id)
     - employee_id references Users(id)
   - Relationships: One-to-many with Order Items

5. **Order Items** (5NF - No join dependencies)
   - Primary Key: id
   - Attributes: order_id, menu_item_id, quantity, price_per_item, special_instructions
   - Foreign Keys:
     - order_id references Orders(id)
     - menu_item_id references Menu Items(id)

6. **Payment Methods** (BCNF - All determinants are candidate keys)
   - Primary Key: id
   - Attributes: name, description

7. **Order Payments**
   - Primary Key: id
   - Attributes: order_id, payment_method_id, amount, payment_time, status
   - Foreign Keys:
     - order_id references Orders(id)
     - payment_method_id references Payment Methods(id)

### Database Features Implementation

#### 1. Constraints
- **Primary Keys**: All tables have AUTO_INCREMENT primary keys
- **Foreign Keys**: Implemented with ON DELETE CASCADE/SET NULL
- **Unique Constraints**: 
  - Username in users table
  - Payment method names
- **Check Constraints**: 
  - Reservation time validation through trigger
  - Role enumeration (customer, employee, admin)
  - Status enumerations for orders and reservations

#### 2. Views
1. **daily_sales**
   - Purpose: Aggregates daily sales data
   - Features: GROUP BY, COUNT, SUM, JOIN operations
   - Columns: order_date, total_orders, total_revenue, unique_customers

2. **customer_loyalty**
   - Purpose: Tracks customer loyalty metrics
   - Features: LEFT JOIN, GROUP BY, aggregation functions
   - Columns: id, username, loyalty_points, total_orders, total_spent, last_order_date

#### 3. Triggers
1. **update_loyalty_points**
   - Event: AFTER INSERT ON orders
   - Purpose: Automatically updates customer loyalty points
   - Action: Adds 10% of order total to customer's loyalty points

2. **check_reservation_time**
   - Event: BEFORE INSERT ON reservations
   - Purpose: Validates reservation time
   - Action: Prevents past date reservations

#### 4. Stored Procedures and Cursors
1. **generate_daily_report**
   - Purpose: Generates detailed daily order reports
   - Features: 
     - Cursor implementation for row-by-row processing
     - Temporary table creation
     - Parameter handling (report_date)
     - Error handling

#### 5. Normalization
- **1NF**: Users table with atomic values
- **2NF**: Menu Items table with no partial dependencies
- **3NF**: Reservations table with no transitive dependencies
- **4NF**: Orders table with no multi-valued dependencies
- **5NF**: Order Items table with no join dependencies
- **BCNF**: Payment Methods table with all determinants as candidate keys

#### 6. Concurrency Control
- Transaction management with explicit COMMIT/ROLLBACK
- Autocommit disabled for better transaction control
- Proper connection handling with context managers
- Error handling and rollback mechanisms

#### 7. Recovery Mechanisms
- Transaction rollback on errors
- Connection pooling and proper resource cleanup
- Error logging and user feedback
- Data validation before operations

### Complex Queries Examples
1. **Daily Sales Analysis**
```sql
SELECT 
    DATE(o.order_time) as order_date,
    COUNT(DISTINCT o.id) as total_orders,
    SUM(oi.quantity * oi.price_per_item) as total_revenue,
    COUNT(DISTINCT o.customer_id) as unique_customers
FROM orders o
JOIN order_items oi ON o.id = oi.order_id
GROUP BY DATE(o.order_time);
```

2. **Customer Loyalty Tracking**
```sql
SELECT 
    u.id,
    u.username,
    u.loyalty_points,
    COUNT(DISTINCT o.id) as total_orders,
    SUM(o.total_amount) as total_spent,
    MAX(o.order_time) as last_order_date
FROM users u
LEFT JOIN orders o ON u.id = o.customer_id
WHERE u.role = 'customer'
GROUP BY u.id;
```

3. **Active Customer Analysis**
```sql
SELECT COUNT(DISTINCT customer_id) as count 
FROM orders 
WHERE order_time >= DATE_SUB(NOW(), INTERVAL 30 DAY);
```

### Database Security
- Password hashing using PBKDF2 with SHA256
- Role-based access control
- Input validation and sanitization
- Secure session management
- Proper error handling without exposing sensitive information