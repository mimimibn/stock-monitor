import yfinance as yf
import pandas as pd
import smtplib
from email.mime.text import MIMEText
import os

def get_stock_data_and_send_email():
    # --- 1. 获取股票数据 ---
    try:
        ticker = yf.Ticker("^NDX")
        # 获取过去1年多的数据，确保能计算均线
        hist_data = ticker.history(period="15mo")
        
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
        
        # --- 3. 计算连续跌破天数 ---
        # 修复逻辑：必须先判断“今天”是否在下方。如果“今天”在上方，天数直接为0。
        
        days_below_120 = 0
        days_below_250 = 0
        
        # 1. 先判断 MA120
        # 只有当今天收盘价 < MA120 时，才开始数天数
        if current_price < current_ma120:
            for i in range(len(hist_data)):
                row = hist_data.iloc[-(i+1)]
                if row['Close'] < row['MA120']:
                    days_below_120 += 1
                else:
                    break # 一旦遇到一天在均线上方，计数停止
        
        # 2. 再判断 MA250
        # 只有当今天收盘价 < MA250 时，才开始数天数
        if current_price < current_ma250:
            for i in range(len(hist_data)):
                row = hist_data.iloc[-(i+1)]
                if row['Close'] < row['MA250']:
                    days_below_250 += 1
                else:
                    break # 一旦遇到一天在均线上方，计数停止

        # --- 4. 核心策略逻辑 ---
        strategy_status = ""
        multiplier = 0.0
        money_amount = ""
        
        # 优先级判断：先看是否满足“大跌抄底”条件（>5天）
        
        # 情况1：跌破 MA250 超过 5天 -> 深度抄底
        if current_price < current_ma250 and days_below_250 > 5:
            strategy_status = f"1.5倍定投 (跌破年线第{days_below_250}天)"
            multiplier = 1.5
            money_amount = "(1000元)"
            
        # 情况2：跌破 MA120 超过 5天 -> 中度抄底
        elif current_price < current_ma120 and days_below_120 > 5:
            strategy_status = f"1倍定投 (跌破半年线第{days_below_120}天)"
            multiplier = 1.0
            money_amount = "(800元)"
            
        # 情况3：在均线上方（或刚跌破没超过5天） -> 保守定投
        else:
            # 这里包含了：价格在均线上，或者刚跌破1-5天的情况
            if current_price > current_ma120:
                strategy_status = "0.5倍定投 (趋势向好)"
            else:
                strategy_status = f"0.5倍定投 (跌破观察期 第{days_below_120}天)"
            multiplier = 0.5
            money_amount = "(400元)"

        # --- 5. 构建邮件内容 ---
        message_body = f"📅 日期: {date_str}\n"
        message_body += f"📈 标的: 纳斯达克100指数 (^NDX)\n"
        message_body += f"当前点位: {current_price:.2f}\n"
        message_body += "-" * 30 + "\n"
        
        # 显示均线数据与状态
        message_body += f"📉 MA250 (年线): {current_ma250:.2f} (已跌破{days_below_250}天)\n"
        message_body += f"📉 MA120 (半年线): {current_ma120:.2f} (已跌破{days_below_120}天)\n"
        message_body += "-" * 30 + "\n"
        
        # 突出显示最终策略
        message_body += f"🚀 今日策略: 【 {strategy_status} 】 {money_amount}"

        # 邮件标题
        subject = f"📊 纳指100定投提醒: {strategy_status}"

        print(f"分析完成:\n{message_body}")
        send_email(subject, message_body)

    except Exception as e:
        error_msg = f"运行出错: {str(e)}"
        print(error_msg)
        send_email("❌ 股票分析脚本运行错误", error_msg)

def send_email(subject, body):
    # --- 6. 邮件发送配置 ---
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
        # msg['From'] = email_user
        msg['From'] = f"=?UTF-8?B?5L2T5piv5bCP5aSp5Li6?= <{email_user}>"
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
