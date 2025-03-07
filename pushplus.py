import http.client
import json
conn = http.client.HTTPSConnection("www.pushplus.plus")
payload = json.dumps({
   "token": "197bcdaf723444f6a0b48dfd304c3153",
   "title": "测试测试",
   "content": '<img src=http://ssqnlgcpi.hn-bkt.clouddn.com/2025-3-6.png alt="图片无法显示">',
   "topic": "",
   "template": "html"
})
headers = {
   'Content-Type': 'application/json'
}
conn.request("POST", "/send", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))