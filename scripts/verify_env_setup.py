#!/usr/bin/env python3
"""
Environment Setup Verification Script

Verifies that environment variables are properly configured
and that no secrets are committed to git.
"""

import os
import sys
from pathlib import Path
import subprocess

# Colors for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_success(message):
    print(f"{GREEN}✓{RESET} {message}")

def print_error(message):
    print(f"{RED}✗{RESET} {message}")

def print_warning(message):
    print(f"{YELLOW}⚠{RESET} {message}")

def print_info(message):
    print(f"{BLUE}ℹ{RESET} {message}")

def check_file_exists(filepath, required=True):
    """Check if a file exists"""
    if Path(filepath).exists():
        print_success(f"Found: {filepath}")
        return True
    else:
        if required:
            print_error(f"Missing: {filepath}")
        else:
            print_warning(f"Optional file not found: {filepath}")
        return False

def check_gitignore():
    """Verify .env is in .gitignore"""
    print_info("\n=== Checking .gitignore ===")
    
    if not check_file_exists(".gitignore"):
        print_error(".gitignore file is missing!")
        return False
    
    with open(".gitignore", "r") as f:
        content = f.read()
    
    if ".env" in content:
        print_success(".env is in .gitignore")
        return True
    else:
        print_error(".env is NOT in .gitignore - secrets may be committed!")
        return False

def check_env_file():
    """Check if .env file exists and has content"""
    print_info("\n=== Checking .env file ===")
    
    if not Path(".env").exists():
        print_warning(".env file not found")
        print_info("Run: cp .env.example .env")
        return False
    
    print_success(".env file exists")
    
    # Check if .env has content
    with open(".env", "r") as f:
        lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    
    if len(lines) == 0:
        print_warning(".env file is empty")
        return False
    
    print_success(f".env file has {len(lines)} configuration lines")
    return True

def check_env_variables():
    """Check critical environment variables"""
    print_info("\n=== Checking Environment Variables ===")
    
    critical_vars = {
        "JWT_SECRET_KEY": "JWT authentication secret",
        "DATABASE_URL": "Database connection string",
    }
    
    optional_vars = {
        "ENCRYPTION_KEY": "Encryption key for API keys",
        "BYBIT_API_KEY": "Bybit API key",
        "BINANCE_API_KEY": "Binance API key",
        "CRYPTOPANIC_API_KEY": "CryptoPanic API key",
    }
    
    all_ok = True
    
    # Check critical variables
    for var, description in critical_vars.items():
        value = os.getenv(var)
        if value:
            # Check if it's still the default placeholder
            if "your-" in value.lower() or "change-in-production" in value.lower():
                print_warning(f"{var}: Set but using placeholder value")
                print_info(f"  → {description}")
                all_ok = False
            else:
                print_success(f"{var}: Configured")
        else:
            print_error(f"{var}: Not set")
            print_info(f"  → {description}")
            all_ok = False
    
    # Check optional variables
    print_info("\nOptional variables:")
    for var, description in optional_vars.items():
        value = os.getenv(var)
        if value and "your-" not in value.lower():
            print_success(f"{var}: Configured")
        else:
            print_warning(f"{var}: Not configured")
            print_info(f"  → {description}")
    
    return all_ok

def check_git_status():
    """Check if .env is tracked by git"""
    print_info("\n=== Checking Git Status ===")
    
    try:
        # Check if .env is tracked
        result = subprocess.run(
            ["git", "ls-files", ".env"],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.stdout.strip():
            print_error(".env is tracked by git - SECURITY RISK!")
            print_info("Run: git rm --cached .env")
            return False
        else:
            print_success(".env is not tracked by git")
            return True
    except FileNotFoundError:
        print_warning("Git not found - skipping git checks")
        return True

def check_secret_strength():
    """Check if JWT secret is strong enough"""
    print_info("\n=== Checking Secret Strength ===")
    
    jwt_secret = os.getenv("JWT_SECRET_KEY", "")
    
    if not jwt_secret:
        print_error("JWT_SECRET_KEY not set")
        return False
    
    if len(jwt_secret) < 32:
        print_warning(f"JWT_SECRET_KEY is short ({len(jwt_secret)} chars) - recommend 32+")
        return False
    
    if jwt_secret == "your-secret-key-here-change-in-production":
        print_error("JWT_SECRET_KEY is using default placeholder - MUST CHANGE!")
        return False
    
    print_success(f"JWT_SECRET_KEY length: {len(jwt_secret)} characters")
    return True

def check_database():
    """Check database configuration"""
    print_info("\n=== Checking Database ===")
    
    db_url = os.getenv("DATABASE_URL", "sqlite:///./db/trading_system.db")
    print_info(f"Database URL: {db_url}")
    
    if "sqlite:///" in db_url:
        # Extract path from SQLite URL
        db_path = db_url.replace("sqlite:///", "")
        if db_path.startswith("./"):
            db_path = db_path[2:]
        
        db_dir = Path(db_path).parent
        
        if not db_dir.exists():
            print_warning(f"Database directory does not exist: {db_dir}")
            print_info(f"Run: mkdir -p {db_dir}")
            return False
        
        print_success(f"Database directory exists: {db_dir}")
        return True
    else:
        print_info("Using non-SQLite database")
        return True

def generate_keys():
    """Generate secure keys for user"""
    print_info("\n=== Key Generation ===")
    
    try:
        import secrets
        jwt_key = secrets.token_urlsafe(32)
        print_info("\nGenerated JWT_SECRET_KEY:")
        print(f"  {jwt_key}")
    except Exception as e:
        print_error(f"Failed to generate JWT key: {e}")
    
    try:
        from cryptography.fernet import Fernet
        encryption_key = Fernet.generate_key().decode()
        print_info("\nGenerated ENCRYPTION_KEY:")
        print(f"  {encryption_key}")
    except Exception as e:
        print_error(f"Failed to generate encryption key: {e}")
        print_info("Install: pip install cryptography")

def main():
    """Main verification function"""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}OpenClaw Trading Dashboard - Environment Setup Verification{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")
    
    # Change to project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    os.chdir(project_root)
    
    checks = []
    
    # Run all checks
    checks.append(("Files", check_file_exists(".env.example")))
    checks.append(("Gitignore", check_gitignore()))
    checks.append(("Env File", check_env_file()))
    checks.append(("Git Status", check_git_status()))
    
    # Load .env file if it exists
    if Path(".env").exists():
        from dotenv import load_dotenv
        load_dotenv()
        checks.append(("Environment Variables", check_env_variables()))
        checks.append(("Secret Strength", check_secret_strength()))
    
    checks.append(("Database", check_database()))
    
    # Summary
    print_info("\n=== Summary ===")
    passed = sum(1 for _, result in checks if result)
    total = len(checks)
    
    print(f"\nPassed: {passed}/{total} checks")
    
    if passed == total:
        print_success("\n✓ All checks passed! Environment is properly configured.")
        return 0
    else:
        print_warning(f"\n⚠ {total - passed} check(s) failed. Please review the issues above.")
        
        # Offer to generate keys
        if not os.getenv("JWT_SECRET_KEY") or not os.getenv("ENCRYPTION_KEY"):
            print_info("\nWould you like to generate secure keys? (y/n)")
            response = input().strip().lower()
            if response == 'y':
                generate_keys()
        
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print_warning("\n\nVerification cancelled by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
