import os

html_path = r"c:\Workspaces\SKN22-Final-4Team-WEB\backend\templates\frontend\includes\homepage\_s2_profile.html"
with open(html_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "data:image" in line:
        lines[i] = '      <img src="{% static \'images/hari_image6.png\' %}" alt="Hari Profile Image" style="width:100%; height:100%; object-fit:cover; display:block;">\n'

with open(html_path, "w", encoding="utf-8") as f:
    f.writelines(lines)
