"""
Generator .env fajla iz env_template.txt.
"""
import shutil
from pathlib import Path


def main():
    """Kreira .env ako ne postoji."""
    env_template = Path("env_template.txt")
    env_file = Path(".env")
    
    if env_file.exists():
        print("⚠ .env file already exists, skipping...")
        return
    
    if not env_template.exists():
        print("✗ env_template.txt not found!")
        return
    
    shutil.copy(env_template, env_file)
    print("✅ Created .env file")
    print("📝 Edit .env and fill in your credentials")


if __name__ == "__main__":
    main()

