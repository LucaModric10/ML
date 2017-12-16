#! /user/bin/evn python3
# -*-coding:utf-8 -*-

from mysql import connector
from math import tanh


class searchnet():
    def __init__(self):
        self.conn = connector.connect(user='root', password='wangweijie0', database='wwj')
        self.cursor = self.conn.cursor()

    def __del__(self):
        if self.conn:
            self.conn.close

    # 建表
    def createtable(self):
        # self.cursor.execute(
        #     'create table inputhidden(`id` integer not null auto_increment,`fromid` varchar(80) not null,`toid` varchar(80) not null,`strength` float not null,primary key (`id`))auto_increment=1')
        # self.cursor.execute(
        #     'create table hiddenoutput(`id` integer not null  auto_increment,`fromid` varchar(80) not null,`toid` varchar(80) not null,`strength` float not null,primary key (`id`))auto_increment=1')
        self.cursor.execute(
            'create table hiddennode(`id`integer not null auto_increment, `createkey` varchar(80) not null,primary key (`id`))auto_increment=1')

        self.conn.commit()

    # 获取链接强度,即链接权重
    def getstrength(self, fromid, toid, layer):
        # 输入-隐藏,sd(strength-default)是默认strength
        if layer == 0:
            tablename, sd = 'inputhidden', -0.2
            self.cursor.execute('select strength from inputhidden where fromid = %s and toid = %s', (fromid, toid))
            res = self.cursor.fetchone()
            if res is None:
                return sd
            return res[0]
        # 隐藏-输出
        elif layer == 1:
            tablename, sd = 'hiddenoutput', 0
            self.cursor.execute('select strength from hiddenoutput where fromid = %s and toid = %s', (fromid, toid))
            res = self.cursor.fetchone()
            if res is None:
                return sd
            return res[0]

    # 设置链接强度
    def setstrength(self, fromid, toid, strength, layer):
        # 输入-隐藏
        if layer == 0:
            tablename = 'inputhidden'
            self.cursor.execute('select strength from inputhidden where fromid=%s and toid=%s',
                                (fromid, toid))
            res = self.cursor.fetchone()
            # 无数据,插入数据
            if res is None:
                self.cursor.execute('insert into inputhidden(`fromid`,`toid`,`strength`) values(%s,%s,%s)',
                                    (fromid, toid, strength))
            # 有数据,更新
            else:
                self.cursor.execute('update inputhidden set strength=%s where fromid=%s and toid=%s',
                                    (strength, fromid, toid))
        # 隐藏-输出
        elif layer == 1:
            tablename = 'hiddenoutput'
            self.cursor.execute('select strength from hiddenoutput where fromid=%s and toid=%s',
                                (fromid, toid))
            res = self.cursor.fetchone()
            # 无数据,插入数据
            if res is None:
                self.cursor.execute('insert into hiddenoutput(`fromid`,`toid`,`strength`) values(%s,%s,%s)',
                                    (fromid, toid, strength))
            # 有数据,更新
            else:
                self.cursor.execute('update hiddenoutput set strength=%s where fromid=%s and toid=%s',
                                    (strength, fromid, toid))
        self.conn.commit()

    # 建立链接网
    def generatehiddennode(self, words, urls):
        if len(words) > 3: return None
        # 通过排序保证key的唯一性
        createkey = ' '.join(sorted([str(word) for word in words]))
        self.cursor.execute('select id from hiddennode where createkey=%s ', (createkey,))
        res = self.cursor.fetchone()
        # 当前节点尚未建立,建立节点,设置权重(连接强度)
        if res is None:
            # 新建隐层节点
            self.cursor.execute('insert into hiddennode(`createkey`) values(%s)', (createkey,))
            for word in words:
                self.setstrength(word, createkey, 1 / len(words), 0)

            for url in urls:
                self.setstrength(createkey, url, 0.1, 1)

            self.conn.commit()

    # 获取所有和输入层,输出层相关的隐藏节点
    def getallhiddenids(self, words, urls):
        ll = {}
        createkey = ' '.join(sorted([str(word) for word in words]))
        for word in words:
            self.cursor.execute('select toid from inputhidden where fromid=%s', (word,))
            for row in self.cursor.fetchall(): ll[row[0]] = 1

        for url in urls:
            cur = self.cursor.execute('select fromid from hiddenoutput where toid=%s', (url,))
            for row in self.cursor.fetchall(): ll[row[0]] = 1

        return list(ll.keys())

    # 建立链接矩阵
    def setupnetword(self, words, urls):
        self.words = words
        self.urls = urls
        self.hiddens = self.getallhiddenids(words, urls)

        # 初始化输出数据,默认输出都是1,wio,who,woo分别代表输入层,隐藏层,输出层的输出
        self.wio = [1.0] * len(self.words)
        self.who = [0.0] * len(self.hiddens)
        self.woo = [0.0] * len(self.urls)

        # 初始化权重矩阵,ih,ho分别代表输入层到隐藏层和隐藏层到输出层
        # 在矩阵中,隐藏层代表列名,输入输出都是行名
        self.ih = [[self.getstrength(fromid, toid, 0) for toid in self.hiddens] for fromid in self.words]
        self.ho = [[self.getstrength(fromid, toid, 1) for fromid in self.hiddens] for toid in self.urls]

    # 前馈算法,计算输出值
    def feedfoward(self):
        for i in range(len(self.words)):
            # 输入层的输出结果默认为1
            self.wio[i] = 1
        # 对每一个隐藏层,计算到这个输隐藏层的输入,再通过tanh函数计算出输出
        # j代表这是第几列,列名是隐藏层节点的名字
        for j in range(len(self.hiddens)):
            sum = 0
            # i代表第几行,行名输入层/输出层名字
            # 这里对某个隐藏节点的所有输入与连接强度的乘积求和,得到隐藏节点的输入
            for i in range(len(self.words)):
                sum += self.wio[i] * self.ih[i][j]
            # 利用激活函数求得输出
            self.who[j] = tanh(sum)
        # 同上,计算输出层的输出
        for i in range(len(self.urls)):
            sum = 0
            for j in range(len(self.hiddens)):
                sum += self.who[j] * self.ho[i][j]
            # 利用激活函数求得输出
            self.woo[i] = tanh(sum)
        return self.woo[:]

    # 根据输入的字符和urls,算出比重
    def getreslut(self, words, urls):
        # 建立矩阵,前馈算法计算输出值
        self.setupnetword(words, urls)
        return self.feedfoward()

    # 反向传播,训练机器,改变链接权重
    def backpropagate(self, targets, N=0.5):
        # 计算输出层的误差,这个误差也就是输出层的输入误差
        ho_deviation = [0.0] * len(self.urls)
        for i in range(len(targets)):
            # 体现在最终输出的误差
            error = targets[i] - self.woo[i]
            # 反函数求输出层的输入值并计算误差
            ho_deviation[i] = self.dtanh(self.woo[i]) * error
        # 根据输出层误差计算隐藏层误差,这个误差是隐藏层的输入误差
        ih_deviation = [0.0] * len(self.hiddens)
        for j in range(len(self.hiddens)):
            for i in range(len(self.urls)):
                error = 0
                # 把误差按当前各个神经元的传递损耗分配下去,计算一个隐藏层的全部误差
                # 通过这个损耗,已经把输出层的输入转化成了隐藏层的输出
                error += ho_deviation[i] * self.ho[i][j]
            # 对当前隐藏层的输出求反,得到了隐藏层输入,进而求得隐藏层输入误差
            ih_deviation[j] = self.dtanh(self.who[j]) * error

        # 修改隐藏层到输出层之间的连接强度
        for j in range(len(self.hiddens)):
            for i in range(len(self.urls)):
                # 应该修改的值是隐藏层的输出值*误差
                change = self.who[j] * ho_deviation[i]
                # N代表学习效率/成功率
                self.ho[i][j] += N * change
        # 修改输入层到隐藏层之间的链接强度
        for j in range(len(self.hiddens)):
            for i in range(len(self.words)):
                # 根据隐藏节点的误差求得输入层到隐藏层的误差
                change = self.wio[i] * ih_deviation[j]
                self.ih[i][j] += N * change

    def updateData(self):
        for j in range(len(self.hiddens)):
            for i in range(len(self.urls)):
                self.cursor.execute('update hiddenoutput set strength=%s where fromid=%s and toid=%s',
                                    (self.ho[i][j], self.hiddens[j], self.urls[i]))

        for j in range(len(self.hiddens)):
            for i in range(len(self.words)):
                self.cursor.execute('update inputhidden set strength=%s where fromid=%s and toid=%s',
                                    (self.ih[i][j], self.words[i], self.hiddens[j]))

        self.conn.commit()

    def train(self, words, urls, target):
        # 生成节点
        # 建立连接矩阵
        # 获取链接强度
        # 在反向训练之前调用前馈算法,这样可以计算好所有输出值
        # 根据target生成输出层输出结果,反向传播修改矩阵数据
        # 修改数据(输入层-隐藏层和隐藏层-输出层都要修改)
        self.generatehiddennode(words, urls)
        self.setupnetword(words, urls)
        self.feedfoward()
        targets = [0.0] * len(urls)
        targets[urls.index(target)] = 1
        self.backpropagate(targets)
        self.updateData()

    # 求原始值
    def dtanh(self, y):
        return 1 - tanh(y) * tanh(y)


se = searchnet()
for i in range(10):
    se.train(['机器', '学习'], ['机器', '学习', '机器学习'], '机器学习')
    print(se.getreslut(['机器', '学习'], ['机器', '学习', '机器学习']))

print(se.getreslut(['机器'], ['机器', '学习', '机器学习']))
