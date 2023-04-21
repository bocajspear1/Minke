

def file_clean(file_path):
    file_path = file_path.replace("\\", "")
    file_path = file_path.replace("/", "")
    while ".." in file_path:
        file_path = file_path.replace("..", "")
    return file_path