import os

def print_tree(root, prefix=""):
    entries = sorted(os.listdir(root))
    for index, entry in enumerate(entries):
        path = os.path.join(root, entry)
        connector = "└── " if index == len(entries) - 1 else "├── "
        print(prefix + connector + entry)
        if os.path.isdir(path):
            extension = "    " if index == len(entries) - 1 else "│   "
            print_tree(path, prefix + extension)

if __name__ == "__main__":
    root_path = os.path.abspath(".")  # current directory
    print("📁 Struktur Folder Proyek\n")
    print(os.path.basename(root_path))
    print_tree(root_path)
