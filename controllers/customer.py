from config.connect_db import mydb
from mysql.connector import Error
mycursor = mydb.cursor()

def create(val):
    try:
        sql = "INSERT INTO customers (name, address) VALUES (%s, %s)"
        mycursor.executemany(sql, val)
        return
    except Error as e:
        print(e)
    
def get_all(self):
    try:
        sql = "SELECT * FROM customers"
        self.mycursor.execute(sql)
        result = self.mycursor.fetchall()
        return result
    except Error as e:
        print(e)
        return []