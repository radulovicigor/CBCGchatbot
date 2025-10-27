"""
Validation script - proverava da li je setup kompletno.
"""
import os
import sys
from pathlib import Path


def check_file_exists(filepath: str, required: bool = True) -> bool:
    """Provera postojanja fajla."""
    exists = Path(filepath).exists()
    status = "✓" if exists else ("✗" if required else "⚠")
    print(f"{status} {filepath}")
    return exists


def check_env_var(var: str) -> bool:
    """Provera environment variable."""
    value = os.getenv(var)
    if not value or value == "..." or value.startswith("<"):
        print(f"✗ {var} nije konfigurisan")
        return False
    print(f"✓ {var}")
    return True


def main():
    """Glavna validacija."""
    print("🔍 Validacija setup-a...\n")
    
    errors = []
    warnings = []
    
    # 1. Fajlovi
    print("1. Provera fajlova:")
    required_files = [
        "README.md",
        "START_HERE.md",
        "env_template.txt",
        "setup.py",
        "apps/api/main.py",
        "apps/functions/scrape_timer/scraper.py",
        "apps/ingest/push_to_search.py",
        "public/widget.html",
    ]
    
    for f in required_files:
        if not check_file_exists(f):
            errors.append(f"Missing required file: {f}")
    
    # 2. .env fajl
    print("\n2. Provera .env:")
    if not Path(".env").exists():
        errors.append(".env file ne postoji - pokreni: python scripts/create_env.py")
    else:
        print("✓ .env postoji")
    
    # 3. Dependencies
    print("\n3. Provera dependencies:")
    try:
        import fastapi
        import openai
        import azure.search.documents
        print("✓ Core dependencies su instalirane")
    except ImportError as e:
        errors.append(f"Missing dependencies: {e}")
    
    # 4. Python version
    print("\n4. Python version:")
    version = sys.version_info
    if version.major == 3 and version.minor >= 11:
        print(f"✓ Python {version.major}.{version.minor}.{version.micro}")
    else:
        warnings.append(f"Python {version.major}.{version.minor} - preporuceno 3.11+")
    
    # 5. Virtual environment
    print("\n5. Virtual environment:")
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✓ Virtual environment je aktiviran")
    else:
        warnings.append("Virtual environment nije aktiviran")
    
    # Summary
    print("\n" + "="*50)
    if errors:
        print("❌ ERRORI PRONADENI:")
        for e in errors:
            print(f"  - {e}")
    else:
        print("✅ SVE REQUIRED PROVERE: OK")
    
    if warnings:
        print("\n⚠ UPOZORENJA:")
        for w in warnings:
            print(f"  - {w}")
    
    print("="*50)
    
    if errors:
        print("\nPopravi greške i pokreni ponovo.")
        return 1
    else:
        print("\nSetup je validan! Možeš nastaviti sa deployment-om.")
        return 0


if __name__ == "__main__":
    sys.exit(main())

