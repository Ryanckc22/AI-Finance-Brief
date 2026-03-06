import requests
import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import yfinance as yf
import google.generativeai as genai

# ===== 北向资金监控 =====
def northbound_funds():
    """抓取北向资金实时净流入数据（东方财富）"""
    url = (
        "http://push2.eastmoney.com/api/qt/kamt.rtmin/get"
        "?fields1=f1,f2,f3,f4&fields2=f51,f52,f53,f54,f55,f56"
        "&ut=b2884a393a59ad64002292a3e90d46a5&cb=jQuery&_=1"
    )
    headers = {"Referer": "https://data.eastmoney.com/"}
    try:
        r = requests.get(url, headers=headers, timeout=8)
        data = r.json()
        north = data.get("data", {}).get("s2n", [])
        if not north:
            raise ValueError("返回数据为空")
        latest = north[-1].split(",")
        time_str = latest[0]
        sh_net = float(latest[1]) / 10000
        sz_net = float(latest[3]) / 10000
        total = sh_net + sz_net
        return [
            f"统计时间: {time_str}",
            f"沪股通净买入: {sh_net:.2f} 亿元",
            f"深股通净买入: {sz_net:.2f} 亿元",
            f"北向资金合计净买入: {total:.2f} 亿元",
        ]
    except Exception as e:
        return [f"北向资金数据抓取失败: {e}"]


# ===== 龙虎榜监控 =====
def longhubang():
    """抓取龙虎榜数据（东方财富）"""
    url = (
        "http://push2.eastmoney.com/api/qt/stock/lhbdata/get"
        "?fields=f12,f14,f2,f3,f62,f184"
        "&fltt=2&invt=2&fid=f184&fs=m:90+t:2&pn=1&pz=10"
        "&ut=b2884a393a59ad64002292a3e90d46a5"
    )
    headers = {"Referer": "https://data.eastmoney.com/"}
    try:
        r = requests.get(url, headers=headers, timeout=8)
        data = r.json().get("data", {}).get("diff", [])
        if not data:
            raise ValueError("龙虎榜列表为空")
        result = []
        for i, item in enumerate(data[:8], 1):
            name = item.get("f14", "未知")
            code = item.get("f12", "")
            net_buy = item.get("f62", 0)
            pct = item.get("f3", 0)
            net_buy_yi = net_buy / 100000000 if net_buy else 0
            result.append(
                f"{i}. {name}({code}): 净买入 {net_buy_yi:.2f} 亿元, 涨跌幅 {pct:.2f}%"
            )
        return result
    except Exception as e:
        return [f"龙虎榜数据抓取失败: {e}"]


# ===== 美股科技股监控 =====
def us_tech_stocks():
    """抓取美股科技股数据（yfinance）"""
    symbols = {
        "NVDA": "英伟达",
        "MSFT": "微软",
        "TSLA": "特斯拉",
        "AAPL": "苹果",
        "META": "Meta",
    }
    result = []
    for i, (s, name) in enumerate(symbols.items(), 1):
        try:
            stock = yf.Ticker(s)
            hist = stock.history(period="2d")
            if len(hist) < 2:
                result.append(f"{i}. {name}({s}): 数据不足")
                continue
            prev_close = hist["Close"].iloc[-2]
            last_close = hist["Close"].iloc[-1]
            change = last_close - prev_close
            change_pct = change / prev_close * 100
            result.append(
                f"{i}. {name}({s}): 收盘 ${last_close:.2f}, "
                f"涨跌 {change:+.2f} ({change_pct:+.2f}%)"
            )
        except Exception as e:
            result.append(f"{i}. {name}({s}) 数据抓取失败: {e}")
    return result


# ===== A股板块 ETF 监控 =====
def sector_etf():
    """通过 ETF 监控A股主要板块表现（yfinance）"""
    etfs = {
        "新能源": "159915.SZ",
        "半导体": "512480.SS",
        "医药生物": "159929.SZ",
        "消费": "159928.SZ",
        "金融": "510230.SS",
    }
    result = []
    for i, (sector, code) in enumerate(etfs.items(), 1):
        try:
            etf = yf.Ticker(code)
            hist = etf.history(period="2d")
            if len(hist) < 2:
                result.append(f"{i}. {sector}ETF({code}): 数据不足")
                continue
            prev = hist["Close"].iloc[-2]
            last = hist["Close"].iloc[-1]
            chg_pct = (last - prev) / prev * 100
            result.append(
                f"{i}. {sector}ETF({code}): 收盘 {last:.3f}, 涨跌幅 {chg_pct:+.2f}%"
            )
        except Exception as e:
            result.append(f"{i}. {sector}ETF({code}) 抓取失败: {e}")
    return result


# ===== AI策略报告生成（Gemini） =====
def ai_report(data_text: str) -> str:
    """调用 Google Gemini 生成投资策略报告"""
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])

    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",  # 免费额度最大的模型
        system_instruction=(
            "你是资深券商策略首席分析师。"
            "你的报告必须100%基于用户提供的真实数据，"
            "禁止出现任何模板化描述或无数据支撑的结论。"
        ),
    )

    prompt = f"""
请根据以下今日市场真实数据，生成一份专业投资策略报告：

{data_text}

报告要求：
1. 【宏观与全球市场】：分析美股科技股涨跌，引用具体股票名称和数值。
2. 【A股资金面】：分析北向资金净流入规模，判断外资情绪。
3. 【热点与龙虎榜】：点评龙虎榜前3名个股，引用具体净买入金额和涨跌幅。
4. 【板块轮动】：对比各板块ETF涨跌，指出强弱板块并给出逻辑。
5. 【投资策略】：给出明日操作方向，包括关注的板块/个股，必须有数据支撑。
6. 严禁出现"市场总体表现良好"等无数据的模板句。
7. 报告长度约600-800字，适合直接邮件阅读。
"""

    response = model.generate_content(prompt)
    return response.text


# ===== 邮件发送 =====
def send_mail(subject: str, content: str):
    """通过 QQ 邮箱 SMTP 发送邮件"""
    sender = os.environ["EMAIL_USER"]
    password = os.environ["EMAIL_PASS"]
    receiver = sender

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = receiver
    msg.attach(MIMEText(content, "plain", "utf-8"))

    try:
        with smtplib.SMTP_SSL("smtp.qq.com", 465) as s:
            s.login(sender, password)
            s.sendmail(sender, receiver, msg.as_string())
        print("✅ 邮件发送成功")
    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")
        raise


# ===== 主程序 =====
def main():
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"[{now}] 开始抓取数据...")

    north = northbound_funds()
    print("北向资金 ✓")

    lhb = longhubang()
    print("龙虎榜 ✓")

    us_tech = us_tech_stocks()
    print("美股科技股 ✓")

    sectors = sector_etf()
    print("板块ETF ✓")

    data_text = "\n".join(
        ["===== 北向资金 ====="] + north
        + ["\n===== 龙虎榜 TOP8 ====="] + lhb
        + ["\n===== 美股科技股 ====="] + us_tech
        + ["\n===== A股板块ETF ====="] + sectors
    )

    print("正在生成 Gemini AI 报告...")
    report = ai_report(data_text)

    final = f"""AI量化投资日报
生成时间: {now}
{'='*50}

【今日市场数据摘要】
{data_text}

{'='*50}

【AI策略报告】
{report}

{'='*50}
本报告由 Gemini AI 基于实时数据自动生成，不构成投资建议。
"""

    subject = f"AI量化投资日报 {datetime.datetime.now().strftime('%Y-%m-%d')}"
    send_mail(subject, final)
    print("完成！")


if __name__ == "__main__":
    main()
