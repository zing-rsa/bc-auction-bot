import os
from pymongo import MongoClient

MONGO_URL = os.getenv('MONGO_URL')

client = MongoClient(MONGO_URL)
db=client.bensdb
mongo_auctions = db.auctions
db_results = mongo_auctions.find_one({})

print(db_results)