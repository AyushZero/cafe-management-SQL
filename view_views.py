import mysql.connector
from tabulate import tabulate

# MySQL configuration
MYSQL_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '0000',
    'database': 'cafe1'
}

def view_database_views():
    try:
        # Connect to MySQL
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        # Get all views
        cursor.execute("SHOW FULL TABLES WHERE TABLE_TYPE LIKE 'VIEW'")
        views = cursor.fetchall()
        
        print("\nAvailable Views:")
        print("-" * 50)
        for view in views:
            view_name = list(view.values())[0]
            print(f"\nView: {view_name}")
            print("-" * 50)
            
            # Get view definition
            cursor.execute(f"SHOW CREATE VIEW {view_name}")
            create_view = cursor.fetchone()
            print("\nView Definition:")
            print(create_view['Create View'])
            
            # Get view data
            cursor.execute(f"SELECT * FROM {view_name}")
            columns = [desc[0] for desc in cursor.description]
            data = cursor.fetchall()
            
            print("\nView Data:")
            if data:
                print(tabulate(data, headers=columns, tablefmt='grid'))
            else:
                print("No data available")
            print("\n" + "="*50)
        
    except mysql.connector.Error as e:
        print(f"MySQL Error: {e}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == '__main__':
    view_database_views() 