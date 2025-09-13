import os

def main():
    print("Hello World des del script youtube_update.py")

    new_title = os.environ.get("NEW_TITLE", None)
    new_description = os.environ.get("NEW_DESCRIPTION", None)

    print(f"NEW_TITLE: {new_title}")
    print(f"NEW_DESCRIPTION: {new_description}")

if __name__ == "__main__":
    main()
