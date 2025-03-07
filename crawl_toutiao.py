from DrissionPage import WebPage
#多条件定位下使用"tag():a"  而不是tag:a
from DrissionPage import ChromiumOptions
import time
import re

article={
    "title":"",
    "content":""
}

co=ChromiumOptions()
co.set_load_mode("normal")
webpage=WebPage(mode="d",chromium_options=co)
url="https://www.toutiao.com"
#主tab
main_tab=webpage.new_tab(url=url)
hotspot_linklist=[]
hot_eles=main_tab.eles("@@tag():a@@class=article-item@@rel=noopener nofollow")
for ele in hot_eles:
    hotspot_linklist.append(ele.attr("href"))
    print(ele.attr("href"))
hotspot_linklist=hotspot_linklist[1:]
articles=[]
#从新标签打开hot 避免js刷新错误
for hot_url in hotspot_linklist:
    tab=webpage.new_tab(url=hot_url)
    #确保是文章属性页面
    if not re.search("article",hot_url):
        new_ele=tab.ele("@@tag():a@@rel=noopener@@class=title")
        article_url=new_ele.attr("href")
        #重新定url还不是文章属性，那就别找了
        if not re.search("article",article_url): 
            tab.close()
            continue
        else:
            tab.get(article_url)
            print(article_url)
    else :
        print(hot_url)
    #对文章属性进行提取
    article["title"]=tab.ele("@tag():h1").text
    article["content"]=str(tab.ele("@tag():article").texts())
    print(article)
    articles.append(article.copy())#传回副本，因为这个变量被复用
    article["title"]=""
    article["content"]=""
    #texts()填True时，只返回这个元素分散的文本节点，例如<p> bbb <strong> aaa <strong/> bbb<p/>只返回bbbbbb
    tab.close()
time.sleep(3)
#主tab关闭
main_tab.close()
# webpage.quit