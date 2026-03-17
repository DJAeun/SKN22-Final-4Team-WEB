
import os
import sys
import subprocess

# Run migrate and capture both stdout and stderr
process = subprocess.Popen(
    [sys.executable, "manage.py", "migrate", "chat"],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    encoding='utf-8'
)
stdout, stderr = process.communicate()

with open("force_migrate_out.txt", "w", encoding='utf-8') as f:
    f.write("STDOUT:\n")
    f.write(stdout)
    f.write("\n\nSTDERR:\n")
    f.write(stderr)
    f.write(f"\nReturn code: {process.returncode}\n")

print(f"Migration completed with return code {process.returncode}")
