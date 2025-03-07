import requests
import pyautogui
from typing import Literal
import json
import os
import threading
import time
from datetime import datetime, timedelta
from cozepy import COZE_CN_BASE_URL
from cozepy import Coze, TokenAuth, Message, ChatStatus, MessageContentType
import logging
state = False

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

# 获取新闻
def get_news(api_token, work_id):
    coze_api_token = api_token
    coze_api_base = COZE_CN_BASE_URL
    global state
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
        context = result_json["result"]
        context = "".join(context.split("\n"))
        return context
    except Exception as e:
        coze_logger.error(f"coze获取新闻发生错误: {e}")


# 新闻文字转图片，在get_news内被调用
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


# 获取accessID
def get_access_token(AppSecret, AppID):
    try:
        url = 'https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={}&secret={}'.format(
            AppID, AppSecret)
        response = requests.get(url)
        res_html = response.json()
        access_token = res_html['access_token']
        coze_logger.info("成功获取access_token")
    except Exception as e:
        coze_logger.error(res_html)
        coze_logger.error(f"获取accessID时出现错误 {e}")
        exit()
    return access_token


# 上传永久素材
def push_image(access_token, image_path, type: Literal["image", "voice", "video", "thumb"]):
    media_type = type
    upload_url = f"https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={access_token}&type={media_type}"
    try:
        coze_logger.info("正在上传新闻卡片至微信公众号永久素材库")
        with open(image_path, 'rb') as file:
            response = requests.post(upload_url, files={'media': (image_path, file)})
        result = response.json()
        coze_logger.info("上传素材成功")
    except Exception as e:
        coze_logger.error(f"上传素材时发生异常：{e}")
    if 'media_id' in result:
        media_id = result['media_id']
        img_url = result['url']
        coze_logger.info(f"上传成功素材成功! media_id: {media_id}, img_url: {img_url}")
        return media_id, img_url
    else:
        coze_logger.error(f"上传素材失败，错误信息: {result['errmsg']}")


# 删除七天以前的在本地存储的新闻png
def delete_old_pngs(year, month, day):
    current_date = datetime(year, month, day)
    seven_days_ago = current_date - timedelta(days=7)
    script_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "png")
    for filename in os.listdir(script_dir):
        if filename.endswith('.png'):
            try:
                file_date_str = filename.split('.')[0]
                file_date = datetime.strptime(file_date_str, '%Y-%m-%d')
                if file_date < seven_days_ago:
                    file_path = os.path.join(script_dir, filename)
                    os.remove(file_path)
                    coze_logger.info(f"已删除旧的 PNG 文件: {filename}")
            except ValueError:
                continue


# 打印运行时间线程函数
def print_running_time():
    start_time = time.time()
    global state
    while not state:
        elapsed_time = time.time() - start_time
        print(f"程序已运行 {elapsed_time:.2f} 秒", end='\r')


# 主要工作线程入口
def main(year, month, day):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # try:
    #     coze_logger.info("获取获取微信api配置")
    #     with open(os.path.join(script_dir, "config/wechat_access_api.json"), "r", encoding='utf-8') as file:
    #         wechat_access_config = json.load(file)
    #     coze_logger.info("成功获取获取微信api配置")
    # except Exception as e:
    #     coze_logger.error("读取微信api配置出错")

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
            liuguang_data = json.load(file)
        coze_logger.info("成功获取新闻卡片配置")
    except Exception as e:
        coze_logger.error("读取新闻卡片配置出错")

    # access_token=get_access_token(*wechat_access_config.values())
    context = get_news(*coze_config.values())
    img_path= get_png(liuguang_data,content=context,script_dir=script_dir,year=year, month=month, day=day)
    # img_id = push_image(access_token, image_path=img_path, type="image")
    delete_old_pngs(year, month, day)
    time.sleep(1)
    global state
    state = True

# 多线程入口函数
if __name__ == "__main__":
    current_time = time.localtime()
    year = current_time.tm_year
    month = current_time.tm_mon
    day = current_time.tm_mday
    threading_main = threading.Thread(target=main, args=(year, month, day))
    threading_time = threading.Thread(target=print_running_time)
    coze_logger.info("开始执行")
    threading_time.start()
    threading_main.start()
    threading_main.join()
    threading_time.join()
    time.sleep(1)
    coze_logger.info("全部完成")

#Moeus