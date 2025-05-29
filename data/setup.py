from database import DatabaseManager

def setup_database():
    """Initialize the database with all tables."""
    db = DatabaseManager()
    db.create_tables()
    print("Database setup completed!")

if __name__ == "__main__":
    setup_database()