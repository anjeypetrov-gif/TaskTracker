from backend.database import engine, Base
from backend.seed import seed_db

def reseed():
    print("=== Recreating schema and populating commercial database ===")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    seed_db()

if __name__ == "__main__":
    reseed()
