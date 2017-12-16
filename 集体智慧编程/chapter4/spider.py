#! /user/bin/evn python3
# -*-coding:utf-8 -*-
from bs4 import BeautifulSoup
import requests
from urllib import parse
import re
import logging
from mysql import connector

logging.basicConfig(level=logging.INFO)


# 爬取网址
def getUrls(url_start='https://en.wikipedia.org/wiki/Tiger'):
    url_base = 'https://en.wikipedia.org'
    urls, allurls, newurls = set(), set(), set()
    urls.add(url_start)
    allurls.add(url_start)
    for i in range(1):
        for url_resource in urls:
            try:
                res = requests.get(url_resource, timeout=2)
                # 只看正文下的内容
                links = BeautifulSoup(str(BeautifulSoup(res.content, 'lxml')('div', id='bodyContent')), 'lxml')('a')
                for link in links:
                    if 'href' in dict(link.attrs):
                        link_to = link['href']
                        # 外链和本文连接直接忽略
                        if link_to.startswith('http') or link_to.startswith('#'): continue
                        url = parse.urljoin(url_base, link_to)
                        if url.find("'") != -1: continue
                        url = url.split('#')[0]
                        newurls.add(url)
            except:
                pass
        urls = newurls.copy()
        allurls.update(newurls)
    with open('urls.txt', 'w') as f:
        for item in allurls:
            try:
                f.write(item + '\n')
            except:
                pass


def readUrls():
    with open('urls.txt', 'r') as f:
        urls = f.read().split('\n')
        return urls


def getUrlId(conn, cursor, url):
    # 查询当前url地址在表中的位置
    cursor.execute('select id from urllist where url=%s', (url,))
    urlid = cursor.fetchone()
    # 如果没有,新增并重新获取urlid
    if urlid is None:
        cursor.execute('insert into urllist(`url`) values(%s)', (url,))
        conn.commit()
        cursor.execute('select id from urllist where url=%s', (url,))
        urlid = cursor.fetchone()
    return urlid[0]


# 根据url地址爬取相关数据,并写入数据库
def parseData(urls):
    conn = connector.connect(user='root', password='wangweijie0', database='wwj')
    cursor = conn.cursor()
    worldid = 1
    ignores = ['a', 'and', 'it', 'or', 'of', 'to', 'is', 'in', 'and', 'but', 'the', 'ma']
    # 循环urlid
    for url in urls:
        try:
            res = requests.get(url, timeout=2)

            urlid = getUrlId(conn, cursor, url)
            soup = BeautifulSoup(str(BeautifulSoup(res.content, 'lxml')('div', id='bodyContent')), 'lxml')
            splitter = re.compile('\\W+')
            words = [t.lower() for t in splitter.split(soup.get_text()) if
                     t != '' and t not in ignores]
            # 单词入库
            for position in range(len(words)):
                # 写库
                cursor.execute('insert into wordlist(`word`,`urlid`)values(%s,%s)', (words[position], urlid))
                cursor.execute('insert into wordlocation(`urlid`,`wordid`,`position`)values(%s,%s,%s)', (
                    urlid, worldid, position + 1))
                worldid += 1
            conn.commit()

            # 只看正文下的内容
            links = soup('a')
            for link in links:
                if 'href' in dict(link.attrs):
                    link_to = link['href']
                    # 外链和本文连接直接忽略
                    if link_to.startswith('http') or link_to.startswith('#'): continue
                    link_url = parse.urljoin('https://en.wikipedia.org', link_to)
                    if link_url.find("'") != -1: continue
                    link_url = link_url.split('#')[0]
                    linkid = getUrlId(conn, cursor, link_url)

                    cursor.execute('insert into link(`fromid`,`toid`)values(%s,%s)', (urlid, linkid))
                    # 查询当前href的字在word中而id不再linkwords中的第一个
                    cursor.execute(
                        'select ws.id from wordlist ws where ws.urlid=%s and ws.word=%s ',
                        (urlid, link.text))
                    wordids = cursor.fetchall()
                    if wordids is not None and len(wordids) > 0:
                        for wordid in wordids:
                            cursor.execute('select lw.wordid from linkwords lw where lw.wordid=%s ', (wordid[0],))
                            r = cursor.fetchone()
                            if r is None or len(r) == 0:
                                cursor.execute('insert into linkwords(`wordid`,`linkid`)values(%s,%s)',
                                               (wordid[0], linkid))
                                conn.commit()
                                break

            conn.commit()
        except BaseException as e:
            conn.rollback()

    cursor.close()
    conn.close()


parseData(readUrls())
