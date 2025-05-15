from config.connect_db import mydb

def get_all_customers():
    cursor = mydb.cursor(dictionary=True)
    cursor.execute("SELECT * FROM customer")
    return cursor.fetchall()

def get_customer_by_id(customer_id):
    cursor = mydb.cursor(dictionary=True)
    cursor.execute("SELECT * FROM customer WHERE id = %s", (customer_id,))
    return cursor.fetchone()
