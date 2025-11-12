#!/usr/bin/env python3
"""
Extract pure HTML and rebuild templates with external CSS only
"""

import re

def extract_pure_html(content):
    """Extract only HTML between {% block content %} and {% endblock %}"""
    match = re.search(r'{% block content %}(.*?){% endblock %}', content, re.DOTALL)
    if match:
        html_content = match.group(1)
        # Remove all CSS (anything between /* and */ or lines with CSS syntax)
        html_content = re.sub(r'/\*.*?\*/', '', html_content, flags=re.DOTALL)
        return html_content.strip()
    return ""

def build_clean_template(title, subtitle, html_content, css_file, script_content=""):
    """Build a clean template"""
    template = '{% extends "base.html" %}\n\n'
    template += f'{{% block title %}}{title}{{% endblock %}}\n\n'
    template += '{% block styles %}\n'
    template += f'    <link rel="stylesheet" href="{{{{ url_for(\'static\', filename=\'{css_file}\') }}}}">\n'
    template += '{% endblock %}\n\n'
    template += '{% block content %}\n'
    template += html_content + '\n'
    template += '{% endblock %}\n\n'
    template += '{% block scripts %}\n'
    template += '<script>\n'
    template += script_content
    template += '\n</script>\n'
    template += '{% endblock %}\n'
    return template

# Read and process files
base_path = "c:\\Users\\wikiepeidia\\OneDrive - caugiay.edu.vn\\bài tập\\usth\\GEN14\\GROUP project\\Group-project-AI-ML"

files = {
    'ui/templates/workspace.html': {
        'title': 'Workflows - Workflow Automation for Retail',
        'css': 'workspace.css',
    },
    'ui/templates/workspace_builder.html': {
        'title': 'Workflow Builder - Workflow Automation for Retail',
        'css': 'builder.css',
    },
    'ui/templates/scenarios.html': {
        'title': 'Automation Scenarios - Workflow Automation for Retail',
        'css': 'scenarios.css',
    },
}

for file_path, config in files.items():
    full_path = f"{base_path}\\{file_path}"
    print(f"Extracting {file_path}...")
    
    with open(full_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract pure HTML
    html = extract_pure_html(content)
    
    # Build clean template
    clean = build_clean_template(config['title'], '', html, config['css'])
    
    # Write back
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(clean)
    
    print(f"  ✓ Done")

print("\n✓ All templates cleaned!")