import os

def print_directory_tree(startpath, max_depth=2):
    for root, dirs, files in os.walk(startpath):
        level = root.replace(startpath, '').count(os.sep)
        if level < max_depth:
            indent = ' ' * 4 * level
            print(f"{indent}{os.path.basename(root)}/")
            subindent = ' ' * 4 * (level + 1)
            for f in files:
                print(f"{subindent}{f}")
        # Stop further traversing if we've reached the max depth
        if level >= max_depth:
            dirs[:] = []  # This prevents further descending into subdirectories

if __name__ == "__main__":
    # Cambia '.' por la ruta a tu proyecto si no estás en la raíz del mismo
    print_directory_tree(".", max_depth=2)
