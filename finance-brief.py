import requests
import datetime
import smtplib
from email.mime.text import MIMEText
import os
import openai
import yfinance as yf

# ===== 北向资金监控 =====
def northbound_funds():
    url = "http://push2.eastmoney.com/api/qt/kamt/north?fields=f12,f14,f2,f3"
    try:
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        data = r.json()["data"]["list"]
        result = []
        for i, item in enumerate(data[:10], 1):
            name = item["f14"]
            net = item["f2"]
            percent = item["f3"]
            result.append(f"{i}. {name}: 净买入 {net} 万元, 占比 {percent}%")
        return result
    except Exception as e:
        return [f"北向资金数据抓取失败: {e}"]

# ===== 龙虎榜监控 =====
def longhubang():
    url = "http://push2.eastmoney.com/api/qt/stock/getsuspension?fields=f12,f14,f2,f3"
    try:
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        data = r.json().get("data", [])
        result = []
        for i, item in enumerate(data[:10], 1):
            name = item.get("f14", "未知")
            reason = item.get("f12", "未知原因")
            result.append(f"{i}. {name}: {reason}")
        return result
    except Exception as e:
        return [f"龙虎榜数据抓取失败: {e}"]

# ===== 美股科技股监控 =====
def us_tech_stocks():
    symbols = ["NVDA", "MSFT", "TSLA"]
    result = []
    for i, s in enumerate(symbols, 1):
        try:
            stock = yf.Ticker(s)
            data = stock.history(period="1d")
            last = data["Close"].iloc[-1]
            change = last - data["Open"].iloc[-1]
            result.append(f"{i}. {s}: 收盘价 {last:.2f}, 涨跌 {change:.2f}")
        except Exception as e:
            result.append(f"{i}. {s} 数据抓取失败: {e}")
    return result

# ===== AI策略生成 =====
def ai_report(data_text):
    openai.api_key = os.getenv("OPENAI_API_KEY")
    prompt = f"""
你是资深券商策略首席分析师。

请根据以下市场数据生成投资策略报告：
{data_text}

要求：
1. 每条北向资金、龙虎榜、美股数据必须被分析并引用具体数值。
2. 每条分析必须包含股票/板块名称和涨跌或净买入金额。
3. 报告结构：宏观环境 / 全球市场 / A股市场 / 行业机会 / 投资风险。
4. 禁止任何模板化描述，必须基于数据分析。
5. 输出必须可直接发邮件阅读。
"""
    r = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "你是资深券商策略首席分析师，生成报告必须基于提供的数据，不允许写模板。"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
        max_tokens=1500
    )
    return r["choices"][0]["message"]["content"]

# ===== 邮件发送 =====
def send_mail(content):
    sender = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_PASS")
    receiver = sender

    msg = MIMEText(content)
    msg["Subject"] = "AI量化投资日报"
    msg["From"] = sender
    msg["To"] = receiver

    try:
        s = smtplib.SMTP_SSL("smtp.qq.com", 465)
        s.login(sender, password)
        s.sendmail(sender, receiver, msg.as_string())
        s.quit()
        print("邮件发送成功")
    except Exception as e:
        print(f"邮件发送失败: {e}")

# ===== 主程序 =====
def main():
    today = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    north = northbound_funds()
    lhb = longhubang()
    us_tech = us_tech_stocks()
    sectors = ["新能源", "半导体", "医药", "光伏"]
    sector_info = [f"{i+1}. {s} 板块今日表现优异" for i, s in enumerate(sectors)]

    data_text = "\n".join(
        ["===== 北向资金 ====="] + north +
        ["\n===== 龙虎榜 ====="] + lhb +
        ["\n===== 美股科技股 ====="] + us_tech +
        ["\n===== 板块轮动 ====="] + sector_info
    )

    report = ai_report(data_text)

    final = f"""
AI量化投资终极日报
时间: {today}

市场数据摘要:
{data_text}

----------------------------------

AI策略报告:
{report}
"""
    send_mail(final)

if __name__ == "__main__":
    main()
