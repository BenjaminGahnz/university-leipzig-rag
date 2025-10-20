import chromadb
from typing import Optional

def manage_chroma_db():
    """Manage ChromaDB collections and database"""
    # Initialize client
    client = chromadb.Client()
    
    # List all collections
    collections = client.list_collections()
    if collections:
        print("\nExisting collections:")
        for collection in collections:
            print(f"- {collection.name}")
            try:
                coll = client.get_collection(collection.name)
                print(f"  Documents: {coll.count()}")
            except Exception as e:
                print(f"  Error getting count: {e}")
    else:
        print("\nNo collections found in database.")

    while True:
        print("\nChoose an action:")
        print("1. Delete specific collection")
        print("2. Reset entire database")
        print("3. Show collection details")
        print("4. Exit")
        
        choice = input("\nEnter your choice (1-4): ")
        
        if choice == "1":
            collection_name = input("Enter collection name to delete: ")
            try:
                client.delete_collection(collection_name)
                print(f"\n✓ Collection '{collection_name}' deleted")
            except Exception as e:
                print(f"\nError deleting collection: {e}")
        
        elif choice == "2":
            confirm = input("Are you sure you want to reset the entire database? (y/n): ")
            if confirm.lower() == 'y':
                client.reset()
                print("\n✓ Entire database reset")
            else:
                print("\nDatabase reset cancelled")
        
        elif choice == "3":
            collection_name = input("Enter collection name to inspect: ")
            try:
                collection = client.get_collection(collection_name)
                print(f"\nCollection: {collection_name}")
                print(f"Documents: {collection.count()}")
            except Exception as e:
                print(f"\nError accessing collection: {e}")
        
        elif choice == "4":
            print("\nExiting ChromaDB manager")
            break
        
        else:
            print("\nInvalid choice. Please try again.")

if __name__ == "__main__":
    manage_chroma_db()