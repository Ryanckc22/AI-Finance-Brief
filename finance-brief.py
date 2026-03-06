import feedparser
import akshare as ak
from datetime import datetime
from openai import OpenAI
import smtplib
from email.mime.text import MIMEText
import os

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

def get_news():

    sources = [
        "https://www.reuters.com/markets/rss",
        "https://rsshub.app/sina/finance"
    ]

    news = []

    for url in sources:
        feed = feedparser.parse(url)
        for entry in feed.entries[:5]:
            news.append(entry.title)

    return news

def get_market_data():

    index = ak.stock_zh_index_daily(symbol="sh000300")
    latest = index.iloc[-1]

    return f"沪深300最新收盘价 {latest['close']}"

def ai_summary(news, market):

    text = "\n".join(news)

    prompt = f"""
以下是最新财经新闻：

{text}

A股市场数据：
{market}

请生成一份投资晨报：

结构：
宏观
国际股市
A股市场
行业机会
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":prompt}]
    )

    return response.choices[0].message.content

def send_email(content):

    sender = os.environ["EMAIL_USER"]
    password = os.environ["EMAIL_PASS"]
    receiver = os.environ["EMAIL_USER"]

    msg = MIMEText(content,"plain","utf-8")

    msg["Subject"] = f"AI投资晨报 {datetime.now().date()}"
    msg["From"] = sender
    msg["To"] = receiver

    server = smtplib.SMTP_SSL("smtp.gmail.com",465)

    server.login(sender,password)
    server.sendmail(sender,[receiver],msg.as_string())

    server.quit()

news = get_news()

market = get_market_data()

summary = ai_summary(news, market)

send_email(summary)
