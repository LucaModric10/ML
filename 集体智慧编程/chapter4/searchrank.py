#! /user/bin/evn python3
# -*-coding:utf-8 -*-
from mysql import connector
from functools import reduce


class search():
    def __init__(self):
        self.conn = connector.connect(user='root', password='wangweijie0', database='wwj')
        self.cursor = self.conn.cursor()

    def __del__(self):
        if self.conn:
            self.conn.close

    # 查询的入口,kw是关键字字符串,以空格分割
    def searchK(self, kw):
        kw.lower()
        words = kw.split(' ')
        self.result = {}
        for word in words:
            self.cursor.execute('select w.urlid,u.url from wordlist w,urllist u where w.word=%s and u.id=w.urlid',
                                (word,))
            # 查到所有连接的urlid
            urlids = self.cursor.fetchall()
            self.result[word] = urlids
        self.data = self.handledata()
        if len(self.data) == 0:
            print('无查询结果')
        else:
            self.getscoredlist()

    # 计算总分数排行
    def getscoredlist(self):
        totalScores = {}
        weight_score = [(1, self.disscore(type='position'))]
        for weight, scores in weight_score:
            for url, score in scores.items():
                totalScores.setdefault(url, 0)
                totalScores[url] += score * weight

        res = self.urlid2url(totalScores)
        res.sort()
        res.reverse()
        print(res)

    # 把数据都转化到0-1之间
    def nomalizescores(self, scores, smallbetter=True):
        vsamll = 0.00001
        # 小了好,小的分数高,小的当分子即可
        if smallbetter:
            minscore = min(scores.values())
            res = [(float(minscore) / max(vsamll, v), k) for k, v in scores.items()]
        # 大了好,大的分数高,大的当分母即可
        else:
            maxscore = max(scores.values())
            # 避免分母是0
            if maxscore == 0: maxscore = vsamll
            res = [(float(v) / maxscore, k) for k, v in scores.items()]

        return dict(res)

    #  根据出现次数打分,多个单词的话以出现次数之和算
    def countscore(self):
        return self.nomalizescores(self.data, smallbetter=False)

    # 根据单词之间的距离/单词位置计算
    # 其实可以把单词位置记录在单词表,可以一起查出来结果,比这样效率高得多
    # type记录计算距离还是计算位置
    def disscore(self, type='distance'):
        # 按单词之间距离来
        if type == 'distance':
            fn = lambda m, n: m - n
        # 按单词的位置来
        else:
            fn = lambda m, n: m + n

        if len(self.result) == 1:
            return 1
        positions = dict([(item, {}) for item in self.data])
        totalscores = {}
        for urlid in self.data:
            for word in self.result:
                self.cursor.execute(
                    'select wl.position from wordlocation wl,wordlist w where w.word=%s and w.urlid=%s and wl.wordid=w.id',
                    (word, urlid))
                p = self.cursor.fetchall()
                positions[urlid][word] = [item[0] for item in p]
        # item是url,ps中包含了url中的关键字和出现的位置
        for item, ps in positions.items():
            totalscores.setdefault(item, 9999)
            # 每次取两个关键字比较
            for k1 in ps:
                for k2 in ps:
                    # 不比较一样的关键字
                    if k1 == k2: continue
                    # 取两个关键字的所有值比较,取到差最小或者和最小的一对,记录
                    # 由于关键字可能不止两个,所以两两计算的结果加在一起作为最终的结果
                    totalscores[item] += min([min([abs(fn(m, n)) for m in ps[k1]]) for n in ps[k2]])
        return self.nomalizescores(totalscores, smallbetter=True)

    # 处理数据,返回共有的url和这些url出现的次数
    def handledata(self):
        # 记录原始数据,但是把数据元素从[(1,),(2,)]变成了[1,2]
        data2 = self.result.copy()
        # 记录新数据,新数据之中去除了重复的url
        newdata = {}
        for word, urls in data2.items():
            urlids = [u[0] for u in urls]
            # 把所有元素添加进来
            urlset = []
            for urlid in urlids:
                if urlid not in urlset:
                    urlset.append(urlid)
            newdata[word] = urlset
        # 通过reduce函数,把新数据中的value变成set并求交集,之后在变回list,这样得到了两个的交集
        urllist = list(reduce(lambda x, y: set(x) & set(y), [newdata[item] for item in newdata]))
        # 计算交集url出现的次数
        return dict([(k, sum([data2[word].count(k) for word in data2])) for k in urllist])

    # 把scores里的urlid换成url
    def urlid2url(self, totalScores):
        # 变换url的字典
        rt = tuple(self.result.values())
        url_trans = dict(list(reduce(lambda x, y: set(x) | set(y), rt)))
        return [(score, url_trans[urlid]) for score, urlid in totalScores.items()]

    # 计算网页分值
    def pagerank(self):
        self.cursor.execute('select id from urllist')
        urlidlist = [item[0] for item in self.cursor.fetchall()]
        self.cursor.execute('select toid,fromid from link')
        linklist = self.cursor.fetchall()
        # todata里放着所有指向这个链接的urlid
        todata = {}
        # fromdata放着所有此链接指向的链接的数量
        fromdata = {}
        for item in linklist:
            todata.setdefault(item[0], [])
            todata[item[0]].append(item[1])
            fromdata.setdefault(item[1], 0)
            fromdata[item[1]] += 1
        # 初始化所有rank为1
        ranks = dict([(urlid, 1) for urlid in urlidlist])
        # 循环30次计算pagerank,基本可以保证接近现实
        for i in range(30):
            for urlid, fl in todata.items():
                ranks[urlid] = 0.15 + 0.85 * sum([float(ranks[fromid]) / fromdata[fromid] for fromid in fl])
        for urlid in ranks:
            self.cursor.execute('update urllist set rank=%s where id=%s', (ranks[urlid], urlid))

        self.conn.commit()

se=search()
se.searchK('big cat')
