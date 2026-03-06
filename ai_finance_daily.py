import requests
import datetime
import smtplib
import json
import re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import yfinance as yf

# ===== 调试工具 =====
def log(tag: str, msg: str):
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {tag}: {msg}")


# ===== 北向资金监控 =====
def northbound_funds():
    url = (
        "http://push2.eastmoney.com/api/qt/kamt.rtmin/get"
        "?fields1=f1,f2,f3,f4&fields2=f51,f52,f53,f54,f55,f56"
        "&ut=b2884a393a59ad64002292a3e90d46a5"
        "&cb=jQuery18304048470484873345_1698890000000&_=1698890000001"
    )
    headers = {
        "Referer": "https://data.eastmoney.com/hsgtcg/",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        text = r.text
        match = re.search(r"jQuery[\w_]+\((\{.*\})\)", text, re.DOTALL)
        if not match:
            raise ValueError(f"JSONP 解析失败，内容片段: {text[:200]}")
        data = json.loads(match.group(1))
        north_list = data.get("data", {}).get("s2n", [])
        if not north_list:
            raise ValueError("s2n 字段为空，可能是非交易时段")
        latest = north_list[-1].split(",")
        time_str = latest[0]
        sh_buy  = float(latest[1]) / 10000
        sh_sell = float(latest[2]) / 10000
        sz_buy  = float(latest[3]) / 10000
        sz_sell = float(latest[4]) / 10000
        sh_net  = sh_buy - sh_sell
        sz_net  = sz_buy - sz_sell
        total   = sh_net + sz_net
        result = [
            f"统计时间: {time_str}",
            f"沪股通净买入: {sh_net:+.2f} 亿元（买入{sh_buy:.2f} / 卖出{sh_sell:.2f}）",
            f"深股通净买入: {sz_net:+.2f} 亿元（买入{sz_buy:.2f} / 卖出{sz_sell:.2f}）",
            f"北向资金合计净买入: {total:+.2f} 亿元",
        ]
        log("北向资金", f"成功，合计净买入 {total:+.2f} 亿")
        return result
    except Exception as e:
        log("北向资金", f"失败: {e}")
        return [f"北向资金数据抓取失败: {e}"]


# ===== 龙虎榜监控 =====
def longhubang():
    url = (
        "http://push2.eastmoney.com/api/qt/stock/lhbdata/get"
        "?fields=f12,f14,f2,f3,f62,f184"
        "&fltt=2&invt=2&fid=f184&fs=m:90+t:3&pn=1&pz=10"
        "&ut=b2884a393a59ad64002292a3e90d46a5"
    )
    headers = {
        "Referer": "https://data.eastmoney.com/stock/lhb.html",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        resp = r.json()
        diff = resp.get("data", {}).get("diff", [])
        if not diff:
            raise ValueError(f"diff 为空，响应: {json.dumps(resp)[:300]}")
        result = []
        for i, item in enumerate(diff[:8], 1):
            name    = item.get("f14", "未知")
            code    = item.get("f12", "")
            pct     = item.get("f3", 0) or 0
            net_buy = item.get("f62", 0) or 0
            net_yi  = net_buy / 1e8
            result.append(f"{i}. {name}({code}): 涨跌幅 {pct:+.2f}%, 龙虎净买入 {net_yi:+.2f} 亿元")
        log("龙虎榜", f"成功，获取 {len(result)} 条")
        return result
    except Exception as e:
        log("龙虎榜", f"失败: {e}")
        return [f"龙虎榜数据抓取失败: {e}"]


# ===== 美股科技股监控 =====
def us_tech_stocks():
    symbols = {"NVDA": "英伟达", "MSFT": "微软", "TSLA": "特斯拉",
               "AAPL": "苹果", "META": "Meta", "GOOGL": "谷歌"}
    result = []
    for i, (s, name) in enumerate(symbols.items(), 1):
        try:
            stock = yf.Ticker(s)
            hist = stock.history(period="5d").dropna(subset=["Close"])
            if len(hist) < 2:
                result.append(f"{i}. {name}({s}): 近期无交易数据")
                continue
            prev_close = hist["Close"].iloc[-2]
            last_close = hist["Close"].iloc[-1]
            last_date  = hist.index[-1].strftime("%m-%d")
            change     = last_close - prev_close
            change_pct = change / prev_close * 100
            result.append(f"{i}. {name}({s}) [{last_date}]: 收盘 ${last_close:.2f}, 涨跌 {change:+.2f} ({change_pct:+.2f}%)")
        except Exception as e:
            result.append(f"{i}. {name}({s}) 抓取失败: {e}")
    log("美股", f"成功，获取 {len([r for r in result if '失败' not in r])} 条")
    return result


# ===== A股板块 ETF 监控 =====
def sector_etf():
    etfs = {"新能源": "159915.SZ", "半导体": "512480.SS", "医药生物": "159929.SZ",
            "消费": "159928.SZ", "金融": "510230.SS", "军工": "512660.SS"}
    result = []
    for i, (sector, code) in enumerate(etfs.items(), 1):
        try:
            etf = yf.Ticker(code)
            hist = etf.history(period="5d").dropna(subset=["Close"])
            if len(hist) < 2:
                result.append(f"{i}. {sector}ETF({code}): 暂无数据")
                continue
            prev      = hist["Close"].iloc[-2]
            last      = hist["Close"].iloc[-1]
            last_date = hist.index[-1].strftime("%m-%d")
            chg_pct   = (last - prev) / prev * 100
            result.append(f"{i}. {sector}ETF({code}) [{last_date}]: 收盘 {last:.3f}, 涨跌幅 {chg_pct:+.2f}%")
        except Exception as e:
            result.append(f"{i}. {sector}ETF({code}) 抓取失败: {e}")
    log("板块ETF", f"成功，获取 {len([r for r in result if '失败' not in r and '暂无' not in r])} 条")
    return result


# ===== AI策略报告生成（Gemini REST API，无需任何第三方库）=====
def ai_report(data_text: str) -> str:
    api_key = os.environ["GEMINI_API_KEY"]
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"

    system_instruction = (
        "你是资深券商策略首席分析师。"
        "报告必须100%基于提供的真实数据。"
        "若某项数据标注'抓取失败'或'暂无数据'，直接跳过该项，不得编造。"
        "禁止出现任何模板化描述。"
    )

    prompt = f"""以下是今日实时市场数据，请生成专业投资策略报告：

{data_text}

报告结构（每节必须引用上方具体数字）：

【一、全球市场】分析美股各科技股涨跌幅和具体股价，判断市场情绪。

【二、A股资金面】分析北向资金净买入规模。若净买入显示±520亿或±1040亿整数，说明是非交易时段占位数据，请注明"今日北向资金数据暂未更新"。

【三、龙虎榜解读】若有龙虎榜数据则点评前3名；若标注失败则跳过本节。

【四、板块轮动】对比各ETF涨跌幅，明确指出今日最强和最弱板块，给出逻辑。

【五、明日策略】基于以上数据，给出明日重点关注方向，说明理由，不得无中生有。

要求：约600字，每句结论必须对应上方某条具体数据。"""

    payload = {
        "system_instruction": {"parts": [{"text": system_instruction}]},
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 1500}
    }

    r = requests.post(url, json=payload, timeout=60)
    r.raise_for_status()
    resp = r.json()
    text = resp["candidates"][0]["content"]["parts"][0]["text"]
    log("Gemini", "报告生成成功")
    return text


# ===== 邮件发送 =====
def send_mail(subject: str, content: str):
    sender   = os.environ["EMAIL_USER"]
    password = os.environ["EMAIL_PASS"]
    receiver = sender
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = sender
    msg["To"]      = receiver
    msg.attach(MIMEText(content, "plain", "utf-8"))
    with smtplib.SMTP_SSL("smtp.qq.com", 465) as s:
        s.login(sender, password)
        s.sendmail(sender, receiver, msg.as_string())
    log("邮件", "发送成功")


# ===== 主程序 =====
def main():
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    log("启动", f"开始运行，时间 {now}")

    north   = northbound_funds()
    lhb     = longhubang()
    us_tech = us_tech_stocks()
    sectors = sector_etf()

    data_text = "\n".join(
        ["===== 北向资金 ====="]        + north
        + ["\n===== 龙虎榜 TOP8 ====="] + lhb
        + ["\n===== 美股科技股 ====="]   + us_tech
        + ["\n===== A股板块ETF ====="]   + sectors
    )

    log("数据汇总", f"\n{data_text}\n")

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


if __name__ == "__main__":
    main()
