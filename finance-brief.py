import requests
from bs4 import BeautifulSoup
import datetime
import smtplib
from email.mime.text import MIMEText
import os
import openai
import yfinance as yf  # 美股数据

# ===== 1️⃣ 北向资金监控 =====
def northbound_funds():
    """
    抓取东方财富北向资金数据（沪股通/深股通）
    返回前10个净买入个股
    """
    url = "http://push2.eastmoney.com/api/qt/kamt/north?fields=f12,f14,f2,f3"
    try:
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        data = r.json()["data"]["list"]
        result = []
        for item in data[:10]:
            name = item["f14"]
            net = item["f2"]
            percent = item["f3"]
            result.append(f"{name}: 净买入 {net} 万元, 占比 {percent}%")
        return result
    except Exception as e:
        return [f"北向资金数据抓取失败: {e}"]

# ===== 2️⃣ 龙虎榜监控 =====
def longhubang():
    """
    东方财富龙虎榜简化版
    """
    url = "http://push2.eastmoney.com/api/qt/stock/getsuspension?fields=f12,f14,f2,f3"
    # 这里使用示意接口，可换成真实龙虎榜接口
    try:
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        data = r.json().get("data", [])
        result = []
        for item in data[:10]:
            name = item.get("f14", "未知")
            reason = item.get("f12", "未知原因")
            result.append(f"{name}: {reason}")
        return result
    except Exception as e:
        return [f"龙虎榜数据抓取失败: {e}"]

# ===== 3️⃣ 美股科技股监控 =====
def us_tech_stocks():
    symbols = ["NVDA", "MSFT", "TSLA"]
    result = []
    for s in symbols:
        try:
            stock = yf.Ticker(s)
            data = stock.history(period="1d")
            last = data["Close"].iloc[-1]
            change = data["Close"].iloc[-1] - data["Open"].iloc[-1]
            result.append(f"{s}: 收盘价 {last:.2f}, 涨跌 {change:.2f}")
        except Exception as e:
            result.append(f"{s} 数据抓取失败: {e}")
    return result

# ===== 4️⃣ AI策略生成 =====
def ai_report(text):
    openai.api_key = os.getenv("OPENAI_API_KEY")
    prompt = f"""
你是券商策略首席分析师。

根据以下市场数据写一份投资情报报告：

{text}

报告结构：
一、宏观环境
二、全球市场
三、A股市场
四、行业机会
五、投资风险

每部分3-5条，专业简洁。
"""
    r = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=1200
    )
    return r["choices"][0]["message"]["content"]

# ===== 5️⃣ 邮件发送 =====
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

# ===== 6️⃣ 主程序 =====
def main():
    today = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # 抓取各模块数据
    north = northbound_funds()
    lhb = longhubang()
    us_tech = us_tech_stocks()
    
    # 简单板块轮动示例
    sectors = ["新能源", "半导体", "医药", "光伏"]
    sector_info = [f"{s} 板块今日表现优异" for s in sectors]
    
    # 汇总数据文本
    data_text = "\n".join([
        "===== 北向资金 ====="] + north + 
        ["\n===== 龙虎榜 ====="] + lhb +
        ["\n===== 美股科技股 ====="] + us_tech +
        ["\n===== 板块轮动 ====="] + sector_info
    )
    
    # AI生成策略报告
    report = ai_report(data_text)
    
    # 终极日报
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
