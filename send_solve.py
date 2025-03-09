"""
获取新闻卡片
发送卡片至七牛云 云对象存储库
使用pushplus推送
"""
import requests
import json
import os
import http.client
from qiniu import Auth, put_file, etag
import logging
root_logger = logging.getLogger('root')
# 清除原有的处理器配置
for handler in root_logger.handlers[:]:
    root_logger.removeHandler(handler)
# 配置日志
root_logger.setLevel(logging.INFO)
#创建格式化器,准备被日志处理器使用
formatter = logging.Formatter(
    fmt='[%(name)s][%(levelname)s][%(asctime)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
# 创建文件处理器，将日志写入 working.log 文件，写入模式为追加，编码使用utf-8
file_handler = logging.FileHandler('working.log', mode='a',encoding='utf-8')
file_handler.setLevel(logging.WARNING)
file_handler.setFormatter(formatter)
root_logger.addHandler(file_handler)
# 创建控制台处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)
root_logger.addHandler(console_handler)

def get_png(content, year, month, day):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    try:
        root_logger.info("获取新闻卡片配置")
        with open(os.path.join(script_dir, "config/liuguang_api.json"), 'r', encoding='utf-8') as file:
            data = json.load(file)
        root_logger.info("成功获取新闻卡片配置")
    except Exception as e:
        root_logger.error("读取新闻卡片配置出错")
    target_url = "https://fireflycard-api.302ai.cn/api/saveImg"
    data["form"]["content"] = content
    data["form"]["title"] = f"<p>👋{year}-{month}-{day}热点新闻😺💕</p>"
    data["form"]["textCount"] = len(content)
    root_logger.info(f"总字数：{len(content)}")
    headers = {
        'Content-Type': 'application/json'
    }
    try:
        root_logger.info("正在生成新闻卡片PNG图像")
        response = requests.post(target_url, json=data, headers=headers, timeout=100, verify=False)
        response.raise_for_status()
        os.chdir(script_dir)
        file_path = f'res/{year}-{month}-{day}.png'
        with open(file_path, 'wb') as file:
            file.write(response.content)
        root_logger.info(f"新闻卡片获取成功已成功！")
        root_logger.info(f"新闻卡片已保存到 {os.path.join(script_dir, file_path)}")
        return os.path.join(script_dir, file_path)
    except requests.exceptions.HTTPError as http_err:
        root_logger.error(f'获取新闻卡片时 HTTP 错误发生: {http_err}')
    except requests.exceptions.ConnectionError as conn_err:
        root_logger.error(f'连接错误发生: {conn_err}')
    except requests.exceptions.Timeout as timeout_err:
        root_logger.error(f'请求超时: {timeout_err}')
    except requests.exceptions.RequestException as req_err:
        root_logger.error(f'请求发生未知错误: {req_err}')
    return 0


#上传到七牛对象存储库
def qiniu_push_file(year,month,day,img_path):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    try:
        root_logger.info("获取对象存储库配置")
        with open(os.path.join(script_dir, "config/qiniu.json"), 'r', encoding='utf-8') as file:
            qiniu_config = json.load(file)
            root_logger.info("成功获取对象存储库配置")
    except Exception as e:
        root_logger.error("读取对象存储库配置出错")
    q = Auth(*qiniu_config.values())
    #检查是否以及存在
    base_url="http://ssqnlgcpi.hn-bkt.clouddn.com/"
    #要上传的空间
    bucket_name = 'moeus-news-res'
    #上传后保存的文件名
    key = f'{year}-{month}-{day}.res'
    #生成上传 Token，可以指定过期时间等
    token = q.upload_token(bucket_name, key, 3600)
    #要上传文件的本地路径
    localfile = img_path
    ret, info = put_file(token, key, localfile, version='v2')
    root_logger.info(info)
    assert ret['key'] == key
    assert ret['hash'] == etag(localfile)
    root_logger.info(ret)
    root_logger.info(base_url + key)
    return base_url+key

def pushplus(token,title,img_url,topic=""):
    conn = http.client.HTTPSConnection("www.pushplus.plus")
    root_logger.info("正在向用户推送新闻" if topic == "" else f"正在向群组{topic}推送新闻")
    payload = json.dumps({
    "token": f"{token}",
    "title": f"{title}",
    "content": f'<img src={img_url} alt="图片无法显示">',
    "topic": f"{topic}",
    "template": "html"
    })
    headers = {
    'Content-Type': 'application/json'
    }
    conn.request("POST", "/send", payload, headers)
    res = conn.getresponse()
    data = res.read()
    root_logger.info(data.decode("utf-8"))

#Moeus