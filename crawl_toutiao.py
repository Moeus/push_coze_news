from DrissionPage import WebPage
#多条件定位下使用"tag():a"  而不是tag:a
from DrissionPage import ChromiumOptions,SessionOptions
import time
import re
import coze_solve
from coze_solve import coze_logger
import queue
import threading
import os
import json
import copy
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

def get_toutiao(webpage:WebPage):
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
        coze_logger.info(f"[头条]单次抓取完成:{hot_url}")
        article["title"]=""
        article["content"]=""
        #texts()填True时，只返回这个元素分散的文本节点，例如<p> bbb <strong> aaa <strong/> bbb<p/>只返回bbbbbb
        # tab.close()
    time.sleep(0.5)
    #主tab关闭
    main_tab.close()
    time.sleep(0.5)

def get_weibo(webpage:WebPage):
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
    #去除首个
    hotspot_linklist=hotspot_linklist[1:]
    #单个新闻的格式
    article={
        "title":"",
        "content":""
    }
    coze_logger.info("[微博]开始抓取热榜微博内容")
    #遍历所有hot链接，获取内容，
    # 新开标签，爬新闻，存入list，退出
    tab=webpage.new_tab()#多线程性能差，先使用复用tab的模式而不是新建tab
    for hot_url in hotspot_linklist:
        tab.get(hot_url)
        #对文章属性进行提取,有些文章可能不完整不包含部分内容，所以使用try语块
        try:
            article["title"]=tab.ele("@@tag()=h1@@class=short",timeout=1).ele("@tag():a",timeout=1).text
            coze_logger.info(f"{article['title']}")
            #获取第一条微博的内容元素，内容包括作者和正文
            content_ele=tab.ele("@@tag()=p@@node-type=feed_list_content@@class=txt",timeout=2)
            contents=[f"{content_ele.attr("nick-name")}:",content_ele.texts()]
            article["content"]=str(contents) #str本身是赋值时副本赋值
            coze_logger.info(f"{article['content']}")
            contents=[]
            article_queue.put(article.copy())#传回副本，因为这个变量被复用
            coze_logger.info(f"[微博]单次抓取完成{hot_url}")
            article["title"]=""
            article["content"]=""
        except Exception as e:
            coze_logger.info(f"链接不包含新闻内容{hot_url}，跳过")
            continue
        #texts()填True时，只返回这个元素分散的文本节点，例如<p> bbb <strong> aaa <strong/> bbb<p/>只返回bbbbbb
        # tab.close()
    time.sleep(0.5)
    #主tab关闭
    main_tab.close()
    time.sleep(0.5)

def read_queue(script_dir:str):
    articles=[]
    while crawl_state or ( not article_queue.empty()):
        #爬虫未结束或者queue还有内容就继续循环
        if not article_queue.empty():
            articles.append(article_queue.get())
            coze_logger.info(f"[读线程]{articles[-1]}")
    script_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(script_dir,"news.json"),"w",encoding="utf-8") as file:
         json.dump(articles, file, indent=4, ensure_ascii=False)
    coze_logger.info("[读线程] 新闻写入news.json成功")

if __name__=="__main__":
    so.set_cookies("SCF=ApviCpT8Ln9U75uBzhkE6-6XBlaqqk1KfmeCMltuuDJ210_iqUnxHHsDPcus242MKQ8sY6K6ZCBU_Q5Xx2b3jZo.; ALF=1744034050; SUB=_2A25KyDxRDeRhGeFH7lUY-S_KzD6IHXVppDGZrDV8PUJbkNANLWjEkW1NevwxzC1f_qH6Rpbw88l8TC9nRXG3yrhz; SUBP=0033WrSXqPxfM725Ws9jqgMF55529P9D9WFs4NZ8B6puoFH9HU0.MPvD5JpX5KzhUgL.FoM4SKM41K2cS0z2dJLoIp7LxKML1KBLBKnLxKqL1hnLBoMN1K-N1K.pSoME; WBPSESS=Dt2hbAUaXfkVprjyrAZT_HHiN_x43quwcFtxtULFpJyyRHCWFHcVeAK76Lv47aSogT12rgOxBUcp1jXqoh0VtAkFyXBoM46oY-hUotU3Cz71udztoJ3joE208FD0FOO5VJQQy7lHy7sr_XBdRzoUPrFzrGrnxmrknITv1qb5MdY6N5XF1LpKHHGcLHfdTun5ea9WXczHxH_kHa0UZOVGYA==; XSRF-TOKEN=RxU5s1KkCNjpKfsqWqy7bthC")
    webpage=WebPage(mode="d",chromium_options=co,session_or_options=so)#返回webpage对象
    get_weibo(webpage=webpage)
    get_toutiao(webpage=webpage)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    coze_logger.info(f"script_dir:{script_dir}")
    T_read_q=threading.Thread(target=read_queue,args=(script_dir,))
    T_read_q.start()
    crawl_state=False
    T_read_q.join()

