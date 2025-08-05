import json
from pymongo import MongoClient

def insert_to_mongo(chunk_path, mongo_uri="mongodb://localhost:27017"):
    client = MongoClient(mongo_uri)
    db = client.agri_assistant
    col = db.kcc_data

    with open(chunk_path) as f:
        data = json.load(f)
    
    col.insert_many(data)
    print("Inserted", len(data), "documents to MongoDB.")

if __name__ == "__main__":
    insert_to_mongo("chunked.json")
