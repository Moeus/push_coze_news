from DrissionPage import WebPage
#多条件定位下使用"tag():a"  而不是tag:a
from DrissionPage import ChromiumOptions
import time
import re
import coze_solve
from coze_solve import coze_logger
import queue
import threading
import os
import json
#全局queue队列，线程之间通信
article_queue=queue.Queue()
#全局浏览器配置
co=ChromiumOptions()
co.set_load_mode("eager")#html的Dom加载完毕就开始爬，因为爬的是文字，所以可以这样设置
co.auto_port()#自动找port，避免冲突
co.set_argument('--autoplay-policy','no-user-gesture-required')#禁用视频播放
co.no_imgs()#禁用图片加载
co.no_js()#禁用js加载

def get_toutiao():
    global co
    webpage=WebPage(mode="d",chromium_options=co)#返回webpage对象
    url="https://www.toutiao.com"
    #主tab
    main_tab=webpage.new_tab(url=url)#返回mixtab对象
    hotspot_linklist=[]
    #匹配热榜区域上的<a/>标签
    hot_eles=main_tab.eles("@@tag():a@@class=article-item@@rel=noopener nofollow")
    for ele in hot_eles:
        #获取热榜文章链接，可能是trending链接也可能是article链接
        pre_url=ele.attr("href")
        #确保是article链接，如果不是找trending链接里面的article链接
        if not re.search("article",pre_url):
            find_tab=webpage.new_tab(url=pre_url)
            try:
                #尝试寻找trending下的article链接
                new_ele=find_tab.ele("@@tag():a@@href:article")#模糊匹配article
                article_url=new_ele.attr("href")
            except Exception as e:
                coze_logger.info(f"[头条]当前链接不是article链接，链接内也未找到article链接{pre_url}")
                find_tab.close()
                continue
            else:
                find_tab.close()
                hotspot_linklist.append(article_url)
                coze_logger.info(f"[头条]找到热榜文章链接{article_url}")
        else :
            coze_logger.info(f"[头条]找到热榜文章链接：{pre_url}")
            hotspot_linklist.append(pre_url)
    #去除首个
    hotspot_linklist=hotspot_linklist[1:]
    #单个新闻的格式
    article={
        "title":"",
        "content":""
    }
    coze_logger.info("[头条]开始抓取新闻内容")
    #遍历所有hot链接，获取内容，
    # 新开标签，爬新闻，存入list，退出
    tab=webpage.new_tab()#多线程性能差，先使用复用tab的模式而不是新建tab
    for hot_url in hotspot_linklist:
        #新开标签来抓取，防止出错
        # tab=webpage.new_tab(url=hot_url)
        tab.get(hot_url)
        #对文章属性进行提取
        article["title"]=tab.ele("@tag():h1").text
        p_list=tab.ele("@tag():article").eles("@tag():p")
        contents=[]
        for p in p_list:
            content=p.text
            contents.append(content)
        article["content"]=contents[:]
        contents=[]
        article_queue.put(article.copy())#传回副本，因为这个变量被复用
        coze_logger.info(f"[头条]单次抓取完成{hot_url}")
        article["title"]=""
        article["content"]=""
        #texts()填True时，只返回这个元素分散的文本节点，例如<p> bbb <strong> aaa <strong/> bbb<p/>只返回bbbbbb
        # tab.close()
    time.sleep(0.5)
    #主tab关闭
    main_tab.close()
    time.sleep(0.5)
    webpage.quit(force=True)

if __name__=="__main__":
    T_toutiao=threading.Thread(target=get_toutiao)
    T_toutiao.start()
    articles=[]
    while T_toutiao.is_alive():
        if not article_queue.empty():
            articles.append(article_queue.get())
    
    script_dir = os.path.dirname(os.path.abspath(__file__))

    with open(os.path.join(script_dir,"news.json"),"w",encoding="utf-8") as file:
         json.dump(articles, file, indent=4, ensure_ascii=False)