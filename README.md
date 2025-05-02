# Cafe Management System

A comprehensive cafe management system built with Flask and MySQL, featuring role-based access control, order management, and customer loyalty tracking.

## Features

### User Roles
- **Admin**: Full system access, user management, reports
- **Employee**: Order management, reservation handling, payment processing
- **Customer**: Make reservations, view order history, track loyalty points

### Core Functionality
- **Reservation Management**
  - Make, view, and manage reservations
  - Track reservation status (confirmed, cancelled, completed)
  - View reservation history

- **Order Management**
  - Create and manage orders for reservations
  - Add/remove items from orders
  - Track order status (pending, preparing, ready, delivered, cancelled)
  - View order history and details

- **Payment Processing**
  - Multiple payment methods support
  - Process payments for orders
  - Track payment status
  - Automatic loyalty points calculation

- **Menu Management**
  - Categorized menu items
  - Price management
  - Availability tracking

- **Customer Loyalty**
  - Points earned on purchases (10% of order total)
  - Points history tracking
  - Customer spending analysis

## Database Schema

### Tables
1. **users**
   - User authentication and role management
   - Loyalty points tracking

2. **reservations**
   - Reservation details
   - Status tracking
   - Customer association

3. **orders**
   - Order details
   - Status tracking
   - Customer and employee association

4. **order_items**
   - Individual items in orders
   - Quantity and pricing
   - Special instructions

5. **menu_items**
   - Menu item details
   - Categories and pricing
   - Availability status

6. **payment_methods**
   - Available payment methods
   - Payment processing details

7. **order_payments**
   - Payment records
   - Payment status tracking

### Views
1. **daily_sales**
   - Daily order statistics
   - Revenue tracking
   - Customer count

2. **customer_loyalty**
   - Customer spending history
   - Points tracking
   - Order frequency

### Triggers
1. **update_loyalty_points**
   - Automatically updates customer loyalty points
   - Triggered on order completion

2. **check_reservation_time**
   - Validates reservation times
   - Prevents past reservations

## Security Features
- Password hashing using PBKDF2 with SHA256
- Role-based access control
- Input validation and sanitization
- Secure session management
- Proper error handling without exposing sensitive information

## Getting Started

### Prerequisites
- Python 3.x
- MySQL Server
- Flask
- mysql-connector-python
- Other dependencies (see requirements.txt)

### Installation
1. Clone the repository
2. Install dependencies: `pip install -r requirements.txt`
3. Configure MySQL connection in `app.py`
4. Initialize the database: `python init_db.py`
5. Run the application: `python app.py`

### Default Users
- Admin: admin/adminpass
- Employee: employee1/emppass
- Customer: customer1/custpass

## Usage

### Admin
- Manage users and roles
- View system reports
- Monitor sales and customer activity
- Access database views and triggers

### Employee
- Handle reservations
- Process orders
- Manage payments
- Track customer orders

### Customer
- Make reservations
- View order history
- Track loyalty points
- View menu items

## Database Queries

### Daily Sales Analysis
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

### Customer Loyalty Tracking
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

### Active Customer Analysis
```sql
SELECT COUNT(DISTINCT customer_id) as count 
FROM orders 
WHERE order_time >= DATE_SUB(NOW(), INTERVAL 30 DAY);
```

## Contributing
1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request

## License
This project is licensed under the MIT License - see the LICENSE file for details.