from urllib.request import urlopen
from bs4 import BeautifulSoup
from urllib.parse import quote
import random
import time
import hashlib
import re
import requests
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from database import Bar, Base,Tie,Customer

# data
engine = create_engine('sqlite:///newtiebar.sqlite')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

# webdriver
chrome_options = Options()
chrome_options.add_argument(
    '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36')
# chrome_options.add_argument('--headless')
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
        b = Bar(name=barName, kind="daxue", hassend=False)
        session.add(b)
        session.commit()

    for barName in get_all_ba_name('中小学'):
        if '高' in barName or '中' in barName:
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


def get_tie(bar_name, kw, pn):
    driver.get(url='http://tieba.baidu.com/f?kw={}&ie=utf-8&pn={}'.format(bar_name, pn))
    time.sleep(3)
    save_tie(bar_name, kw)
    driver.close()


def save_tie(bar_name,kw):
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
            for i in range(4):
                pn = i * 50
                get_tie(gaozhong.name, '高考', pn)

        daxues = session.query(Bar).filter(Bar.kind =="daxue").all()
        for daxue in daxues:
            for i in range(4):
                pn = i * 50
                get_tie(daxue.name, '报考', pn)
    except Exception as e:
        print(e)
        get_ties()





if __name__ == '__main__':
    get_ties()

