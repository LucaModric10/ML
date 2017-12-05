#! /user/bin/evn python3
# -*-coding:utf-8 -*-
from bs4 import BeautifulSoup
import requests


def getUrls(url):
    pages, newpages, allpages = set(), set(), set()
    pages.add(url)
    for page in pages:
        res = requests.get(page)
        soup = BeautifulSoup(res.text, 'lxml')
        links=soup('a')



def test():
    a=[1,2,3]
    b=[4,5,6]
    for i in range(len(a)):
        print(str(a[i]))
        if i==len(a)-2:
            a=b

test()
