from config.connect_db import mydb

def get_all_customers():
    db = mydb() 
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM customers")
    result = cursor.fetchall()
    cursor.close()
    db.close()
    return result

def get_customer_by_id(customer_id):
    db = mydb()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM customers WHERE id = %s", (customer_id,))
    result = cursor.fetchone()
    cursor.close()
    db.close()
    return result

def create_customer(name, address):
    db = mydb()
    cursor = db.cursor()
    cursor.execute("INSERT INTO customers (name, address) VALUES (%s, %s)", (name, address))
    db.commit()
    new_id = cursor.lastrowid
    cursor.close()
    db.close()
    return new_id

def update_customer(customer_id, name, address):
    db = mydb()
    cursor = db.cursor()
    cursor.execute("UPDATE customers SET name = %s, address = %s WHERE id = %s", (name, address, customer_id))
    db.commit()
    affected_rows = cursor.rowcount
    cursor.close()
    db.close()
    return affected_rows

def delete_customer(customer_id):
    db = mydb()
    cursor = db.cursor()
    cursor.execute("DELETE FROM customers WHERE id = %s", (customer_id,))
    db.commit()
    affected_rows = cursor.rowcount
    cursor.close()
    db.close()
    return affected_rows