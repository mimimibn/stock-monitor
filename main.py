import yfinance as yf
import pandas as pd
import pandas_datareader as pdr
import smtplib
from email.mime.text import MIMEText
import os

def get_stock_data_and_send_email():
    # --- 1. 获取股票数据 (用于计算均线) ---
    try:
        ticker_ndx = yf.Ticker("^NDX") # 用于获取价格和均线
        
        # 获取过去1年多的数据
        hist_data = ticker_ndx.history(period="15mo")
        if hist_data.empty:
            print("获取 ^NDX 数据失败")
            return
            
        current_price = hist_data['Close'].iloc[-1]
        date_str = hist_data.index[-1].strftime('%Y-%m-%d')

        # --- 2. 获取 PE 数据 (改用 QQQ 的 PE) ---
        # 原因：^NDX 是指数，没有 PE 字段。QQQ 是追踪该指数的 ETF，有 PE 数据且高度相关。
        ticker_qqq = yf.Ticker("QQQ")
        info_qqq = ticker_qqq.info
        
        # 尝试获取 QQQ 的滚动市盈率
        # 优先级：trailing_pe (新版库) > trailingPE (旧版库) > 9999 (兜底)
        current_pe = info_qqq.get('trailing_pe') or info_qqq.get('trailingPE') or 9999
        
        # 调试打印
        if current_pe == 9999:
            print(f"⚠️ 警告：QQQ 的 PE 获取失败，当前值: {current_pe}")
        else:
            print(f"✅ 成功从 QQQ 获取 PE: {current_pe}")


        # --- 3. 计算均线 ---
        hist_data['MA120'] = hist_data['Close'].rolling(window=120).mean()
        hist_data['MA250'] = hist_data['Close'].rolling(window=250).mean()

        current_ma120 = hist_data['MA120'].iloc[-1]
        current_ma250 = hist_data['MA250'].iloc[-1]

        # --- 4. 计算连续跌破天数 ---
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

        # --- 5. 核心策略逻辑 ---
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

        # --- 6. 构建邮件内容 ---
        display_pe = "数据异常" if current_pe == 9999 else f"{current_pe:.2f}"
        
        message_body = f"📅 日期: {date_str}\n"
        message_body += f"📈 标的: 纳斯达克100指数 (^NDX)\n"
        message_body += f"💰 当前点位: {current_price:.2f}\n"
        message_body += f"📊 参考PE (来自QQQ): {display_pe}\n" # 修改文案
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
