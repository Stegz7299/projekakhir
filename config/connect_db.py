import mysql.connector

def mydb():
    mydb = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="projek"
    )
    return mydb