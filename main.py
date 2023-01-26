import logging
import random
import re
import json
import time
import urllib.parse
import warnings
import csv

import requests
from lxml import etree

warnings.filterwarnings("ignore")

SHOP_REGULAR = "item.jd.com/([0-9]*).html"
RE_SHOP_PATTERN = re.compile(pattern=SHOP_REGULAR)

RE_GET_DICT_PATTERN = re.compile("{.*}")
RE_DEL_HTML_PATTERN = re.compile("<[^>]*>")


class Parse:
    @staticmethod
    def url_encode(s: str):
        return urllib.parse.quote(s)

    @staticmethod
    def decode_shop_list(response, goods: dict):
        tree = etree.HTML(response.text)
        for url_list in tree.xpath('//*[@id="J_goodsList"]//@href'):
            good = RE_SHOP_PATTERN.search(url_list)
            if good:
                try:
                    if good.group(1) not in goods:
                        good_id = good.group(1)
                        good_url = good.group()
                        goods[good_id] = {"url": good_url}
                except Exception as e:
                    logging.debug("cannot get goods url", goods)
        return goods

    @staticmethod
    def decode_good_info(response, goods: dict, good_id):
        res = RE_GET_DICT_PATTERN.search(response.text)
        if res:
            try:
                stock_info = json.loads(res.group())
                goods[good_id]["price"] = stock_info["price"]["p"]
                goods[good_id]["title"] = stock_info["wareInfo"]["wname"]
                goods[good_id]["shopName"] = stock_info["shopInfo"]["shop"]["name"]
            except Exception as e:
                raise ValueError("一会再爬吧 请求频率过高了") from None

    @staticmethod
    def sales_sub(s):
        res = RE_DEL_HTML_PATTERN.sub("", s)
        s = s if not res else res
        return s


class JDCrawler:
    def __init__(self, keyword: str):
        self.keyword = Parse.url_encode(keyword)
        self.goods = dict()
        self.request = requests.Session()
        self.csv_opea = CsvOp()

    def get_shop_list(self, page: int, cookie: str):
        url = f"https://search.jd.com/search?keyword={self.keyword}&page={page}"
        useragent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 "
            "Safari/537.36 "
        )
        self.request.method = "get"
        self.request.headers = {"cookie": cookie, "user-agent": useragent}
        response = self.request.request(method="get", url=url)

        Parse.decode_shop_list(response, goods=self.goods)

    def get_goods_detail(self):
        for i, good_id in enumerate(self.goods.keys()):
            print(f"正在获取{good_id}")
            jq_id = random.randint(9000000, 9999999)
            url = f"https://item-soa.jd.com/getWareBusiness?callback=jQuery{jq_id}&skuId={good_id}"
            response = self.request.request(method="get", url=url)
            Parse.decode_good_info(response, self.goods, good_id=good_id)
            time.sleep(random.randint(1, 3))
            self.csv_opea.to_csv(goods=self.goods)

    def start(self, cookie, page):
        for i in range(1, page + 1):
            self.get_shop_list(cookie=cookie, page=page)
            self.get_goods_detail()


class CsvOp:
    init_file = False

    def __init__(self):
        with open("goodsInfo.csv", "w+") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["链接地址", "店铺名称", "商品名称", "价格"])
            self.init_file = True

    def to_csv(self, goods: dict):
        print(goods)
        with open("goodsInfo.csv", "a+") as csvfile:
            writer = csv.writer(csvfile)
            if not self.init_file:
                writer.writerow(["链接地址", "店铺名称", "商品名称", "价格"])
            # 写入多行用writerows
            try:
                for good in goods.values():
                    writer.writerows(
                        [
                            good["url"],
                            good["shopName"],
                            good["title"],
                            good["price"],
                        ]
                    )
            except Exception as e:
                logging.info("to csv error", e)


if __name__ == "__main__":
    # 复制jd ck
    # exp
    """

          JD CK
     例子：

    "__jdu=123; shshshfpa=; shshshfpb=test; qrsc=1; ipLocation=test; '

    """

    example_ck = "__jdu=123; shshshfpa=uuid; shshshfpb=test; qrsc=1; ipLocation=test; "
    cookie = example_ck

    keyword = "test"
    jd = JDCrawler(keyword=keyword)

    # page = (1~page) 获取从1到 page 页
    page = 1
    jd.start(cookie=cookie, page=page)
