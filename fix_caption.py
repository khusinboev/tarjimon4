with open(r'G:\my\projects\python\tarjimon4\src\handlers\users\translate.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

with open(r'G:\my\projects\python\tarjimon4\src\handlers\users\translate.py', 'w', encoding='utf-8') as f:
    f.writelines(lines[:359])

print("✅ Old caption handler removed successfully!")
