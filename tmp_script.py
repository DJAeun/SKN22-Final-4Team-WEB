import sys

with open(r'c:\Workspaces\SKN22-Final-4Team-WEB\backend\templates\frontend\includes\homepage\_s3_gallery.html', 'r', encoding='utf-8') as f:
    for i, line in enumerate(f):
        if 'data:image' in line:
            print(f'{i+1}: <img src="data:image... ">')
        else:
            print(f'{i+1}: {line.strip()}')
