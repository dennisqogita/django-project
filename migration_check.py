import sys

if __name__ == "__main__":
    print(f"Argument length: {len(sys.argv)}")
    migration_files = sys.argv[1:]
    print(migration_files)
