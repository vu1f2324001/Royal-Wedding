import sqlite3

conn = sqlite3.connect('instance/database.db')
cursor = conn.cursor()
cursor.execute("DELETE FROM user")
conn.commit()
conn.close()