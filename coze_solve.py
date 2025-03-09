import requests
from typing import Literal
import json
import os
import threading
import time
from datetime import datetime, timedelta
import http.client
from qiniu import Auth, put_file, etag
from cozepy import COZE_CN_BASE_URL
from cozepy import Coze, TokenAuth, Message, ChatStatus, MessageContentType
import logging
coze_logger = logging.getLogger('root')
# 清除原有的处理器配置
for handler in coze_logger.handlers[:]:
    coze_logger.removeHandler(handler)
# 配置日志
coze_logger.setLevel(logging.INFO)
#创建格式化器,准备被日志处理器使用
formatter = logging.Formatter(
    fmt='[%(name)s][%(levelname)s][%(asctime)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
# 创建文件处理器，将日志写入 working.log 文件，写入模式为追加，编码使用utf-8
file_handler = logging.FileHandler('working.log', mode='a',encoding='utf-8')
file_handler.setLevel(logging.WARNING)
file_handler.setFormatter(formatter)
coze_logger.addHandler(file_handler)
# 创建控制台处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(formatter)
coze_logger.addHandler(console_handler)
#日志功能处理完成

def solve_news(api_token, work_id):
    coze_api_token = api_token
    coze_api_base = COZE_CN_BASE_URL
    try:
        coze = Coze(auth=TokenAuth(token=coze_api_token), base_url=coze_api_base)
        workflow_id = work_id
        parameters = {
            "secret_key": "Moeus"
        }
        coze_logger.info("开始调用coze工作流获取新闻")
        workflow = coze.workflows.runs.create(
            workflow_id=workflow_id,
            parameters=parameters
        )
        result_json = json.loads(workflow.data)
        coze_logger.info("成功解析coze返回的json")
        context = result_json["result"]#这里面时字符串，需要json解析成json格式
        return context
    except Exception as e:
        coze_logger.error(f"coze获取新闻发生错误: {e}")


def get_png(data,content,script_dir, year, month, day):
    target_url = "https://fireflycard-api.302ai.cn/api/saveImg"
    data["form"]["content"] = content
    data["form"]["title"] = f"<p>👋{year}-{month}-{day}热点新闻😺💕</p>"
    data["form"]["textCount"] = len(content)
    coze_logger.info(f"总字数：{len(content)}")
    headers = {
        'Content-Type': 'application/json'
    }
    try:
        coze_logger.info("正在生成新闻卡片PNG图像")
        response = requests.post(target_url, json=data, headers=headers, timeout=100, verify=False)
        response.raise_for_status()
        os.chdir(script_dir)
        file_path = f'png/{year}-{month}-{day}.png'
        with open(file_path, 'wb') as file:
            file.write(response.content)
        coze_logger.info(f"新闻卡片获取成功已成功！")
        coze_logger.info(f"新闻卡片已保存到 {os.path.join(script_dir, file_path)}")
        return os.path.join(script_dir, file_path)
    except requests.exceptions.HTTPError as http_err:
        coze_logger.error(f'获取新闻卡片时 HTTP 错误发生: {http_err}')
    except requests.exceptions.ConnectionError as conn_err:
        coze_logger.error(f'连接错误发生: {conn_err}')
    except requests.exceptions.Timeout as timeout_err:
        coze_logger.error(f'请求超时: {timeout_err}')
    except requests.exceptions.RequestException as req_err:
        coze_logger.error(f'请求发生未知错误: {req_err}')
    return 0

# 删除七天以前的在本地存储的新闻png
def check_old_pngs(year, month, day):
    """
    检查并删除七天前的新闻图片，并且检查今日新闻图片是否以及存在
    """
    current_date = datetime(year, month, day)
    seven_days_ago = current_date - timedelta(days=7)
    script_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "png")
    nowaday_news_exist=False
    for filename in os.listdir(script_dir):
        if filename.endswith('.png'):
            if filename==f"{year}-{month}-{day}.png": 
                coze_logger.info(f"找到今现存的日新闻卡片{year}-{month}-{day}.png")
                nowaday_news_exist=True
            try:
                file_date_str = filename.split('.')[0]
                file_date = datetime.strptime(file_date_str, '%Y-%m-%d')
                if file_date < seven_days_ago:
                    file_path = os.path.join(script_dir, filename)
                    os.remove(file_path)
                    coze_logger.info(f"已删除旧的 PNG 文件: {filename}")
            except ValueError:
                continue
    return nowaday_news_exist


#上传到七牛对象存储库
def qiniu_push_file(qiniu_config,year,month,day,img_path):
    q = Auth(*qiniu_config.values())
    #检查是否以及存在
    base_url="http://ssqnlgcpi.hn-bkt.clouddn.com/"
    #要上传的空间
    bucket_name = 'moeus-news-png'
    #上传后保存的文件名
    key = f'{year}-{month}-{day}.png'
    #生成上传 Token，可以指定过期时间等
    token = q.upload_token(bucket_name, key, 3600)
    #要上传文件的本地路径
    localfile = img_path
    ret, info = put_file(token, key, localfile, version='v2')
    coze_logger.info(info)
    assert ret['key'] == key
    assert ret['hash'] == etag(localfile)
    coze_logger.info(ret)
    coze_logger.info(base_url+key)
    return base_url+key

def pushplus(token,title,img_url,topic=""):
    conn = http.client.HTTPSConnection("www.pushplus.plus")
    coze_logger.info("正在向用户推送新闻" if topic=="" else f"正在向群组{topic}推送新闻")
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
    coze_logger.info(data.decode("utf-8"))

# 主要工作线程入口
def main(year, month, day):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if check_old_pngs(year, month, day):
        coze_logger.info(f"已存在今日新闻卡片{year}-{month}-{day}.png，即将上传与推送")
        try:
            coze_logger.info("获取对象存储库配置")
            with open(os.path.join(script_dir, "config/qiniu.json"), 'r', encoding='utf-8') as file:
                qiniu_config = json.load(file)
            coze_logger.info("成功获取对象存储库配置")
        except Exception as e:
            coze_logger.error("读取对象存储库配置出错")

        url=qiniu_push_file(qiniu_config=qiniu_config,year=year,month=month,day=day,img_path=os.path.join(script_dir,"png",f'{year}-{month}-{day}.png'))
        res=pushplus(token="197bcdaf723444f6a0b48dfd304c3153",title=f"{year}-{month}-{day}今日热点新闻",img_url=url,topic="Moeus266")
    else:
        try:
            coze_logger.info("获取coze令牌配置")
            with open(os.path.join(script_dir, "config/coze_api.json"), "r", encoding='utf-8') as file:
                coze_config = json.load(file)
            coze_logger.info("成功获取获取coze令牌配置")
        except Exception as e:
            coze_logger.error("读取coze令牌配置出错")
            
        try:
            coze_logger.info("获取新闻卡片配置")
            with open(os.path.join(script_dir, "config/liuguang_api.json"), 'r', encoding='utf-8') as file:
                liuguang_config = json.load(file)
            coze_logger.info("成功获取新闻卡片配置")
        except Exception as e:
            coze_logger.error("读取新闻卡片配置出错")

        try:
            coze_logger.info("获取对象存储库配置")
            with open(os.path.join(script_dir, "config/qiniu.json"), 'r', encoding='utf-8') as file:
                qiniu_config = json.load(file)
            coze_logger.info("成功获取对象存储库配置")
        except Exception as e:
            coze_logger.error("读取对象存储库配置出错")
        context = get_news(*coze_config.values())
        img_path= get_png(liuguang_config,content=context,script_dir=script_dir,year=year, month=month, day=day)
        url=qiniu_push_file(qiniu_config=qiniu_config,year=year,month=month,day=day,img_path=img_path)
        res=pushplus(token="197bcdaf723444f6a0b48dfd304c3153",title=f"{year}-{month}-{day}今日热点新闻",img_url=url,topic="Moeus266")
    time.sleep(1)
    global state
    state = True


#Moeus