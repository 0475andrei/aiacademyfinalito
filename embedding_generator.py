import os
import json
from document_chunker import get_document_chunks
from embeddings_client import EmbeddingsClient

def generate_and_save_embeddings(output_file="embeddings.json"):
    
    existing_embeddings = {}
    if os.path.exists(output_file):
        print(f"Found existing '{output_file}'. Loading for incremental update...")
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Map the exact text content to its existing embedding vector
                existing_embeddings = {item["content"]: item["embedding"] for item in data}
        except json.JSONDecodeError:
            print("Existing embeddings file is corrupted. Starting fresh.")

    
    print("Generating new embeddings... This might take a moment.")
    
    # Load all chunks generated in the previous exercise
    chunks = get_document_chunks()
    
    # Initialize the client (which uses the endpoint in config.py)
    client = EmbeddingsClient()
    
    embedded_chunks = []
    
    # 2. Generate an embedding for each chunk
    for chunk in chunks:
        # Extract the text content to embed
        text_to_embed = chunk["content"]
        
        try:
            
            if text_to_embed in existing_embeddings:
                embedding_vector = existing_embeddings[text_to_embed]
            else:
                embedding_vector = client.get_embedding(text_to_embed)
                print(f"API CALL: Generated NEW embedding for {chunk['document_id']} (Chunk {chunk['chunk_index']})")
                
            # 3. Format the result
            embedded_chunk = {
                "document_id": chunk["document_id"],
                "chunk_index": chunk["chunk_index"],
                "content": chunk["content"],
                "embedding": embedding_vector
            }
            embedded_chunks.append(embedded_chunk)
            
            print(f"Successfully embedded chunk {chunk['chunk_index']} from {chunk['document_id']}")
        except Exception as e:
            print(f"Failed to embed chunk {chunk['chunk_index']}: {e}")

    # 4. Save the result into a JSON file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(embedded_chunks, f, indent=4)
        
    print(f"\nSaved {len(embedded_chunks)} embeddings to '{output_file}'.")


if __name__ == "__main__":
    generate_and_save_embeddings()
