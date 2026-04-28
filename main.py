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
            print("获取历史K线数据失败")
            return
            
        # --- 获取 PE 数据 (已修复) ---
        info = ticker.info
        
        # 1. 尝试使用新版本的 key: 'trailing_pe'
        # 2. 如果失败，尝试旧版本的 key: 'trailingPE'
        # 3. 如果都失败，使用兜底值 9999
        current_pe = info.get('trailing_pe') or info.get('trailingPE') or 9999

        # --- 调试日志：如果获取失败，打印所有包含 'pe' 的字段 ---
        if current_pe == 9999:
            print("⚠️ 警告：未能通过 'trailing_pe' 或 'trailingPE' 获取数据。")
            print("🔍 正在扫描 info 中所有包含 'pe' 的字段，请检查下方输出：")
            for key, value in info.items():
                if 'pe' in key.lower():
                    print(f"   发现疑似字段: {key} = {value}")
            print("-" * 30)

        # --- 2. 计算均线 ---
        hist_data['MA120'] = hist_data['Close'].rolling(window=120).mean()
        hist_data['MA250'] = hist_data['Close'].rolling(window=250).mean()

        # 获取最新数据
        current_price = hist_data['Close'].iloc[-1]
        current_ma120 = hist_data['MA120'].iloc[-1]
        current_ma250 = hist_data['MA250'].iloc[-1]
        date_str = hist_data.index[-1].strftime('%Y-%m-%d')

        # --- 3. 计算连续跌破天数 ---
        days_below_120 = 0
        days_below_250 = 0

        if current_price < current_ma120:
            for i in range(len(hist_data)):
                row = hist_data.iloc[-(i+1)]
                if row['Close'] < row['MA120']:
                    days_below_120 += 1
                else:
                    break

        if current_price < current_ma250:
            for i in range(len(hist_data)):
                row = hist_data.iloc[-(i+1)]
                if row['Close'] < row['MA250']:
                    days_below_250 += 1
                else:
                    break

        # --- 4. 核心策略逻辑 ---
        strategy_status = ""
        money_amount = 0
        reasoning = ""

        # 逻辑判断
        if current_price < current_ma250 and current_pe < 30:
            strategy_status = "【激进加仓】"
            money_amount = 800
            reasoning = f"逻辑：跌破年线且估值(PE={current_pe:.2f})进入安全区，重仓抄底。"
        
        elif current_price < current_ma120 or (current_price < current_ma250 and current_pe >= 30):
            strategy_status = "【标准定投】"
            money_amount = 400
            if current_pe >= 30:
                reasoning = f"逻辑：虽然跌破均线，但估值(PE={current_pe:.2f})仍偏高，适度参与。"
            else:
                reasoning = "逻辑：处于半年线下方调整期，维持标准投入。"
        
        else:
            strategy_status = "【保守观望】"
            money_amount = 200
            reasoning = f"逻辑：趋势向好但当前估值(PE={current_pe:.2f})较贵，低额维持。"

        # --- 5. 构建邮件内容 ---
        # 显示处理：如果是9999，显示为“数据异常”，否则显示数值
        display_pe = "数据异常" if current_pe == 9999 else f"{current_pe:.2f}"
        
        message_body = f"📅 日期: {date_str}\n"
        message_body += f"📈 标的: 纳斯达克100指数 (^NDX)\n"
        message_body += f"💰 当前点位: {current_price:.2f}\n"
        message_body += f"📊 当前市盈率(PE-TTM): {display_pe}\n"
        message_body += "-" * 40 + "\n"
        message_body += f"📉 MA250 (年线): {current_ma250:.2f} (已跌破{days_below_250}天)\n"
        message_body += f"📉 MA120 (半年线): {current_ma120:.2f} (已跌破{days_below_120}天)\n"
        message_body += "-" * 40 + "\n"
        message_body += f"🚀 今日策略: {strategy_status}\n"
        message_body += f"💰 每日定投金额: 【{money_amount} 元】\n"
        message_body += f"💡 策略依据: {reasoning}"

        subject = f"📊 纳指100定投提醒: {strategy_status} - {money_amount}元"
        print(f"分析完成:\n{message_body}")
        send_email(subject, message_body)

    except Exception as e:
        error_msg = f"运行出错: {str(e)}"
        print(error_msg)
        send_email("❌ 股票分析脚本运行错误", error_msg)

def send_email(subject, body):
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
