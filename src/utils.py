import os

def get_user_ids(filename):
    ids = []
    with open(filename, "r") as f:
        lines = f.readlines()
        for line in lines:
            ids.append(line.strip())
    return ids

def get_newest_file_by_name(folder_path):
    # List all files (not directories)
    files = [f for f in os.listdir(folder_path)
             if os.path.isfile(os.path.join(folder_path, f)) and '.png' in  os.path.join(folder_path, f)]

    if not files:
        return None  # No files found
    
    files.sort(reverse=False)
    
    return files[-1]
