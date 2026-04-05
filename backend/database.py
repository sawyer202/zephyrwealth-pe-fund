import os
from motor.motor_asyncio import AsyncIOMotorClient
from pathlib import Path

MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

DOCUMENTS_DIR = Path("/documents")
