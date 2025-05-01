# init_db.py
import mysql.connector
from werkzeug.security import generate_password_hash

# MySQL configuration
MYSQL_CONFIG = {
    'host': 'localhost',
    'user': 'root',  # Replace with your MySQL username
    'password': '0000',  # Replace with your MySQL password
    'database': 'cafe1'
}

def init_db():
    print(f"Initializing MySQL database: {MYSQL_CONFIG['database']}")
    conn = None
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        print("MySQL connection established.")

        # Drop existing tables (in reverse order due to foreign key constraints)
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
        cursor.execute("DROP TABLE IF EXISTS order_items")
        cursor.execute("DROP TABLE IF EXISTS orders")
        cursor.execute("DROP TABLE IF EXISTS menu_items")
        cursor.execute("DROP TABLE IF EXISTS reservations")
        cursor.execute("DROP TABLE IF EXISTS users")
        cursor.execute("DROP TABLE IF EXISTS payment_methods")
        cursor.execute("DROP TABLE IF EXISTS order_payments")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
        print("Dropped existing tables.")

        # Create users table (1NF - Atomic values)
        cursor.execute("""
        CREATE TABLE users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(255) UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role ENUM('customer', 'employee', 'admin') NOT NULL,
            loyalty_points DECIMAL(10,2) DEFAULT 0.00,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_username (username)
        ) ENGINE=InnoDB;
        """)
        print("Created 'users' table.")

        # Create menu_items table (2NF - No partial dependencies)
        cursor.execute("""
        CREATE TABLE menu_items (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            price DECIMAL(10,2) NOT NULL,
            category VARCHAR(50) NOT NULL,
            is_available BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_category (category)
        ) ENGINE=InnoDB;
        """)
        print("Created 'menu_items' table.")

        # Create reservations table (3NF - No transitive dependencies)
        cursor.execute("""
        CREATE TABLE reservations (
            id INT AUTO_INCREMENT PRIMARY KEY,
            customer_id INT NOT NULL,
            reservation_time DATETIME NOT NULL,
            num_guests INT NOT NULL,
            status ENUM('confirmed', 'cancelled', 'completed') DEFAULT 'confirmed',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES users(id) ON DELETE CASCADE,
            INDEX idx_reservation_time (reservation_time)
        ) ENGINE=InnoDB;
        """)
        print("Created 'reservations' table.")

        # Create payment_methods table (BCNF - All determinants are candidate keys)
        cursor.execute("""
        CREATE TABLE payment_methods (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(50) NOT NULL UNIQUE,
            description TEXT
        ) ENGINE=InnoDB;
        """)
        print("Created 'payment_methods' table.")

        # Create orders table (4NF - No multi-valued dependencies)
        cursor.execute("""
        CREATE TABLE orders (
            id INT AUTO_INCREMENT PRIMARY KEY,
            reservation_id INT,
            customer_id INT NOT NULL,
            employee_id INT NOT NULL,
            order_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_amount DECIMAL(10,2) NOT NULL,
            status ENUM('pending', 'preparing', 'ready', 'delivered', 'cancelled') DEFAULT 'pending',
            FOREIGN KEY (reservation_id) REFERENCES reservations(id) ON DELETE SET NULL,
            FOREIGN KEY (customer_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (employee_id) REFERENCES users(id) ON DELETE CASCADE,
            INDEX idx_order_time (order_time)
        ) ENGINE=InnoDB;
        """)
        print("Created 'orders' table.")

        # Create order_items table (5NF - No join dependencies)
        cursor.execute("""
        CREATE TABLE order_items (
            id INT AUTO_INCREMENT PRIMARY KEY,
            order_id INT NOT NULL,
            menu_item_id INT NOT NULL,
            quantity INT NOT NULL,
            price_per_item DECIMAL(10,2) NOT NULL,
            special_instructions TEXT,
            FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
            FOREIGN KEY (menu_item_id) REFERENCES menu_items(id) ON DELETE CASCADE
        ) ENGINE=InnoDB;
        """)
        print("Created 'order_items' table.")

        # Create order_payments table
        cursor.execute("""
        CREATE TABLE order_payments (
            id INT AUTO_INCREMENT PRIMARY KEY,
            order_id INT NOT NULL,
            payment_method_id INT NOT NULL,
            amount DECIMAL(10,2) NOT NULL,
            payment_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status ENUM('pending', 'completed', 'failed', 'refunded') DEFAULT 'pending',
            FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
            FOREIGN KEY (payment_method_id) REFERENCES payment_methods(id) ON DELETE CASCADE
        ) ENGINE=InnoDB;
        """)
        print("Created 'order_payments' table.")

        # Create Views
        cursor.execute("""
        CREATE OR REPLACE VIEW daily_sales AS
        SELECT 
            DATE(o.order_time) as order_date,
            COUNT(DISTINCT o.id) as total_orders,
            SUM(oi.quantity * oi.price_per_item) as total_revenue,
            COUNT(DISTINCT o.customer_id) as unique_customers
        FROM orders o
        JOIN order_items oi ON o.id = oi.order_id
        GROUP BY DATE(o.order_time);
        """)
        print("Created 'daily_sales' view.")

        cursor.execute("""
        CREATE OR REPLACE VIEW customer_loyalty AS
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
        """)
        print("Created 'customer_loyalty' view.")

        # Create Triggers
        cursor.execute("""
        DELIMITER //
        CREATE TRIGGER update_loyalty_points
        AFTER INSERT ON orders
        FOR EACH ROW
        BEGIN
            UPDATE users
            SET loyalty_points = loyalty_points + (NEW.total_amount * 0.10)
            WHERE id = NEW.customer_id;
        END //
        DELIMITER ;
        """)
        print("Created 'update_loyalty_points' trigger.")

        cursor.execute("""
        DELIMITER //
        CREATE TRIGGER check_reservation_time
        BEFORE INSERT ON reservations
        FOR EACH ROW
        BEGIN
            IF NEW.reservation_time < NOW() THEN
                SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'Reservation time cannot be in the past';
            END IF;
        END //
        DELIMITER ;
        """)
        print("Created 'check_reservation_time' trigger.")

        # Create Stored Procedures
        cursor.execute("DROP PROCEDURE IF EXISTS generate_daily_report")
        cursor.execute("""
        DELIMITER //
        CREATE PROCEDURE generate_daily_report(IN report_date DATE)
        BEGIN
            DECLARE done INT DEFAULT FALSE;
            DECLARE order_id INT;
            DECLARE total_amount DECIMAL(10,2);
            DECLARE cur CURSOR FOR 
                SELECT id, total_amount 
                FROM orders 
                WHERE DATE(order_time) = report_date;
            DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;
            
            CREATE TEMPORARY TABLE IF NOT EXISTS daily_report (
                order_id INT,
                total_amount DECIMAL(10,2),
                customer_id INT,
                order_time TIMESTAMP
            );
            
            OPEN cur;
            read_loop: LOOP
                FETCH cur INTO order_id, total_amount;
                IF done THEN
                    LEAVE read_loop;
                END IF;
                INSERT INTO daily_report 
                SELECT id, total_amount, customer_id, order_time
                FROM orders WHERE id = order_id;
            END LOOP;
            CLOSE cur;
            
            SELECT * FROM daily_report;
            DROP TEMPORARY TABLE daily_report;
        END //
        DELIMITER ;
        """)
        print("Created 'generate_daily_report' procedure.")

        # Seed Data
        admin_pass_hash = generate_password_hash('adminpass', method='pbkdf2:sha256')
        cursor.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)",
            ('admin', admin_pass_hash, 'admin')
        )
        print("Added default admin user (admin/adminpass).")

        emp_pass_hash = generate_password_hash('emppass', method='pbkdf2:sha256')
        cursor.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (%s, %s, %s)",
            ('employee1', emp_pass_hash, 'employee')
        )
        print("Added default employee user (employee1/emppass).")

        cust_pass_hash = generate_password_hash('custpass', method='pbkdf2:sha256')
        cursor.execute(
            "INSERT INTO users (username, password_hash, role, loyalty_points) VALUES (%s, %s, %s, %s)",
            ('customer1', cust_pass_hash, 'customer', 50)
        )
        print("Added default customer user (customer1/custpass).")

        # Insert menu items
        menu_items = [
            ('Espresso', 'Coffee', 150.00, True),
            ('Latte', 'Coffee', 220.00, True),
            ('Cappuccino', 'Coffee', 200.00, True),
            ('Americano', 'Coffee', 180.00, True),
            ('Mocha', 'Coffee', 250.00, True),
            ('Cold Coffee', 'Coffee', 200.00, True),
            ('Masala Chai', 'Tea', 100.00, True),
            ('Ginger Tea', 'Tea', 90.00, True),
            ('Green Tea', 'Tea', 120.00, True),
            ('Iced Tea', 'Tea', 180.00, True),
            ('Hot Chocolate', 'Beverages', 230.00, True),
            ('Lemonade', 'Beverages', 150.00, True),
            ('Milkshake', 'Beverages', 280.00, True),
            ('Smoothie', 'Beverages', 350.00, True),
            ('Croissant', 'Bakery', 180.00, True),
            ('Muffin', 'Bakery', 120.00, True),
            ('Pastry', 'Bakery', 200.00, True),
            ('Cake Slice', 'Bakery', 250.00, True),
            ('Brownie', 'Bakery', 220.00, True),
            ('Cookie', 'Bakery', 100.00, True),
            ('Sandwich', 'Food', 300.00, True),
            ('Panini', 'Food', 350.00, True),
            ('Burger', 'Food', 400.00, True),
            ('Pasta', 'Food', 450.00, True),
            ('Pizza Slice', 'Food', 250.00, True),
            ('Garlic Bread', 'Food', 200.00, True),
            ('French Fries', 'Food', 150.00, True),
            ('Nachos', 'Food', 280.00, True)
        ]

        cursor.executemany(
            "INSERT INTO menu_items (name, category, price, is_available) VALUES (%s, %s, %s, %s)",
            menu_items
        )
        print("Added sample menu items.")

        # Add payment methods
        payment_methods = [
            ('Cash', 'Physical currency'),
            ('Credit Card', 'Visa, Mastercard, etc.'),
            ('Debit Card', 'Bank card'),
            ('Mobile Payment', 'Apple Pay, Google Pay, etc.')
        ]
        cursor.executemany(
            "INSERT INTO payment_methods (name, description) VALUES (%s, %s)",
            payment_methods
        )
        print("Added payment methods.")

        conn.commit()
        print("Database initialized and seeded successfully.")

    except mysql.connector.Error as e:
        print(f"MySQL error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if conn and conn.is_connected():
            cursor.close()
            conn.close()
            print("MySQL connection closed.")

if __name__ == '__main__':
    init_db()