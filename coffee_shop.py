import sqlite3
import os
import csv
from sqlite3 import IntegrityError
from datetime import datetime
from faker import Faker
from tabulate import tabulate

fake = None
if not os.path.exists("coffee_shop.db"):
    # Fake data generator
    fake = Faker()

# Initialize SQLite database
conn = sqlite3.connect('coffee_shop.db')
conn.execute("PRAGMA foreign_keys = 1")
cursor = conn.cursor()

# Create tables
cursor.execute('''
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    address TEXT NOT NULL,
    phone_number TEXT NOT NULL
);
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER,
    clerk_id INTEGER,
    delivery_id INTEGER,
    description TEXT NOT NULL,
    date TEXT NOT NULL,
    total_amount REAL NOT NULL,
    status TEXT DEFAULT 'Incomplete',
    FOREIGN KEY (customer_id) REFERENCES customers(id)
    FOREIGN KEY (clerk_id) REFERENCES employees(id)
    FOREIGN KEY (delivery_id) REFERENCES employees(id)
);
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL
);
''')

if fake:
    for username, role in zip(['c1', 'c2', 'd1', 'd2', 'm1'], ['clerk', 'clerk', 'delivery', 'delivery', 'manager']):
        cursor.execute('''
        INSERT INTO employees (username, password, role) VALUES (?, ?, ?);
        ''', (username, 'password', role))

    for _ in range(3):
        cursor.execute('''
        INSERT INTO customers (name, address, phone_number) VALUES (?, ?, ?);
        ''', (fake.name(), fake.address(), fake.phone_number()))

    for _ in range(5):
        cursor.execute('''
        INSERT INTO orders (customer_id, description, date, total_amount, clerk_id) VALUES (?, ?, ?, ?, ?);
        ''', (fake.random_int(min=1, max=3), fake.text(), fake.date_this_decade(), fake.random_int(min=10, max=100), fake.random_int(min=1, max=2)))

    conn.commit()

# Function to export data to CSV
def export_to_csv(table_name, filename):
    cursor.execute(f'SELECT * FROM {table_name};')
    rows = cursor.fetchall()

    with open(filename + '.csv', 'w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow([desc[0] for desc in cursor.description])
        csv_writer.writerows(rows)

# Main program
def login():
    username = input("Enter your username: ")
    password = input("Enter your password: ")

    cursor.execute('SELECT * FROM employees WHERE username=? AND password=?;', (username, password))
    result = cursor.fetchone()

    if result:
        return result[3], result[0]
    else:
        print("Invalid credentials. Please try again.")
        exit()

def clerk_menu():
    print("1. Place an order")
    print("2. Assign order to delivery")
    print("3. Check incomplete orders")

def delivery_menu():
    print("1. Mark order as completed")

def manager_menu():
    print("1. Customer profile")
    print("2. Number of orders in a specific day")
    print("3. Pending orders")
    print("4. Total number of orders per clerk")
    print("5. Export data to CSV")

def place_order(userid):
    try:
        customer_id = int(input("Enter customer ID: "))
    except ValueError as e:
        print(e)
        raise Exception("Wrong customer id type: should be a number, not text")
    description = input("Enter order description: ")
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        total_amount = float(input("Enter total amount: "))
    except ValueError as e:
        print(e)
        raise Exception(f"Wrong total amount type: should be a number, not text")

    try:
        cursor.execute('''
        INSERT INTO orders (customer_id, description, date, total_amount, clerk_id) VALUES (?, ?, ?, ?, ?);
        ''', (customer_id, description, date, total_amount, userid))
        conn.commit()
    except IntegrityError as fk_e:
        print("Customer does not exists. Please add it now")
        name = input("Enter customer name: ")
        address = input("Enter customer address: ")
        phone = input("Enter customer phone number: ")

        cursor.execute('''
        INSERT INTO customers (id, name, address, phone_number) VALUES (?, ?, ?, ?);
        ''', (customer_id, name, address, phone))
        conn.commit()
        cursor.execute('''
        INSERT INTO orders (customer_id, description, date, total_amount, clerk_id) VALUES (?, ?, ?, ?, ?);
        ''', (customer_id, description, date, total_amount, userid))
        conn.commit()
    print("Order placed successfully.")

def assign_order_to_delivery(delivery_id):
    cursor.execute('SELECT * FROM employees WHERE role = "delivery" AND id = ?;', (delivery_id,))
    rows = cursor.fetchall()
    if not rows:
        print(f"Deliery employee does not exists: ID {delivery_id}")
        return
    order_id = int(input("Enter order ID to assign to delivery: "))
    cursor.execute('UPDATE orders SET status = "Assigned", delivery_id = ? WHERE id = ?;', (delivery_id, order_id))
    if cursor.rowcount < 1:
        print(f"The order with ID `{order_id}` does not exists")
        return
    conn.commit()
    print("Order assigned to delivery.")

def check_incomplete_orders(userid):
    cursor.execute('SELECT id, customer_id, date, total_amount, status FROM orders WHERE status = "Incomplete" AND clerk_id = ?;', (userid,))
    rows = cursor.fetchall()

    if rows:
        print("YOUR INCOMPLETED ORDERS")
        print(tabulate(rows, headers=['Order ID', 'Customer ID', 'Date', 'Total Amount', 'Status'], tablefmt='grid'))
    else:
        print("No incomplete orders.")

def mark_order_as_completed():
    order_id = int(input("Enter order ID to mark as completed: "))
    cursor.execute('UPDATE orders SET status = "Completed" WHERE id = ?;', (order_id,))
    if cursor.rowcount < 1:
        print(f"The order with ID `{order_id}` does not exists")
        return
    conn.commit()
    print("Order marked as completed.")

def customer_profile():
    try:
        customer_id = int(input("Enter customer ID: "))
    except ValueError as e:
        print(e)
        raise Exception("Wrong customer id type: should be a number, not text")
    cursor.execute('SELECT * FROM customers WHERE id = ?;', (customer_id,))
    customer_data = cursor.fetchone()

    if customer_data:
        print("Customer Profile:")
        print(tabulate([customer_data], headers=['Name', 'Address', 'Phone'], tablefmt='grid'))
    else:
        print("Customer not found.")

def orders_in_specific_day():
    specific_day = input("Enter specific day (YYYY-MM-DD): ")
    cursor.execute('SELECT COUNT(id), SUM(total_amount) FROM orders WHERE date LIKE ?;', (f'{specific_day}%',))
    result = cursor.fetchone()

    if result:
        print(f"Number of orders on {specific_day}: {result[0]}")
        print(f"Total amount of orders on {specific_day}: {result[1]}")
    else:
        print("No orders on the specified day.")

def pending_orders():
    cursor.execute('SELECT id, customer_id, date, total_amount, clerk_id, delivery_id, status FROM orders WHERE status = "Incomplete" OR status = "Assigned";')
    rows = cursor.fetchall()
    info = [row[1::] for row in rows]

    if rows:
        print("Pending Orders:")
        print(tabulate(info, headers=['Customer ID', 'Date', 'Total Amount', 'Clerk ID', 'Delivery ID', 'Status'], tablefmt='grid'))
    else:
        print("No pending orders.")

def total_orders_per_clerk():
    cursor.execute('SELECT clerk_id, COUNT(id) as "Total orders", SUM(total_amount) as "Total amount" FROM orders GROUP BY clerk_id')
    rows = cursor.fetchall()

    if rows:
        print("Total Orders per Clerk:")
        print(tabulate(rows, headers=['Clerk ID', 'Number of orders', 'Summ amount'], tablefmt='grid'))
    else:
        print("No data available.")

def main():
    role, userid = login()
    if role:
        while True:
            if role == 'clerk':
                clerk_menu()
                choice = input("Enter your choice: ")
                if choice == '1':
                    place_order(userid)
                elif choice == '2':
                    delivery_id = int(input("Enter delivery ID to assign: "))
                    assign_order_to_delivery(delivery_id)
                elif choice == '3':
                    check_incomplete_orders(userid)
                else:
                    print("Invalid choice. Try again.")
            elif role == 'delivery':
                delivery_menu()
                choice = input("Enter your choice: ")

                if choice == '1':
                    mark_order_as_completed()
                else:
                    print("Invalid choice. Try again.")
            elif role == 'manager':
                manager_menu()
                choice = input("Enter your choice: ")

                if choice == '1':
                    customer_profile()
                elif choice == '2':
                    orders_in_specific_day()
                elif choice == '3':
                    pending_orders()
                elif choice == '4':
                    total_orders_per_clerk()
                elif choice == '5':
                    filename = input("Enter database name (`employees`, `orders` or `customers`): ")
                    export_to_csv('orders', filename)
                    print(f"Data exported to {filename}")
                else:
                    print("Invalid choice. Try again.")

if __name__ == "__main__":
    main()
