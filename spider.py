import time
import json
import re
import random
from DrissionPage import Chromium, ChromiumOptions

from font_decoder import ShixisengDecoder


# 私有区字符：字体解密之后理论上不该再有，留作兜底清理
PUA_RE = re.compile(r'[\x00-\x1F\x7F-\x9F\uE000-\uF8FF]')
# 薪资：150/天、120-200/天、3-5千/月
SALARY_RE = re.compile(r'(\d+(?:\.\d+)?(?:\s*-\s*\d+(?:\.\d+)?)?\s*[千万]?\s*/\s*[天月])')


class ShixisengSpider:
    def __init__(self):
        options = ChromiumOptions()
        # options.set_browser_path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")
        options.set_argument('--disable-blink-features=AutomationControlled')

        self.chrome = Chromium(addr_or_opts=options)
        self.tab = self.chrome.latest_tab

        # 多个关键词的数据合并保存
        self.all_jobs_set = set()
        self.all_jobs = []

    def build_decoder(self):
        """每页重新建一次：实习僧每次请求都会换一套字体，字典不能跨页复用。"""
        try:
            decoder = ShixisengDecoder.from_browser(self.tab)
        except Exception as e:
            print(f"⚠️ 字体解密器构造失败：{type(e).__name__}: {e}")
            return None

        if len(decoder) == 0:
            print("⚠️ 本页没拿到字体字典，文本将保留乱码（检查 @font-face 或网络）")
            return None

        print(f"🔑 字体字典 {len(decoder)} 条（模式：{decoder.mode}）")
        return decoder

    def crawl(self, keyword, max_pages=15):
        print(f"\n========== 正在抓取关键词: {keyword} ==========")

        for page in range(1, max_pages + 1):
            url = f"https://www.shixiseng.com/interns?keyword={keyword}&city=%E5%85%A8%E5%9B%BD&type=intern&page={page}"
            print(f"正在抓取第 {page} 页...")

            self.tab.get(url)

            # 防封核心：每页随机休眠 4 到 8 秒，模拟真人
            sleep_time = random.uniform(4, 8)
            print(f"⏳ 防封休眠 {sleep_time:.2f} 秒...")
            time.sleep(sleep_time)

            # 🌟 字体解密：必须在取卡片文本之前建好，否则拿到的是私有区乱码
            decoder = self.build_decoder()

            job_cards = self.tab.eles('xpath://div[contains(@class, "intern-item")]')
            print(f"🎯 本页找到 {len(job_cards)} 个职位卡片")

            if len(job_cards) == 0:
                print("⚠️ 没有找到卡片了，触发反爬或到底了，直接停止该关键词的抓取。")
                break

            for card in job_cards:
                try:
                    card_all_text = card.text
                    # 🌟 先把假字换成真字，再拆行；否则标题、薪资全是 U+E0xx
                    if decoder is not None:
                        card_all_text = decoder.decode(card_all_text)

                    lines = [line.strip() for line in card_all_text.split('\n') if line.strip()]
                    if not lines:
                        continue

                    raw_text = "，".join(lines)

                    # 解密后只剩控制字符和零星的图标字体，清一遍就行
                    # 第一行是「标题 + 薪资」连在一起的，先把薪资切掉再当标题
                    clean_title = SALARY_RE.sub('', PUA_RE.sub('', lines[0])).strip()
                    real_title = clean_title[:30] if clean_title else "未知岗位"
                    real_city = lines[1].split('|')[0].strip() if len(lines) > 1 else "未知"
                    real_company = lines[2] if len(lines) > 2 else "未知"

                    m = SALARY_RE.search(raw_text)
                    if m:
                        real_salary = m.group(1).replace(' ', '')
                    elif "面议" in raw_text:
                        real_salary = "面议"          # 字节/小红书这类大厂实习常见
                    else:
                        real_salary = "见详情"

                    job_data = {
                        "raw_text": f"招聘信息如下：{raw_text}",
                        "title": real_title,
                        "company": real_company,
                        "salary": real_salary,
                        "city": real_city
                    }

                    # 去重校验
                    unique_id = f"{real_company}_{real_title}_{real_city}"
                    if unique_id not in self.all_jobs_set:
                        self.all_jobs_set.add(unique_id)
                        self.all_jobs.append(job_data)
                        print(f"  ✅ 新增: {real_title} | {real_company} | {real_city} | {real_salary}")

                except Exception as e:
                    pass

            # 每翻完一页，就保存一次文件
            with open("raw_scraped_data.json", "w", encoding="utf-8") as f:
                json.dump(self.all_jobs, f, ensure_ascii=False, indent=4)
            print(f"💾 当前总累计保存 {len(self.all_jobs)} 条不重复数据。")


if __name__ == "__main__":
    spider = ShixisengSpider()

    # 🌟 多关键词火力覆盖，每个词抓 15 页
    # 15页 * 20条 * 6个词 = 1800 条潜在数据！
    keywords = ["Python", "Java", "前端", "数据分析", "算法", "测试"]

    for kw in keywords:
        spider.crawl(keyword=kw, max_pages=15)
        # 关键词之间也休息一下，别被彻底封杀
        print("切换关键词，休眠 10 秒...")
        time.sleep(10)

    print(f"\n🎉 终极抓取完毕！共获取 {len(spider.all_jobs)} 条海量真实数据！")
