import asyncio

import aiohttp
from DrissionPage import WebPage
#多条件定位下使用"tag():a"  而不是tag:a
from DrissionPage import ChromiumOptions,SessionOptions
import time
import re
import coze_solve
from coze_solve import coze_logger
import random
import queue
import threading
import os
import json
#全局queue队列，线程之间通信
article_queue=queue.Queue()
#主线程运行状态
crawl_state=True
#全局浏览器配置
co=ChromiumOptions()
co.set_load_mode("eager")#html的Dom加载完毕就开始爬，因为爬的是文字，所以可以这样设置
co.set_argument('--autoplay-policy','no-user-gesture-required')#禁用视频播放
co.no_imgs()#禁用图片加载
co.no_js()#禁用js加载
co.set_local_port(9222)
co.set_user_data_path(r"C:\Users\26627\AppData\Local\Google\Chrome\User Data")
so=SessionOptions()
co.set_argument("--remote-debugging-port","9222")

def get_toutiao(webpage:WebPage,count:int=3):
    url="https://www.toutiao.com"
    #主tab
    main_tab=webpage.new_tab(url=url)#返回mixtab对象
    hotspot_linklist=[]
    #匹配热榜区域上的<a/>标签
    hot_eles=main_tab.eles("@@tag():a@@class=article-item@@rel=noopener nofollow")
    target_count=-1#后面要去除首个，所以取-1
    for ele in hot_eles:
        #获取热榜文章链接，可能是trending链接也可能是article链接
        pre_url=ele.attr("href")
        #确保是article链接，如果不是找trending链接里面的article链接
        if not re.search("article",pre_url):
            find_tab=webpage.new_tab(url=pre_url)
            try:
                #尝试寻找trending下的article链接
                new_ele=find_tab.ele("@@tag():a@@href:article",timeout=1)#模糊匹配article
                article_url=new_ele.attr("href")
            except Exception as e:
                coze_logger.info(f"[头条]当前链接不是article链接，链接内也未找到article链接{pre_url}")
                find_tab.close()
                continue
            else:
                find_tab.close()
                hotspot_linklist.append(article_url)
                coze_logger.info(f"[头条]找到热榜文章链接{article_url}")#少个冒号做区别
        else :
            coze_logger.info(f"[头条]找到热榜文章链接:{pre_url}")
            hotspot_linklist.append(pre_url)
        target_count+=1
        #检测数量
        if target_count==count:
            break
    #去除首个
    hotspot_linklist=hotspot_linklist[1:]
    #单个新闻的格式
    article={
        "title":"",
        "source":"[头条新闻]",
        "content":""
    }
    coze_logger.info("[头条]开始抓取新闻内容")
    #遍历所有hot链接，获取内容，
    # 新开标签，爬新闻，存入list，退出
    tab=webpage.new_tab()
    for hot_url in hotspot_linklist:
        tab.get(hot_url)
        #对文章属性进行提取
        article["title"]=tab.ele("@tag():h1").text
        p_list=tab.ele("@tag():article").eles("@tag():p")
        contents=[]
        for p in p_list:
            content=p.text
            contents.append(content)
        article["content"]="".join(contents)
        contents=[]
        article_queue.put(article.copy())#传回副本，因为这个变量被复用
        coze_logger.info(f"[头条]单次抓取完成:{hot_url}")
        article["title"]=""
        article["content"]=""
    time.sleep(0.5)
    #子tab关闭
    tab.close()
    #主tab关闭
    main_tab.close()
    time.sleep(0.5)

def get_weibo(webpage:WebPage,count:int=3):
    url="https://weibo.com/hot/search"#进入微博
    #主tab
    main_tab=webpage.new_tab(url=url)#返回mixtab对象
    main_tab.ele("@@tag():a@@href:search").click()#<a href="/newlogin?tabtype=search&amp;gid=&amp;openLoginLayer=0&amp;url=https%3A%2F%2Fweibo.com%2Fhot%2Fsearch" class="router-link-exact-active router-link-active ALink_default_2ibt1" to="[object Object]"><div class="woo-box-flex woo-box-alignCenter NavItem_main_2hs9r NavItem_cur_2ercx" role="link" title="热搜" tabindex="0" data-focus-visible="true"><i class="woo-font woo-font--navDot NavItem_icon_1tzN0"></i><span class="NavItem_text_3Z0D7">热搜</span></div></a>
    hotspot_linklist=[]
    #匹配微博热榜区域上的<a/>标签
    hot_eles=main_tab.eles("@@tag():a@@class:HotTopic@@target=_blank")
    for ele in hot_eles:
        pre_url=ele.attr("href")
        hotspot_linklist.append(pre_url)
        coze_logger.info(f'[微博]找到热榜微博链接:{pre_url}')
    
    #随机取数,取链接
    if count<=len(hotspot_linklist):
        coze_logger.info(f"[微博]随机选取{count}个链接")
        random_number=random.sample(list(range(0,len(hotspot_linklist))),k=count)
        target_link=[hotspot_linklist[i] for i in random_number]
    else:
        coze_logger.info("[微博]文章链接少有目标数量，取取全部文章链接")
        target_link=hotspot_linklist

    #单个新闻的格式
    article={
        "title":"",
        "source": "[微博]",
        "content":""
    }
    coze_logger.info("[微博]开始抓取热榜微博内容")
    # 新开标签，爬新闻，存入list，退出
    tab=webpage.new_tab()
    for hot_url in target_link:
        tab.get(hot_url)
        #对文章属性进行提取,有些文章可能不完整不包含部分内容，所以使用try语块
        try:
            article["title"]=tab.ele("@@tag()=h1@@class=short",timeout=1).ele("@tag():a",timeout=1).text
            #寻找正文内容，先找展开键
            try:
                tab.ele("@@tag()=a@@action-type=fl_unfold").click()
            finally:
                content_ele = tab.ele("@@tag()=p@@node-type=feed_list_content_full@@class=txt", timeout=2)
            contents=[f"{content_ele.attr("nick-name")}:","".join(content_ele.texts())]#确保两个元素都是str，否则下一个join报错
            article["content"]=re.sub(r'[\n\s]', '',"".join(contents))
            contents=[]
            article_queue.put(article.copy())#传回副本，因为这个变量被复用
            coze_logger.info(f"[微博]单次抓取完成{hot_url}")
            article["title"]=""
            article["content"]=""
        except Exception as e:
            coze_logger.error(e)
            coze_logger.info(f"[微博]可能是链接不包含新闻内容{hot_url}，跳过")
            continue

    time.sleep(0.5)
    #子tab关闭
    tab.close()
    #主tab关闭
    main_tab.close()
    time.sleep(0.5)


def get_zhihuToday(webpage: WebPage, count: int = 3):
    url = "https://tophub.today/n/KMZd7VOvrO"  # 进入微博
    # 主tab
    main_tab = webpage.new_tab(url=url)  # 返回mixtab对象
    linklist = []
    hot_eles = main_tab.ele("@@tag():div@@class=cc-dc-c").eles("@@tag():a@@rel=nofollow@!title")
    #存在重复a标签，所以加@!title
    for ele in hot_eles:
        linklist.append(ele.attr("href"))
    # 单个新闻的格式
    article = {
        "title": "",
        "source": "[知乎日报]",
        "content": ""
    }
    coze_logger.info("[知乎日报]开始抓取知乎日报内容")
    tab = webpage.new_tab()
    for hot_url in linklist:
        tab.get(hot_url)
        # 对文章属性进行提取,有些文章可能不完整不包含部分内容，所以使用try语块
        try:
            article["title"] = tab.ele("@@tag()=p@@class=DailyHeader-title", timeout=1).text
            # 获取文章内所有p标签
            content_eles=tab.ele("@@tag()=div@@class=content").eles("@tag():p")
            contents =""
            for ele in content_eles:
                contents=contents+ele.text
            article["content"] = contents
            article_queue.put(article.copy())  # 传回副本，因为这个变量被复用
            coze_logger.info(f"{article}")
            coze_logger.info(f"[知乎日报]单次抓取完成{hot_url}")
            article["title"] = ""
            article["content"] = ""
        except Exception as e:
            coze_logger.error(e)
            coze_logger.info(f"[知乎日报]可能是链接内容有问题{hot_url}，跳过")
            continue
    time.sleep(0.5)
    # 子tab关闭
    tab.close()
    # 主tab关闭
    main_tab.close()
    time.sleep(0.5)


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
                coze_logger.info(f"{result}")
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

def read_queue(script_dir:str):
    articles=[]
    while not article_queue.empty():
        articles.append(article_queue.get())
        coze_logger.info(f"[读线程]{articles[-1]}")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(script_dir,"news.json"),"w",encoding="utf-8") as file:
         json.dump(articles, file, indent=4, ensure_ascii=False)
    coze_logger.info("[读线程] 新闻写入news.json成功")

if __name__=="__main__":
    #单线程同步运行，drssionpage多线程情况下很慢
    webpage=WebPage(mode="d",chromium_options=co,session_or_options=so)#返回webpage对象
    get_zhihuToday(webpage=webpage)
    get_weibo(webpage=webpage)
    get_toutiao(webpage=webpage)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    coze_logger.info(f"script_dir:{script_dir}")
    T_read_q=threading.Thread(target=read_queue,args=(script_dir,))
    T_read_q.start()
    T_read_q.join()

