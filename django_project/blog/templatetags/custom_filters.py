import re
from django import template
from markdownx.utils import markdownify

register = template.Library()

@register.filter
def show_markdown(text):
    html_content = markdownify(text)
    # Adjust the max-width for images
#    html_content = re.sub(r'<img ', r'<img style="max-width: 100%; height: auto; display: block; margin: 20px auto;" ', html_content)
    # Adjust the max-width for images
    html_content = re.sub(r'<img ', r'<img style="max-width: 100%; height: auto; display: block; margin: 20px auto;" ', html_content)

    # Adjust tables
#    html_content = re.sub(r'<table ', r'<table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;" ', html_content)
#    html_content = re.sub(r'<th ', r'<th style="padding: 8px; border: 1px solid #ddd; background-color: #f4f4f4;" ', html_content)
#    html_content = re.sub(r'<td ', r'<td style="padding: 8px; border: 1px solid #ddd; text-align: left;" ', html_content)

    # Adjust code blocks
#    html_content = re.sub(r'<pre ', r'<pre style="background-color: #f5f5f5; padding: 15px; overflow-x: auto;" ', html_content)
#    html_content = re.sub(r'<code ', r'<code style="background-color: #f5f5f5; padding: 2px 5px; border-radius: 4px;" ', html_content)

    # Bold text
#    html_content = re.sub(r'<b>', r'<b style="font-weight: bold;">', html_content)

    # Headers
#    html_content = re.sub(r'<h1>', r'<h1 style="font-size: 2em; color: #444;">', html_content)
#    html_content = re.sub(r'<h2>', r'<h2 style="font-size: 1.75em; color: #444;">', html_content)
#    html_content = re.sub(r'<h3>', r'<h3 style="font-size: 1.5em; color: #444;">', html_content)

    return html_content

