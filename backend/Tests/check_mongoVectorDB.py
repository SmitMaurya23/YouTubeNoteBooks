# check_mongodb.py
import os
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure

load_dotenv()

try:
    mongo_uri = os.getenv("MONGODB_URI")
    if not mongo_uri:
        raise ValueError("MONGODB_URI not set in .env file.")

    print("Attempting to connect to MongoDB Atlas...")
    client = MongoClient(mongo_uri)

    # The ping command is cheap and does not require auth.
    # It sends a command to the database that returns with a success message
    # if the connection is established.
    client.admin.command('ping')
    print("MongoDB Atlas connection successful!")

    # Optionally, try to list database names to ensure authentication
    # This requires the user to have read access to databases
    print("Listing database names (requires appropriate user privileges)...")
    db_names = client.list_database_names()
    print(f"Successfully listed databases: {db_names}")

    client.close()
    print("MongoDB connection closed.")

except ConnectionFailure as e:
    print(f"MongoDB connection failed: {e}")
    print("Please check your MONGODB_URI, network access (IP whitelist), and cluster status.")
except OperationFailure as e:
    print(f"MongoDB operation failed (likely authentication/authorization error): {e}")
    print("Please ensure your database username and password in MONGODB_URI are correct, and the user has 'Read and write to any database' or similar privileges.")
except ValueError as e:
    print(f"Configuration error: {e}")
except Exception as e:
    print(f"An unexpected error occurred during MongoDB setup check: {e}")