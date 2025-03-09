import asyncio
import os.path

import aiohttp
import json

from send_solve import root_logger


async def run_workflow(news: str):
    url = 'https://api.coze.cn/v1/workflow/run'
    headers = {
        "Authorization": "Bearer pat_yUmVBjZAhTbmF90GZjKcysB7UrTKQ4GevS33z5AadZQxqweT4Jni0ZdlDIiKBTLA",
        "Content-Type": "application/json"
    }
    data = {
        "parameters": {
            "secret_key": "Moeus",
            "news": f"{news}"
        },
        "workflow_id": "7475598695737229346"
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as response:
            if response.status == 200:
                result = await response.json()
                root_logger.info(f"{result}")
                root_logger.info(f"{result['result']}")
                return result
            else:
                print(f"Request failed with status code: {response.status}")
                return None


async def coze_main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(script_dir, "news.json"), "r", encoding="utf-8") as file:
        news_list = json.load(file)

    task_list = []
    while news_list:
        news = news_list.pop()
        task = asyncio.create_task(run_workflow(news))  # 使用 create_task 替代 ensure_future
        task_list.append(task)

    results = await asyncio.gather(*task_list)  # 直接使用 await 等待所有任务
    print("All results:", results)


if __name__ == "__main__":
    asyncio.run(coze_main())  # 自动管理事件循环，避免手动创建和关闭