import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
import datetime
import os
import openai

# ========= 1 新闻抓取 =========

def get_eastmoney_news():
    url = "https://finance.eastmoney.com/"
    r = requests.get(url)
    soup = BeautifulSoup(r.text, "html.parser")

    news = []
    for a in soup.select("a")[:10]:
        title = a.text.strip()
        if len(title) > 10:
            news.append(title)

    return news[:5]


def get_cls_news():
    url = "https://www.cls.cn/"
    r = requests.get(url)
    soup = BeautifulSoup(r.text, "html.parser")

    news = []
    for a in soup.select("a")[:10]:
        title = a.text.strip()
        if len(title) > 10:
            news.append(title)

    return news[:5]


def get_bloomberg_news():
    url = "https://www.bloomberg.com/markets"
    r = requests.get(url)
    soup = BeautifulSoup(r.text, "html.parser")

    news = []
    for a in soup.select("a")[:10]:
        title = a.text.strip()
        if len(title) > 10:
            news.append(title)

    return news[:5]


# ========= 2 AI总结 =========

def ai_summary(news_text):

    openai.api_key = os.getenv("OPENAI_API_KEY")

    prompt = f"""
你是一个券商策略分析师，请把下面新闻总结为一份投资晨报。

新闻：
{news_text}

输出格式：
宏观
A股
行业机会
"""

    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":prompt}]
    )

    return response["choices"][0]["message"]["content"]


# ========= 3 发送邮件 =========

def send_email(content):

    sender = os.getenv("25041156@qq.com")
    password = os.getenv("impkhcgtvtxacbdb")
    receiver = sender

    msg = MIMEText(content)
    msg["Subject"] = "AI金融晨报"
    msg["From"] = sender
    msg["To"] = receiver

    server = smtplib.SMTP_SSL("smtp.qq.com",465)
    server.login(sender,password)
    server.sendmail(sender,receiver,msg.as_string())
    server.quit()


# ========= 4 主程序 =========

def main():

    east = get_eastmoney_news()
    cls = get_cls_news()
    bloomberg = get_bloomberg_news()

    all_news = east + cls + bloomberg
    news_text = "\n".join(all_news)

    report = ai_summary(news_text)

    today = datetime.date.today()

    final_report = f"""
AI金融情报系统

日期: {today}

{report}
"""

    send_email(final_report)


if __name__ == "__main__":
    main()
