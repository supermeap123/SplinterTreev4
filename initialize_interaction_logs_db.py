import sqlite3

def initialize_db():
    with open('databases/schema.sql', 'r') as f:
        schema_sql = f.read()

    conn = sqlite3.connect('databases/interaction_logs.db')
    cursor = conn.cursor()

    cursor.executescript(schema_sql)

    conn.commit()
    conn.close()
    print('Database initialized successfully.')

if __name__ == '__main__':
    initialize_db()
