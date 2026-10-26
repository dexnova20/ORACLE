import psycopg

def init_db():
    return psycopg.connect('postgresql://user:pass@localhost:5432/testdb')
