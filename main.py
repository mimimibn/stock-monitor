import yfinance as yf
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.header import Header
import os
from datetime import datetime

def get_stock_data_and_send_email():
    # --- 1. 获取股票数据 ---
    try:
        ticker = yf.Ticker("^NDX")
        # 获取历史数据
        hist_data = ticker.history(period="6mo")
        
        if hist_data.empty:
            print("获取数据失败")
            return

        # 计算 MA120
        hist_data['MA120'] = hist_data['Close'].rolling(window=120).mean()
        
        current_price = hist_data['Close'].iloc[-1]
        current_ma120 = hist_data['MA120'].iloc[-1]
        date_str = hist_data.index[-1].strftime('%Y-%m-%d')
        
        # --- 2. 判断逻辑 ---
        message_body = f"日期: {date_str}\n"
        message_body += f"标的: 纳斯达克100指数 (^NDX)\n"
        message_body += f"当前点位: {current_price:.2f}\n"
        message_body += f"MA120点位: {current_ma120:.2f}\n"
        message_body += "-" * 30 + "\n"

        if current_price < current_ma120:
            # 触发加仓信号
            message_body += f"当前MA120点位为：{current_ma120:.2f}，纳斯达克100指数点位为：{current_price:.2f}，该加仓了"
            subject = "纳斯达克100加仓信号提醒"
        else:
            # 正常汇报
            message_body += "当前指数位于MA120上方，继续持有或观望。"
            subject = "纳斯达克100每日均线日报"

        print(f"分析完成:\n{message_body}")
        send_email(subject, message_body)

    except Exception as e:
        error_msg = f"运行出错: {str(e)}"
        print(error_msg)
        send_email("股票分析脚本运行错误", error_msg)

def send_email(subject, body):
    # --- 3. 邮件发送配置 ---
    # 从 GitHub Secrets 获取环境变量
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT"))
    email_user = os.getenv("EMAIL_USER")
    email_pass = os.getenv("EMAIL_PASS") # 这里填授权码
    email_receiver = os.getenv("EMAIL_RECEIVER")

    if not all([smtp_server, email_user, email_pass, email_receiver]):
        print("错误: 未配置完整的邮件环境变量")
        return

    try:
        msg = MIMEText(body, 'plain', 'utf-8')
        msg['From'] = Header(f"GitHub Actions <{email_user}>", 'utf-8')
        msg['To'] = Header(f"Me <{email_receiver}>", 'utf-8')
        msg['Subject'] = Header(subject, 'utf-8')

        server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        server.login(email_user, email_pass)
        server.sendmail(email_user, [email_receiver], msg.as_string())
        server.quit()
        print(f"邮件发送成功 -> {email_receiver}")
    except Exception as e:
        print(f"邮件发送失败: {str(e)}")

if __name__ == "__main__":
    get_stock_data_and_send_email()