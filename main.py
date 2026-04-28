import yfinance as yf
import pandas as pd
import smtplib
from email.mime.text import MIMEText
import os

def get_stock_data_and_send_email():
    # --- 1. 获取股票数据 ---
    try:
        ticker = yf.Ticker("^NDX")
        # 获取过去1年的数据，确保包含至少250个交易日
        hist_data = ticker.history(period="1y")
        
        if hist_data.empty:
            print("获取数据失败")
            return

        # --- 2. 计算均线 ---
        # 计算 MA120 (半年线)
        hist_data['MA120'] = hist_data['Close'].rolling(window=120).mean()
        
        # 计算 MA250 (年线)
        hist_data['MA250'] = hist_data['Close'].rolling(window=250).mean()

        # 获取最新数据
        current_price = hist_data['Close'].iloc[-1]
        current_ma120 = hist_data['MA120'].iloc[-1]
        current_ma250 = hist_data['MA250'].iloc[-1]
        date_str = hist_data.index[-1].strftime('%Y-%m-%d')
        
        # --- 3. 核心策略逻辑判断 ---
        # 默认状态
        strategy_status = "未知状态"
        
        # 逻辑优先级：先看年线，再看半年线，最后是高位
        if current_price < current_ma250:
            # 情况1：低于年线（深度低估）
            strategy_status = "1.5倍定投"
        elif current_price < current_ma120:
            # 情况2：低于半年线，但高于年线（相对低估）
            strategy_status = "1倍定投"
        elif current_price > current_ma120 and current_price > current_ma250:
            # 情况3：高于所有均线（高估区域）
            strategy_status = "0.5倍定投"
        else:
            # 边缘情况：介于两者之间（通常不会发生，除非均线纠缠）
            strategy_status = "1倍定投"

        # --- 4. 构建邮件内容 ---
        message_body = f"日期: {date_str}\n"
        message_body += f"标的: 纳斯达克100指数 (^NDX)\n"
        message_body += f"当前点位: {current_price:.2f}\n"
        message_body += "-" * 30 + "\n"
        
        # 显示均线数据供参考
        message_body += f"A250 (年线): {current_ma250:.2f}\n"
        message_body += f"MA120 (半年线): {current_ma120:.2f}\n"
        message_body += "-" * 30 + "\n"
        
        # 突出显示最终策略
        message_body += f"今日策略: 【 {strategy_status} 】"

        # 邮件标题
        subject = f"纳指100定投提醒: {strategy_status}"

        print(f"分析完成:\n{message_body}")
        send_email(subject, message_body)

    except Exception as e:
        error_msg = f"运行出错: {str(e)}"
        print(error_msg)
        send_email("股票分析脚本运行错误", error_msg)

def send_email(subject, body):
    # --- 5. 邮件发送配置 ---
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT"))
    email_user = os.getenv("EMAIL_USER")
    email_pass = os.getenv("EMAIL_PASS")
    email_receiver = os.getenv("EMAIL_RECEIVER")

    if not all([smtp_server, email_user, email_pass, email_receiver]):
        print("错误: 未配置完整的邮件环境变量")
        return

    try:
        msg = MIMEText(body, 'plain', 'utf-8')
        msg['From'] = email_user
        msg['To'] = email_receiver
        msg['Subject'] = subject

        server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        server.login(email_user, email_pass)
        server.sendmail(email_user, [email_receiver], msg.as_string())
        server.quit()
        print(f"邮件发送成功 -> {email_receiver}")
        
    except Exception as e:
        print(f"邮件发送失败: {str(e)}")

if __name__ == "__main__":
    get_stock_data_and_send_email()
