import smtplib
from email.mime.text import MIMEText
import datetime

# QQ邮箱
sender = "25041156@qq.com"
password = "impkhcgtvtxacbdb"
receiver = "25041156@qq.com"

today = datetime.date.today()

content = f"""
AI Finance Brief

日期: {today}

【A股重要新闻】
- 今日政策
- 热点行业

【全球市场】
- 美股走势
- 美联储政策

【行业】
AI / 半导体 / 新能源

（自动生成）
"""

msg = MIMEText(content)
msg["Subject"] = "每日金融简报"
msg["From"] = sender
msg["To"] = receiver

server = smtplib.SMTP_SSL("smtp.qq.com", 465)
server.login(sender, password)
server.sendmail(sender, receiver, msg.as_string())
server.quit()

print("Email sent")
