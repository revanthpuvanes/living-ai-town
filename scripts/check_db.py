from app.db.connection import check_database

database, user = check_database()

print(f"Connected database: {database}")
print(f"Connected user: {user}")
print("PostgreSQL connection: OK")
