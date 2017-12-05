#! /user/bin/evn python3
# -*-coding:utf-8 -*-

import math
from PIL import Image, ImageDraw
import random
import copy


# 读取博客的统计数据
def readFile():
    with open('blogdata.txt', 'r')as f:
        lines = [line for line in f]
        # 第一行数据是列名称,去掉第一个blog字样
        colNames = lines[0].replace('\n', '').split('\t')[1:]
        # 每一行的第一个数据是行名称
        rowNames = []
        # data数据不包含每一行的第一列
        data = []
        for i in range(1, len(lines)):
            # 去除换行符合空格
            l = lines[i].replace('\n', '').split('\t')
            # 行名是第一个数据
            rowNames.append(l[0])
            data.append([float(x) for x in l[1:]])

        return colNames, rowNames, data


# 比较数据d1和d2的相似度
def pearson(d1, d2):
    # 求和
    sum1 = sum(d1)
    sum2 = sum(d2)
    # 平方和
    sumSq1 = sum([pow(v, 2) for v in d1])
    sumSq2 = sum([pow(v, 2) for v in d2])

    # 乘积之和
    pSum = sum([d1[i] * d2[i] for i in range(len(d1))])

    num = pSum - (sum1 * sum2 / len(d1))
    den = math.sqrt(((sumSq1 - pow(sum1, 2) / len(d1)) * (sumSq2 - pow(sum2, 2) / len(d2))))

    if den == 0: return 0

    # num/den得到皮尔逊系数,这个数字越大表示两个数据集相似度越高
    # 用1-num/den得到的结果表示两个数据集之间的距离,相似度越高距离越近
    return 1 - num / den


# 毕达哥拉斯距离,即实际距离
def pythagoras(d1, d2):
    return math.sqrt(sum([pow(d1[i] - d2[i], 2) for i in range(len(d1))]))


# 曼哈顿距离,计算在轴上的差值的和
def manhattan(d1, d2):
    return sum([abs(d1[i] - d2[i]) for i in range(len(d1))])


# 用来保存聚合数据的类
# vec 保存聚合数据
# left 是聚合数据的左节点
# right 是聚合数据的右节点
# id 可以用来判断数据是原始数据还是聚合数据,如果是原始数据还可以根据id获取对应的行名称
# distance中保存数据的距离
class bicluster:
    def __init__(self, vec, left=None, right=None, id=None, distance=None):
        self.vec = vec
        self.left = left
        self.right = right
        self.id = id
        self.distance = distance


# 分级聚类,将数据聚合成一个bicluster对象
def hcluster(data, distance=pearson):
    distances = {}
    currentclustId = -1
    # 原始的聚类就是所有数据的集合
    clust = [bicluster(data[i], id=i) for i in range(len(data))]
    # 大循环
    while len(clust) > 1:

        # 默认0/1是每次大循环开始时最近的数据
        # lowestpair保存最近的一组数据,closest保存他们的距离
        lowestpair = (0, 1)
        closest = distance(clust[0].vec, clust[1].vec)
        # 两次循环保证所有数据可以比较
        for i in range(len(clust)):
            for j in range(len(clust)):
                # 不跟自己比
                if i == j: continue
                # 如果当前数据没有计算过才计算,不直接用i,j是因为聚合之后i,j就不跟原始的数据对应了
                if (clust[i].id, clust[j].id) not in distances:
                    distances[(clust[i].id, clust[j].id)] = distance(clust[i].vec, clust[j].vec)

                d = distances[(clust[i].id, clust[j].id)]
                # 当前的比最近的还近,替换
                if d < closest:
                    # 在这个大循环结束之前,i/j组合还可以代表最近的组
                    lowestpair = (i, j)
                    closest = d

        # 获取当前最近组的所有项的平均值
        mergevec = [(clust[lowestpair[0]].vec[i] + clust[lowestpair[1]].vec[i]) / 2 for i in range(len(data[0]))]
        # 构造新的组,这个组中包含了子数据的所有信息
        newclust = bicluster(mergevec, left=clust[lowestpair[0]], right=clust[lowestpair[1]], id=currentclustId,
                             distance=closest)

        # 清除原始数据组,加入新数据
        currentclustId -= 1
        del clust[lowestpair[1]]
        del clust[lowestpair[0]]
        clust.append(newclust)
    print(clust[0])
    return clust[0]


# 获取聚类的高度
def getHeight(bicluster):
    # 是原始数据,高度为1
    if bicluster.left is None and bicluster.right is None:
        return 1
    # 非原始数据,高度是两个子数据高度之和
    else:
        return getHeight(bicluster.left) + getHeight(bicluster.right)


# 获取聚类的误差
def getDepth(bicluster):
    # 原始数据误差为0
    if bicluster.left is None and bicluster.right is None:
        return 0
    # 聚合数据取误差较大者
    else:
        return max(getDepth(bicluster.left), getDepth(bicluster.right)) + bicluster.distance


# 绘制图片
def drawDendrogram(bicluster, labels, jpge='clusters.jpeg'):
    # 设置宽高数据
    h = getHeight(bicluster) * 20
    w = 1200
    depath = getDepth(bicluster)
    # 宽度固定,所有留一点额外的空间
    scaling = float((w - 150) / depath)

    image = Image.new('RGB', (w, h), (255, 255, 255))
    draw = ImageDraw.Draw(image)

    draw.line((0, h / 2, 10, h / 2), (255, 0, 0))

    print('draw start...')
    drawNode(bicluster, draw, 10, h / 2, scaling, labels)
    image.save(jpge, 'JPEG')


# 递归绘制细节
def drawNode(bicluster, draw, x, y, scaling, labels):
    # 原始数据,显示文字即可
    if bicluster.left is None and bicluster.right is None:
        draw.text((x + 5, y - 7), labels[bicluster.id], (0, 0, 0))
    # 聚合数据,根据聚合两个元素的距离来画
    else:
        h1 = getHeight(bicluster.left) * 20
        h2 = getHeight(bicluster.right) * 20
        # 留出两个子元素高度的空隙
        top = y - (h1 + h2) / 2
        bottom = y + (h1 + h2) / 2
        # 画出竖直的线,高度是两个子元素高度的一半
        draw.line((x, top + h1 / 2, x, bottom - h2 / 2), fill=(255, 0, 0))

        # 画出水平的线,宽度是缩放系数X距离
        ll = scaling * bicluster.distance
        draw.line((x, top + h1 / 2, x + ll, top + h1 / 2), fill=(255, 0, 0))
        draw.line((x, bottom - h2 / 2, x + ll, bottom - h2 / 2), fill=(255, 0, 0))

        # 循环,画左右两个子节点
        drawNode(bicluster.left, draw, x + ll, top + h1 / 2, scaling, labels)
        drawNode(bicluster.right, draw, x + ll, bottom - h2 / 2, scaling, labels)


def translateXY(data):
    result = []
    # 获取列数,用此进行循环,每个新的组包含了原来的一列元素
    for x in range(len(data[0])):
        # x代表第x列,y代表第y行,这样把每一列的元素都取出来形成新的数组
        newrow = [data[y][x] for y in range(len(data))]
        # 这样添加的数据,他的列数和他的索引是相同的
        result.append(newrow)

    return result


# colNames, rowNames, data = readFile()
# drawDendrogram(hcluster(data), rowNames)
# drawDendrogram(hcluster(translateXY(data)), colNames, jpge='trans_clusters.jpeg')
# print('end')


# k均值聚类
def kclust(data, rowNames, distance=pearson, k=5):
    # 存一下列数,经常要用
    col_num = len(data[0])
    # 随机列的数据
    randomrows = []
    # 通过k-v的形式存储每个随机聚点下的子数据
    last_clusts = {}
    new_clusts = {}

    # 循环列,拿到每一列的最大值和最小值
    # for x in range(len(data[0])):
    #     # 最大值
    #     col_max = max([row[x] for row in data])
    #     # 最小值
    #     col_min = min([row[x] for row in data])
    #     # 每一列对应的正好是索引
    #     max_min.append((col_max, col_min))
    # 简写如下:
    # 存储每一列的最大值和最小值
    max_min = [(max([row[x] for row in data]), min([row[x] for row in data])) for x in range(col_num)]

    # 随机k个行数据
    for i in range(k):
        # max_min[j][0]-max_min[j][1]表示取最大值和最小值的差值,在用这个值X随机数,在加上最小值
        # 得到了最大值和最小值之间的一个随机值
        # 把上述过程进行列数个次数,就得到了一个随机行
        random_row = [(random.randint(0, 1) * (max_min[j][0] - max_min[j][1]) + max_min[j][1]) for j in range(col_num)]
        randomrows.append(random_row)

    # 大循环进行到数据不再更改
    while True:
        for i in range(k):
            new_clusts[i] = []

        # 拿每一行去跟随机行比,找到最近的,算进他的组里
        for i in range(len(data)):
            # 默认最近的是第一个随机行
            c_index = 0
            closest = distance(data[i], randomrows[c_index])
            for j in range(1, k):
                d = distance(randomrows[j], data[i])
                # 找到了更近的
                if d < closest:
                    c_index = j
                    closest = d
            # 把数据放入最近的聚点的名下
            new_clusts[c_index].append((rowNames[i], data[i]))
        # 如果重新排之后数据没变化,说明已完成,退出循环
        if last_clusts == new_clusts: break
        # 数据复制,直接=的话会一直相同,用copy复制出来
        last_clusts = new_clusts.copy()

        # randomrows.clear()
        # for k in new_clusts:
        #
        #     # 如果组里没东西,过
        #     if new_clusts[k] is None or len(new_clusts[k]) == 0: continue
        #     # 对于组中的每一列,求平均值,形成一个结果组,放进原来的随机组里
        #     randomrows.append(
        #         [sum([row[x] for row in new_clusts[k]]) / len(new_clusts[k]) for x in range(col_num)]
        #     )
        # 简写如下:
        randomrows = [[sum([row[1][x] for row in new_clusts[k]]) / len(new_clusts[k]) for x in range(col_num)] for k in
                      new_clusts if new_clusts[k] is not None and len(new_clusts[k]) != 0]
    return new_clusts


# colNames, rowNames, data = readFile()
# result=kclust(data,rowNames, k=10)
# for i in result:
#     print(result[i])

def scaledown(data, distance=pearson, rate=0.01):
    n = len(data)
    # 记录上次的误差值
    last_err = None
    # 记录数据的真实距离,这是我们的目标结果
    realDis = [[distance(data[j], data[i]) for j in range(n)] for i in range(n)]

    # 每一列随机生成一个坐标点,代表这一列的位置
    rpoints = [[random.random(), random.random()] for i in range(n)]
    # 做一个双层数组存储数据信息
    fakeDis = [[[0.0] for j in range(n)] for i in range(n)]
    while True:
        # 求模拟点之间的距离,视为当前距离
        for i in range(n):
            for j in range(n):
                fakeDis[i][j] = math.sqrt(sum([pow(rpoints[j][x] - rpoints[i][x], 2) for x in range(2)]))

        grad = [[0.0, 0.0] for i in range(n)]

        total_err = 0
        for i in range(n):
            for j in range(n):
                if i == j: continue
                # 记录当前两个点的误差值
                err = (fakeDis[i][j] - realDis[i][j]) / realDis[i][j]
                # i来移动,移动的距离是i,j在x/y轴上的差值/当前距离X误差
                grad[i][0] += ((rpoints[i][0] - rpoints[j][0]) / fakeDis[i][j]) * err
                grad[i][1] += ((rpoints[i][1] - rpoints[j][1]) / fakeDis[i][j]) * err

                total_err += abs(err)

        print(total_err)
        # 移动之后如果会更混乱,则停止
        if last_err is not None and total_err >= last_err: break
        last_err = total_err
        # 根据计算结果移动点的位置
        for i in range(n):
            rpoints[i][0] -= grad[i][0] * rate
            rpoints[i][1] -= grad[i][1] * rate

    return rpoints


def drawPoints(points, labels, jpeg='sdc.jpeg'):
    # 白色背景图
    image = Image.new('RGB', (2000, 2000), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    # 取出移动完毕的点,拿到相应的名称显示出来
    for i in range(len(points)):
        x = points[i][0] * 1000
        y = points[i][1] * 1000
        draw.text((x, y), labels[i], fill=(0, 0, 0))
    image.save(jpeg)


# colNames, rowNames, data = readFile()
# drawPoints(scaledown(data), rowNames)


def tanimoto(d1, d2):
    # r1/r2表示d1/d2中的非无数据个数,sr表示交集个数,此处我采用0表示没有数据,1表示有
    r1, r2, sr = 0, 0, 0

    for i in range(len(d1)):
        if d1[i] == 1:
            r1 += 1
        if d2[i] == 1:
            r2 += 1
        if d1[i] == d2[i]:
            sr += 1
    # sr/(r1+r2-sr)得到的数据越大说明相似度越高,但是不利于我们看距离,
    # 所以用1-sr/(r1+r2-sr)来表示距离,值越小说明距离越近,相似度越高
    return 1.0-float(sr / (r1 + r2 - sr))


# 课后作业

# 毕达哥拉斯距离进行分级聚类
colNames, rowNames, data = readFile()
# drawDendrogram(hcluster(data, pythagoras), rowNames, jpge='pycluster.jpeg')
drawDendrogram(hcluster(data, manhattan), rowNames, jpge='mcluster.jpeg')
