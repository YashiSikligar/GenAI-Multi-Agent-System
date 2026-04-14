
import sqlite3

DB_PATH = "support.db"

def get_db_path():
    return DB_PATH

def create_and_seed_database():
    """ here we are creating the SQLite database for customer support system and seeding it with sample data which 
    includes customers and support tickets tables"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    ## create tables if not already there
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            location TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS tickets (
            ticket_id  INTEGER PRIMARY KEY,
            customer_id INTEGER NOT NULL,
            issue  TEXT NOT NULL,
            status  TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        );
    """)

    #check if already seeded (to avoid duplicate seeding)
    cursor.execute("SELECT COUNT(*) FROM customers")
    if cursor.fetchone()[0] > 0:
        conn.close()
        return

    #customer_data
    customers = [
        (1, "Alice Johnson", "alice@example.com","New York"),
        (2,"Bob Smith",  "bob@example.com","Los Angeles"),
        (3, "Carol Williams", "carol@example.com",  "Chicago"),
        (4,"David Brown",  "david@example.com",  "Houston"),
        (5,"Ema Clarke",  "ema@example.com","Seattle"),
        (6,"Frank Lee",  "frank@example.com",  "Philadelphia"),
        (7,"Grace Kim",  "grace@example.com", "San Antonio"),
        (8,"Henry Davis", "henry@example.com", "Dallas"),
        (9,"Iris Chen", "iris@example.com", "San Jose"),
        (10,"Jack Wilson", "jack@example.com", "Austin"),
    ]

    cursor.executemany(
        "INSERT OR IGNORE INTO customers VALUES (?,?,?,?)",
        customers
    )

    #ticket_table/data
    tickets = [
        #index, customer_id, reason, status and date
        (1, 1, "Login issues - cannot access account","open","2024-01-05"),
        (2,1, "Password reset email not received","resolved","2024-02-14"),
        (3,1, "Slow dashboard loading times","in_progress", "2024-03-22"),
        (4,2, "Billing discrepancy on last invoice","open","2024-01-18"),
        (5,2, "Incorrect charge on credit card","closed","2024-02-27"),
        (6,3, "API rate limit exceeded unexpectedly","in_progress", "2024-02-03"),
        (7, 3, "Integration with Slack not working","open","2024-03-10"),
        (8,3, "Missing data after migration","resolved","2024-04-01"),
        (9,4, "Mobile app crashes on launch","open","2024-01-29"),
        (10,4, "Two-factor authentication setup issue","closed","2024-03-05"),
        (11,5, "Unable to invite team members","open","2024-02-11"),
        (12,5, "Email notifications not sending","in_progress", "2024-03-19"),
        (13,5, "Search functionality returning wrong results", "open",     "2024-04-08"),
        (14,6, "Report generation takes too long",  "resolved", "2024-01-22"),
        (15,6, "PDF export formatting broken",  "open",  "2024-03-30"),
        (16,7, "Account locked after multiple attempts", "closed",      "2024-02-06"),
        (17,7, "Data sync failure between devices", "in_progress", "2024-04-15"),
        (18,8, "Cannot delete old records",  "open", "2024-01-13"),
        (19,8, "Dashboard widgets not loading", "resolved", "2024-02-28"),
        (20,8, "Feature request: bulk export",  "closed",   "2024-03-17"),
        (21,9, "Login issues - cannot access account", "in_progress", "2024-02-19"),
        (22,9, "Billing discrepancy on last invoice", "open",  "2024-04-02"),
        (23,10, "Password reset email not received",  "resolved","2024-01-31"),
        (24,10, "API rate limit exceeded unexpectedly", "open",  "2024-03-08"),
        (25,10, "Mobile app crashes on launch", "closed", "2024-04-20"),
    ]
    #insert tickets data into table
    cursor.executemany(
        "INSERT OR IGNORE INTO tickets VALUES (?,?,?,?,?)",
        tickets
    )

    conn.commit()
    conn.close()
    #done seeding db
    print(f"[DB] Database seeded with {len(customers)} customers and {len(tickets)} tickets.")


if __name__ == "__main__":
    create_and_seed_database()
    print("Database ready at:", DB_PATH)