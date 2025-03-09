import datetime
from datetime import timedelta,datetime
import os
from send_solve import root_logger
import send_solve
import re
def check_old_files(year, month, day):
    """
    res这个文件夹下的文件都是以f'{year}-{month}-{day}'为前缀命名的
    检查并删除七天前的旧文件，并且检查是否存在今日的文件
    """
    current_date = datetime(year, month, day)
    seven_days_ago = current_date - timedelta(days=7)
    script_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "res")
    nowaday_news_exist = False
    # 定义正则表达式模式来匹配日期部分
    date_pattern = r'(\d{4})-(\d{1,2})-(\d{1,2})'
    for filename in os.listdir(script_dir):
        # 检查是否存在今日的文件
        if filename == f"{year}-{month}-{day}.png":
            root_logger.info(f"找到今现存的日新闻卡片{year}-{month}-{day}.png")
            nowaday_news_exist = True
        # 使用正则表达式匹配文件名中的日期部分
        match = re.search(date_pattern, filename)
        if match:
            try:
                file_date = datetime.strptime(match.group(0), '%Y-%m-%d')
                # 对比日期
                if file_date < seven_days_ago:
                    file_path = os.path.join(script_dir, filename)
                    os.remove(file_path)
                    root_logger.info(f"已删除旧的文件文件: {filename}")
            except ValueError:
                continue
    return nowaday_news_exist

check_old_files(2025,3,9)
url=send_solve.qiniu_push_file(2025,3,9,r"D:\push_coze_news\res\2025-3-9.png")

send_solve.pushplus("197bcdaf723444f6a0b48dfd304c3153","今日新闻",img_url=url,topic="Moeus266")