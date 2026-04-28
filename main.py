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
            
        # 获取实时估值信息 (关键新增)
        info = ticker.info
        # 获取市盈率 (PE-TTM)
        # 如果无法获取PE，设为 9999 (代替之前的 inf)
        current_pe = info.get('trailingPE', 9999) 

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
        days_below_120 = 0
        days_below_250 = 0

        # 1. 计算跌破 MA120 天数
        if current_price < current_ma120:
            for i in range(len(hist_data)):
                row = hist_data.iloc[-(i+1)]
                if row['Close'] < row['MA120']:
                    days_below_120 += 1
                else:
                    break

        # 2. 计算跌破 MA250 天数
        if current_price < current_ma250:
            for i in range(len(hist_data)):
                row = hist_data.iloc[-(i+1)]
                if row['Close'] < row['MA250']:
                    days_below_250 += 1
                else:
                    break

        # --- 4. 核心策略逻辑 (双因子：均线 + 估值) ---
        strategy_status = ""
        money_amount = 0
        reasoning = ""

        # 优先级最高：跌破年线 且 估值回归合理 (PE < 30)
        if current_price < current_ma250 and current_pe < 30:
            strategy_status = "【激进加仓】"
            money_amount = 800
            reasoning = f"逻辑：跌破年线且估值(PE={current_pe:.2f})进入安全区，重仓抄底。"
        
        # 中间档：跌破半年线 或 跌破年线但估值依然偏高 (PE >= 30)
        elif current_price < current_ma120 or (current_price < current_ma250 and current_pe >= 30):
            strategy_status = "【标准定投】"
            money_amount = 400
            if current_pe >= 30:
                reasoning = f"逻辑：虽然跌破均线，但估值(PE={current_pe:.2f})仍偏高，适度参与。"
            else:
                reasoning = "逻辑：处于半年线下方调整期，维持标准投入。"
        
        # 保守档：在半年线上方 (趋势行情)
        else:
            strategy_status = "【保守观望】"
            money_amount = 200
            reasoning = f"逻辑：趋势向好但当前估值(PE={current_pe:.2f})较贵，低额维持。"

        # --- 5. 构建邮件内容 ---
        message_body = f"📅 日期: {date_str}\n"
        message_body += f"📈 标的: 纳斯达克100指数 (^NDX)\n"
        message_body += f"💰 当前点位: {current_price:.2f}\n"
        
        # 修改这里：如果 PE 是 9999，显示为 "数据异常/极高"
        display_pe = "数据异常" if current_pe == 9999 else f"{current_pe:.2f}"
        message_body += f"📊 当前市盈率(PE-TTM): {display_pe}\n"
        
        message_body += "-" * 40 + "\n"
        
        # 显示均线数据与状态
        message_body += f"📉 MA250 (年线): {current_ma250:.2f} (已跌破{days_below_250}天)\n"
        message_body += f"📉 MA120 (半年线): {current_ma120:.2f} (已跌破{days_below_120}天)\n"
        message_body += "-" * 40 + "\n"
        
        # 突出显示最终策略
        message_body += f"🚀 今日策略: {strategy_status}\n"
        message_body += f"💰 每日定投金额: 【{money_amount} 元】\n"
        message_body += f"💡 策略依据: {reasoning}"

        # 邮件标题
        subject = f"📊 纳指100定投提醒: {strategy_status} - {money_amount}元"
        print(f"分析完成:\n{message_body}")
        send_email(subject, message_body)

    except Exception as e:
        error_msg = f"运行出错: {str(e)}"
        print(error_msg)
        send_email("❌ 股票分析脚本运行错误", error_msg)

def send_email(subject, body):
    # --- 6. 邮件发送配置 ---
    # 请确保在系统环境变量中配置了以下信息
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
