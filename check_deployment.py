#!/usr/bin/env python3
"""
Server deployment checker
Serverda kerakli fayllar borligini tekshiradi
"""

import os
import sys
from pathlib import Path

# Colors for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'

def check_file(filepath, required=True):
    """Fayl mavjudligini tekshirish"""
    if os.path.exists(filepath):
        size = os.path.getsize(filepath)
        print(f"{GREEN}✅ {filepath} ({size} bytes){RESET}")
        return True
    else:
        if required:
            print(f"{RED}❌ {filepath} - TOPILMADI!{RESET}")
        else:
            print(f"{YELLOW}⚠️  {filepath} - mavjud emas (optional){RESET}")
        return False

def check_import(module_path):
    """Import ishlashini tekshirish"""
    try:
        __import__(module_path)
        print(f"{GREEN}✅ Import OK: {module_path}{RESET}")
        return True
    except ImportError as e:
        print(f"{RED}❌ Import XATO: {module_path} - {e}{RESET}")
        return False
    except Exception as e:
        print(f"{YELLOW}⚠️  Import Warning: {module_path} - {e}{RESET}")
        return False

def main():
    print("=" * 60)
    print("🔍 TARJIMON4 SERVER DEPLOYMENT CHECKER")
    print("=" * 60)
    print()
    
    all_ok = True
    
    # 1. Check required utility files
    print("📁 Checking utility modules...")
    utils_files = [
        'src/utils/__init__.py',
        'src/utils/logger.py',
        'src/utils/rate_limiter.py',
        'src/utils/translation_history.py'
    ]
    
    for file in utils_files:
        if not check_file(file, required=True):
            all_ok = False
    print()
    
    # 2. Check main handler files
    print("📁 Checking handler files...")
    handler_files = [
        'src/handlers/users/translate.py',
        'src/handlers/admins/admin.py'
    ]
    
    for file in handler_files:
        if not check_file(file, required=True):
            all_ok = False
    print()
    
    # 3. Check main files
    print("📁 Checking main files...")
    main_files = [
        'main.py',
        'config.py',
        'requirements.txt'
    ]
    
    for file in main_files:
        if not check_file(file, required=True):
            all_ok = False
    print()
    
    # 4. Check optional documentation
    print("📁 Checking documentation (optional)...")
    doc_files = [
        'README.md',
        'CHANGELOG.md',
        'IMPLEMENTATION_GUIDE.md',
        'DEPLOY_SERVER.md'
    ]
    
    for file in doc_files:
        check_file(file, required=False)
    print()
    
    # 5. Check imports
    print("🔧 Checking Python imports...")
    imports = [
        'aiogram',
        'psycopg2',
        'deep_translator',
        'googletrans',
        'src.utils.logger',
        'src.utils.rate_limiter',
        'src.utils.translation_history',
        'src.handlers.users.translate',
        'src.handlers.admins.admin'
    ]
    
    for imp in imports:
        if not check_import(imp):
            if imp.startswith('src.utils'):
                all_ok = False
    print()
    
    # 6. Check logs directory
    print("📊 Checking logs directory...")
    logs_dir = 'logs'
    if os.path.exists(logs_dir):
        print(f"{GREEN}✅ {logs_dir}/ directory exists{RESET}")
        log_files = os.listdir(logs_dir)
        if log_files:
            print(f"{GREEN}   Found {len(log_files)} log files{RESET}")
            for f in log_files[:5]:  # Show first 5
                print(f"   - {f}")
        else:
            print(f"{YELLOW}   No log files yet (will be created on first run){RESET}")
    else:
        print(f"{YELLOW}⚠️  {logs_dir}/ directory not found (will be created automatically){RESET}")
    print()
    
    # Final result
    print("=" * 60)
    if all_ok:
        print(f"{GREEN}✅ ALL CHECKS PASSED!{RESET}")
        print(f"{GREEN}   Bot ready to run: python main.py{RESET}")
        return 0
    else:
        print(f"{RED}❌ SOME CHECKS FAILED!{RESET}")
        print(f"{YELLOW}   Missing files need to be uploaded to server.{RESET}")
        print(f"{YELLOW}   See DEPLOY_SERVER.md for instructions.{RESET}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
