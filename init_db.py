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
        cursor.execute("DROP TABLE IF EXISTS reservations")
        cursor.execute("DROP TABLE IF EXISTS users")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
        print("Dropped existing tables.")

        # Create users table
        cursor.execute("""
        CREATE TABLE users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(255) UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role ENUM('customer', 'employee', 'admin') NOT NULL,
            loyalty_points INT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB;
        """)
        print("Created 'users' table.")

        # Create reservations table
        cursor.execute("""
        CREATE TABLE reservations (
            id INT AUTO_INCREMENT PRIMARY KEY,
            customer_id INT NOT NULL,
            reservation_time DATETIME NOT NULL,
            num_guests INT NOT NULL,
            status VARCHAR(20) DEFAULT 'confirmed',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES users(id) ON DELETE CASCADE
        ) ENGINE=InnoDB;
        """)
        print("Created 'reservations' table.")

        # Create orders table
        cursor.execute("""
        CREATE TABLE orders (
            id INT AUTO_INCREMENT PRIMARY KEY,
            reservation_id INT,
            employee_id INT NOT NULL,
            order_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            total_amount DECIMAL(10,2) NOT NULL,
            FOREIGN KEY (reservation_id) REFERENCES reservations(id) ON DELETE SET NULL,
            FOREIGN KEY (employee_id) REFERENCES users(id) ON DELETE CASCADE
        ) ENGINE=InnoDB;
        """)
        print("Created 'orders' table.")

        # Create order_items table
        cursor.execute("""
        CREATE TABLE order_items (
            id INT AUTO_INCREMENT PRIMARY KEY,
            order_id INT NOT NULL,
            item_name VARCHAR(255) NOT NULL,
            quantity INT NOT NULL,
            price_per_item DECIMAL(10,2) NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
        ) ENGINE=InnoDB;
        """)
        print("Created 'order_items' table.")

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