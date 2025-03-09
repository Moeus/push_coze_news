import json
import os
from send_solve import get_png
script_dir = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(script_dir,"res","2025-3-9-processed.json"),"r",encoding="utf-8") as file:
    datas=json.load(file)
html_str=""
for data in datas:
    html_str+='''<li><p style="font-size: 16px;"><strong>'''+data["title"]+'''</strong><br/>'''+data["content"]+'''<br/><small style="font-size: 0.618em; color: #999;">'''+"来源:"+data["source"]+'''</small></p></li>'''

html_str='''<ol>'''+html_str+'''</ol>'''
get_png(html_str,2025,3,9)