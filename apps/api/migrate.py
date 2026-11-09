from dotenv import load_dotenv

from apps.api.config import ROOT, Config
from memory.store import Store

if __name__ == "__main__":
    load_dotenv(ROOT / ".env")
    store = Store(Config().database)
    store.close()
    print("Database migrations are current.")
