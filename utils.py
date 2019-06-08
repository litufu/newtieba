# -*- coding: utf-8 -*-

from urllib.request import urlopen
from bs4 import BeautifulSoup
from urllib.parse import quote
import random
import asyncio
import time
import hashlib
import re
import requests
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from database import Bar, Base,Tie,Customer,Proxy

# data
engine = create_engine('sqlite:///newtiebar.sqlite')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

engine1 = create_engine('sqlite:///newtiebar1.sqlite')
con = engine1.connect()#创建连接

# webdriver
chrome_options = Options()
chrome_options.add_argument(
    '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36')
chrome_options.add_argument('--headless')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
driver = webdriver.Chrome(
    executable_path="C:\Program Files (x86)\Google\Chrome\Application\chromedriver.exe",
    options=chrome_options)


# baClassFirst : 贴吧大类 如高等院校、中小学
# baClassSecond: 贴吧二类 如广东地区、北京地区
# 获取二级类别
def get_second_ba_class(first_class):
    html = urlopen("http://tieba.baidu.com/f/index/forumpark?cn=&ci=0&"
                   "pcn={}&pci=0&ct=1&rn=20&pn=1".format(quote(first_class, encoding="utf-8")))
    bs = BeautifulSoup(html.read(), 'html.parser')
    return bs.find("ul", {"class": "class_list"}).find_all('li')


# 获取所有的吧名
def get_all_ba_name(first_class):
    second_classes = get_second_ba_class(first_class)
    for className in second_classes:
        print('-----{}-----'.format(className.get_text()))
        for i in range(1, 31):
            html = urlopen("http://tieba.baidu.com/f/index/forumpark?cn={}&ci=0&pcn="
                           "{}&pci=0&ct=1&st=new&pn={}"
                           .format(quote(className.get_text(), encoding="utf-8"),
                                   quote(first_class, encoding="utf-8"), i))
            bs = BeautifulSoup(html.read(), 'html.parser')
            for baInfo in bs.find_all('div', {"class": "ba_info"}):
                ba_name = baInfo.find("p", {"class": "ba_name"}).get_text()
                if len(ba_name) != 0:
                    yield ba_name[0:len(ba_name) - 1]


def get_bar():
    # 获取高中和大学吧,从百度贴吧获取
    for barName in get_all_ba_name('高等院校'):
        print(barName)
        b = Bar(name=barName, kind="daxue", hassend=False)
        session.add(b)
        session.commit()

    for barName in get_all_ba_name('中小学'):
        if '高' in barName or '中' in barName:
            print(barName)
            b = Bar(name=barName, kind="gaozhong", hassend=False)
            session.add(b)
            session.commit()


def get_school():
    # 获取高中和大学从csv获取
    df_daxue = pd.read_csv('./data/daxue.csv')
    for name in df_daxue['name']:
        bars = session.query(Bar).filter(Bar.name == name).all()
        if len(bars) == 0:
            b = Bar(name=name, kind="daxue", hassend=False)
            session.add(b)
            session.commit()

    df_gaozhong = pd.read_csv('./data/gaozhong.csv')
    for name in df_gaozhong['school_name']:
        bars = session.query(Bar).filter(Bar.name == name).all()
        if len(bars) == 0:
            b = Bar(name=name, kind="gaozhong", hassend=False)
            session.add(b)
            session.commit()


def get_tie(bar_name, kw):
    url = 'http://tieba.baidu.com/f?kw={}'.format(bar_name)
    print(url)
    driver.get(url=url)
    time.sleep(3)
    save_tie(bar_name, kw)
    #driver.close()


def save_tie(bar_name,kw):
    print('{}kaishi'.format(bar_name))
    links = driver.find_element_by_id('thread_list').find_elements_by_partial_link_text(kw)
    if len(links) == 0:
        print('没有找到相关{}链接'.format(kw))
    else:
        # 保存贴
        for link in links:
            text = link.get_attribute('href')
            print('tie link{}'.format(text))
            pattern = re.compile('.*/p/(\d+)')
            res = pattern.match(text)
            if res:
                tid = res[1]
                ties = session.query(Tie).filter(Tie.tid == tid).all()
                if len(ties) == 0:
                    b = Tie(url=text, tid=tid, bar_name=bar_name)
                    session.add(b)
        session.commit()
#         保存用户
        for link in links:
            link.click()
            time.sleep(3)
            windows = driver.window_handles
            # 切换页面
            driver.switch_to.window(windows[1])
            customer_links = driver.find_elements_by_class_name('p_author_name')
            for customer_link in customer_links:

                href = customer_link.get_attribute('href')
                print('客户连接{}'.format(href))
                nick_name = customer_link.text
                customers = session.query(Customer).filter(Customer.url == href).all()
                if len(customers) == 0:
                    b = Customer(url=href, nick_name=nick_name, has_send=False)
                    session.add(b)
            session.commit()
            driver.close()
            print(windows)
            driver.switch_to.window(windows[0])


def get_ties():
    try:
        gaozhongs = session.query(Bar).filter(Bar.kind =="gaozhong").all()
        for gaozhong in gaozhongs:
            get_tie(gaozhong.name, '高考')

        daxues = session.query(Bar).filter(Bar.kind =="daxue").all()
        for daxue in daxues:
            get_tie(daxue.name, '报考')
    except Exception as e:
        print(e.__traceback__)
        get_ties()


def proxy_test_loop():
    # 不断的测试代理
    while True:
        proxies = session.query(Proxy).all()
        for proxy in proxies:
            if test_proxy(proxy):
                continue
            session.delete(proxy)
            session.commit()
        time.sleep(300)


def get_proxy():
    # 获取代理
    proxies = requests.get("http://118.24.52.95:5010/get_all/").json()
    proxy_pool = []
    for proxy_ip in proxies:
        if test_proxy(proxy_ip):
            proxy_pool.append(proxy_ip)
            proxy_ips = session.query(Proxy).filter(Proxy.ip == proxy_ip).all()
            if len(proxy_ips) == 0 :
                proxy = Proxy(ip=proxy_ip,occupy=False)
                session.add(proxy)
    session.commit()


def test_proxy(proxy_ip):
    proxies = {
        "http": "http://{}".format(proxy_ip),
        "https": "https://{}".format(proxy_ip),
    }
    try:
        requests.get('http://www.baidu.com', proxies=proxies, timeout=2)
        print('1')
        return True
    except Exception as e:
        print('2')
        return False


def encodeData(data):
    SIGN_KEY = 'tiebaclient!!!'
    s = ''
    keys = data.keys()
    for i in sorted(keys):
        s += i + '=' + str(data[i])
    sign = hashlib.md5((s + SIGN_KEY).encode('utf-8')).hexdigest().upper()
    data.update({'sign': str(sign)})
    return data


def get_fid(bdname):
    # 获取贴吧对用的fourm id
    url = 'http://tieba.baidu.com/f/commit/share/fnameShareApi?ie=utf-8&fname='+str(bdname)
    fid = requests.get(url,timeout=2).json()['data']['fid']
    return fid


def Post(bduss, content, tid, fid, tbname,proxy=None):
    # 网页版回帖
    tbs = get_tbs(bduss)
    headers = {
        'Accept':"application/json, text/javascript, */*; q=0.01",
        'Accept-Encoding':"gzip, deflate, br",
        'Accept-Language':"zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
        'Connection':"keep-alive",
        'Content-Type': "application/x-www-form-urlencoded;charset=UTF-8",
        'Cookie': 'BDUSS='+bduss,
        'DNT':'1',
        'Host':'tieba.baidu.com',
        'Origin': 'https://tieba.baidu.com',
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.71 Safari/537.36',
        'X-Requested-With': 'XMLHttpRequest',
    }
    data = {
        'ie':'utf-8',
        'kw':tbname,
        'fid':fid,
        'tid':tid,
        'tbs':tbs,
        '__type__':'reply',
        'content':content,
    }
    url = 'https://tieba.baidu.com/f/commit/post/add'
    if proxy:
        proxies = {
            "http": "http://{}".format(proxy),
            "https": "https://{}".format(proxy),
        }
        r = requests.post(url=url, data=data, headers=headers, timeout=2, proxies=proxies).json()
    else:
        r = requests.post(url=url, data=data, headers=headers, timeout=2).json()

    return r


def client_Post(bduss, kw, tid, fid, content,proxy=None):
    # 客户端回帖模式
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Cookie': 'ka=open',
        'User-Agent': 'bdtb for Android 9.7.8.0',
        'Connection': 'close',
        'Accept-Encoding': 'gzip',
        'Host': 'c.tieba.baidu.com',
    }

    data = {
        'BDUSS':bduss,
        '_client_type':'2',
        '_client_version':'9.7.8.0',
        '_phone_imei':'000000000000000',
        'anonymous':'1',
        'content':content,
        'fid':fid,
        'from':'1008621x',
        'is_ad':'0',
        'kw':kw,
        'model':'MI+5',
        'net_type':'1',
        'new_vcode':'1',
        'tbs':get_tbs(bduss),
        'tid':tid,
        'timestamp':str(int(time.time())),
        'vcode_tag':'11',
    }
    data = encodeData(data)
    url = 'http://c.tieba.baidu.com/c/c/post/add'
    if proxy:
        proxies = {
            "http": "http://{}".format(proxy),
            "https": "https://{}".format(proxy),
        }
        a = requests.post(url=url, data=data, headers=headers, timeout=2, proxies=proxies).json()
    else:
        a = requests.post(url=url, data=data, headers=headers, timeout=2 ).json()
    return a


def get_tbs(bduss):
    # 获取tbs
    headers = {
        'Host': 'tieba.baidu.com',
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.71 Safari/537.36',
        'Cookie': 'BDUSS=' + bduss,
    }
    url = 'http://tieba.baidu.com/dc/common/tbs'
    return requests.get(url=url,headers=headers).json()['tbs']


def get_mingyan():
    driver.get("https://www.jinrishici.com/#")
    time.sleep(3)
    sen = driver.find_element_by_id('sentence').text
    return sen


def gen_content(barname):
    contents = ['''{}的同学们， 高考模拟报考用格物水滴APP, 查看自己报考排名，与报考者相互交流。祝吧里的高三同学都能有不错的成绩。{}'''.format(barname, get_mingyan()),
                "{}同学们，高考志愿模拟填报用格物水滴app,助你考上理想大学。{}祝高三同学都能发挥最高水平。".format(barname, get_mingyan()),
                "{}同学们，求人不如求己，高考志愿模拟报考快用格物水滴app，看看都谁和自己报考了同一个学校。百度搜索格物水滴。{}，祝福高三同学都能取得高分。".format(barname,
                                                                                                  get_mingyan()),
                "{}的高三同学们，有没有要做网络兼职的？格物水滴在招高考志愿填报模拟APP业务推广员，想了解的可以百度搜索格物水滴了解一下。{}，祝每个人都能上理想大学".format(barname,
                                                                                                      get_mingyan()),
                "{}高三做兼职的同学看过来，百度搜“格物水滴”了解招聘详情！{}，祝高考的同学们都能考上理想大学".format(barname, get_mingyan()),
                "{}同学们，高考分数固然重要，但是报对正确的学校和专业更重要。使用高考志愿模拟报考软件增加自己报考的准确性，试下百度搜索“格物水滴”{}，祝高三同学们取得好成绩".format(barname,
                                                                                                          get_mingyan()),
                ]
    i = random.randint(0,len(contents))
    while True:
        return contents[i]


def clint_send(bduss):
    df = pd.read_sql_table('tie', con)
    bar_names = []
    for i in range(1, len(df)):
        bar_name = df.iat[i, 3]
        if bar_name in bar_names:
            continue
        bar_names.append(bar_name)
        tid = df.iat[i, 2]
        fid = get_fid(bar_name)
        content = gen_content(bar_name)
        client_Post(bduss, bar_name, tid, fid, content, proxy=None)
        time.sleep(181)


def gen_args(bduss):
    df = pd.read_sql_table('tie', con)
    for i in range(1, len(df)):
        bar_name = df.iat[i, 3]
        tid = df.iat[i, 2]
        fid = get_fid(bar_name)
        proxy = session.query(Proxy).filter(Proxy.occupy==False).first()
        proxy.occupy = True
        session.commit()
        content = gen_content(bar_name)
        yield bar_name,tid,fid,bduss,proxy,content


if __name__ == '__main__':
    clint_send(bduss)

