import json
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import os

def load_json_files(root_dir, target_filename, save_filename):
    json_data_list = []

    # Traverse directories and subdirectories
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename == target_filename:
                file_path = os.path.join(dirpath, filename)
                save_path = os.path.join(dirpath, save_filename)
                json_data_list.append((file_path, save_path))
    return json_data_list

def load_data(file_path):
    with open(file_path, 'r') as f:
        return json.load(f)

def find_cluster_center(cluster_indices, embeddings):
    # Find all embeddings in the cluster
    cluster_embeddings = np.array([embeddings[i] for i in cluster_indices])
    center_embedding = np.mean(cluster_embeddings, axis=0)
    # Find the index of the entry closest to the center vector
    distances = np.linalg.norm(cluster_embeddings - center_embedding, axis=1)
    center_index = np.argmin(distances)
    # Return the original dataset index of the center entry
    return cluster_indices[center_index]

def create_embeddings(data):
    model = SentenceTransformer('all-MiniLM-L6-v2') # could be replaced by other models
    embeddings = []
    for item in data:
        embeddings.append(model.encode(item['input']))
    return np.array(embeddings)

def cluster_similar_items(embeddings, threshold=0.9): # threshold could be adjusted
    clusters = {}
    for i, emb in enumerate(embeddings):
        max_sim = 0
        best_cluster = None
        for j, other_emb in enumerate(embeddings):
            if i != j:
                sim = cosine_similarity(emb.reshape(1,-1), other_emb.reshape(1,-1))[0][0]
                if sim > max_sim:
                    max_sim = sim
                    best_cluster = j
        if max_sim >= threshold:
            clusters[i] = best_cluster
    
    return {k: v for k, v in clusters.items() if v != k}

def process_data(input_file, output_file):
    data = load_data(input_file)
    
    # Create embeddings
    embeddings = create_embeddings(data)
    
    # Cluster similar items
    clusters = cluster_similar_items(embeddings)
    
    # Group original data based on clustering results
    grouped_data = {}
    for i, item in enumerate(data):
        cluster_id = clusters.get(i, i)
        if cluster_id not in grouped_data:
            grouped_data[cluster_id] = []
        grouped_data[cluster_id].append(i)  # Use index instead of storing entries directly
    
    # Retain the center entry of each cluster
    deduplicated_data = []
    for cluster_id, cluster_indices in grouped_data.items():
        if len(cluster_indices) > 1:
            center_index = find_cluster_center(cluster_indices, embeddings)
            deduplicated_data.append(data[center_index])
        else:
            deduplicated_data.append(data[cluster_indices[0]])
    
    # Write processed data to file
    with open(output_file, 'w') as f:
        json.dump(deduplicated_data, f, ensure_ascii=False, indent=4)

# Usage
total = load_json_files('output', 'tuning_set.json', 'deduplicated_inputs.json')
for t in total:
    process_data(t[0], t[1])
