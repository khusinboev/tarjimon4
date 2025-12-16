#!/bin/bash
# Quick deployment script for server
# Serverda ishlatish uchun

echo "=================================="
echo "🚀 TARJIMON4 QUICK DEPLOY CHECKER"
echo "=================================="
echo ""

# Check Python version
echo "📌 Checking Python version..."
python3 --version || python --version
echo ""

# Check current directory
echo "📁 Current directory:"
pwd
echo ""

# Check required files
echo "🔍 Checking required files..."
files=(
    "src/utils/logger.py"
    "src/utils/rate_limiter.py"
    "src/utils/translation_history.py"
    "src/handlers/users/translate.py"
    "src/handlers/admins/admin.py"
    "main.py"
    "config.py"
)

missing_files=()
for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null)
        echo "✅ $file ($size bytes)"
    else
        echo "❌ $file - MISSING!"
        missing_files+=("$file")
    fi
done
echo ""

# Check if any files are missing
if [ ${#missing_files[@]} -eq 0 ]; then
    echo "✅ All required files present!"
    echo ""
    
    # Test imports
    echo "🔧 Testing imports..."
    python3 -c "from src.utils.logger import translate_logger; print('✅ logger.py OK')" 2>/dev/null || echo "❌ logger.py import failed"
    python3 -c "from src.utils.rate_limiter import rate_limiter; print('✅ rate_limiter.py OK')" 2>/dev/null || echo "❌ rate_limiter.py import failed"
    python3 -c "from src.utils.translation_history import save_translation_history; print('✅ translation_history.py OK')" 2>/dev/null || echo "❌ translation_history.py import failed"
    echo ""
    
    echo "=================================="
    echo "✅ READY TO START BOT!"
    echo "=================================="
    echo ""
    echo "Run: python3 main.py"
    echo "Or background: nohup python3 main.py > bot.log 2>&1 &"
    echo ""
else
    echo "=================================="
    echo "❌ MISSING FILES!"
    echo "=================================="
    echo ""
    echo "Missing files:"
    for file in "${missing_files[@]}"; do
        echo "  - $file"
    done
    echo ""
    echo "Upload these files to server:"
    echo "  scp src/utils/*.py user@server:/path/to/tarjimon4/src/utils/"
    echo ""
    echo "See DEPLOY_SERVER.md for detailed instructions."
    echo ""
fi
