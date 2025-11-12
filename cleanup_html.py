#!/usr/bin/env python3
"""
Clean HTML templates: Remove ALL embedded CSS and JS, add external links only
"""

import re
import os

def clean_html_file(filepath, css_files):
    """
    Remove all embedded CSS/JS and add external links
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remove all <style>...</style> blocks (including content)
    content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove all <script>...</script> blocks
    content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL | re.IGNORECASE)
    
    # Remove floating CSS (lines between {% endblock %} styles and {% block content %})
    # This handles raw CSS that's outside of <style> tags
    content = re.sub(
        r'({% endblock %}\s*)(\n\s*:root\s*\{.*?\n\s*\})',
        r'\1',
        content,
        flags=re.DOTALL | re.IGNORECASE
    )
    
    # Remove any remaining CSS rules that float in the HTML
    lines = content.split('\n')
    cleaned_lines = []
    in_css_block = False
    brace_count = 0
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Detect start of CSS blocks (look for CSS patterns: selector {, :root {, @media {, etc)
        if re.match(r'^(:|@|\.|\[|[a-z]|--).*\{|^--[a-z-]+:|^:[a-z-]+', stripped) and not in_css_block:
            in_css_block = True
            brace_count = line.count('{') - line.count('}')
            continue
        
        # If in CSS block, count braces
        if in_css_block:
            brace_count += line.count('{') - line.count('}')
            if brace_count <= 0:
                in_css_block = False
                brace_count = 0
            continue
        
        # Keep lines that are not CSS
        if stripped:  # Skip empty lines during first pass
            cleaned_lines.append(line)
        elif cleaned_lines and cleaned_lines[-1].strip():  # Keep single empty lines after content
            cleaned_lines.append(line)
    
    # Clean up excessive empty lines
    content = '\n'.join(cleaned_lines)
    content = re.sub(r'\n\n\n+', '\n\n', content)
    
    # Add CSS links to {% block styles %}
    css_links = '\n    '.join(f'<link rel="stylesheet" href="{{{{ url_for(\'static\', filename=\'{css_file}\') }}}}">' for css_file in css_files)
    content = re.sub(
        r'{% block styles %}[^}]*{% endblock %}',
        '{% block styles %}\n    ' + css_links + '\n{% endblock %}',
        content,
        flags=re.DOTALL
    )
    
    return content

# Files to process
files_config = {
    'ui/templates/workspace.html': ['workspace.css'],
    'ui/templates/workspace_builder.html': ['builder.css'],
    'ui/templates/scenarios.html': ['scenarios.css'],
}

base_path = "c:\\Users\\wikiepeidia\\OneDrive - caugiay.edu.vn\\bài tập\\usth\\GEN14\\GROUP project\\Group-project-AI-ML"

for file_path, css_files in files_config.items():
    full_path = os.path.join(base_path, file_path)
    print(f"Processing {file_path}...")
    
    cleaned = clean_html_file(full_path, css_files)
    
    with open(full_path, 'w', encoding='utf-8') as f:
        f.write(cleaned)
    
    print(f"  ✓ Cleaned and saved")

print("\n✓ All files cleaned successfully!")
