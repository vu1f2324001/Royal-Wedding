import sqlite3

conn = sqlite3.connect('instance/database.db')
cursor = conn.cursor()

tables = ['user', 'guest', 'wedding']

for table in tables:
    cursor.execute(f'DELETE FROM {table};')

conn.commit()
conn.close()

print("All data deleted from user, guest, and wedding tables.")





import sqlite3

# database ला connect होतो
conn = sqlite3.connect('instance/database.db')
cursor = conn.cursor()

# टेबल drop करतो
tables = ['_alembic_tmp_guest', 'alembic_version']

for table in tables:
    cursor.execute(f'DROP TABLE IF EXISTS {table};')
    print(f"Table '{table}' successfully dropped.")

conn.commit()
conn.close()