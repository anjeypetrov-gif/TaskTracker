import os
from backend.database import engine, Base
from backend.seed import seed_db

def _confirm_destructive_action():
    """Drops every table — refuse to run against what looks like a non-local
    database without an explicit confirmation. See reset_clean_db.py."""
    if not os.getenv("DATABASE_URL"):
        return
    if os.getenv("CONFIRM_DESTRUCTIVE_RESET") == "yes":
        return
    print("DATABASE_URL is set — this looks like a non-local database.")
    print("This script permanently deletes ALL existing data and reseeds demo data.")
    answer = input("Type YES to permanently wipe this database: ").strip()
    if answer != "YES":
        print("Aborted. No changes made.")
        raise SystemExit(1)

def reseed():
    _confirm_destructive_action()
    print("=== Recreating schema and populating commercial database ===")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    seed_db()

if __name__ == "__main__":
    reseed()
