import requests
import smtplib
import os
from email.mime.text import MIMEText
from datetime import datetime

def get_danjuan_valuation():
    url = "https://danjuanfunds.com/djapi/index_eva/detail/NDX"
    headers = {
        "Host": "danjuanfunds.com",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://danjuanfunds.com/dj-valuation-table-detail/NDX"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data['result_code'] == 0:
                valuation = data['data']
                pe = valuation['pe']
                pe_percentile = valuation['pe_percentile'] * 100
                ts = valuation['ts']
                data_time = datetime.fromtimestamp(ts / 1000).strftime('%Y-%m-%d %H:%M:%S')
                return {
                    "success": True,
                    "pe": round(pe, 2),
                    "pe_percentile": round(pe_percentile, 2),
                    "data_time": data_time
                }
    except Exception as e:
        return {"success": False, "msg": str(e)}

def determine_strategy(pe_percentile):
    if pe_percentile >= 90:
        return {"action": "【极度高估 - 暂停定投】", "amount": 0}
    elif pe_percentile >= 70:
        return {"action": "【适中区域】", "amount": 200}
    elif pe_percentile >= 40:
        return {"action": "【标准定投】", "amount": 500}
    elif pe_percentile >= 20:
        return {"action": "【低估区域】", "amount": 1000}
    else:
        return {"action": "【深度低估 - 重仓买入】", "amount": 2000}

def send_email(subject, body):
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT"))
    email_user = os.getenv("EMAIL_USER")
    email_pass = os.getenv("EMAIL_PASS")
    email_receiver = os.getenv("EMAIL_RECEIVER")

    if not email_user or not email_pass:
        print("错误: 未配置邮箱环境变量")
        return False

    try:
        msg = MIMEText(body, 'plain', 'utf-8')
        msg['From'] = email_user
        msg['To'] = email_receiver
        msg['Subject'] = subject
        
        server = smtplib.SMTP_SSL(smtp_server, smtp_port)
        server.login(email_user, email_pass)
        server.sendmail(email_user, [email_receiver], msg.as_string())
        server.quit()
        print("✅ 邮件发送成功")
        return True
    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")
        return False

def main():
    print("🚀 开始执行纳斯达克定投策略...")
    
    valuation_data = get_danjuan_valuation()
    
    if not valuation_data["success"]:
        error_msg = f"获取估值失败: {valuation_data['msg']}"
        print(error_msg)
        send_email("【定投脚本错误】", error_msg)
        return

    strategy = determine_strategy(valuation_data["pe_percentile"])

    # 自动获取当前日期
    current_date = datetime.now().strftime('%Y-%m-%d')
    current_day = datetime.now().strftime('%A')

    email_body = f"""📅 日期: {current_date} ({current_day})
📈 标的: 纳斯达克100指数 (NDX)
📊 真实PE: {valuation_data['pe']}
📊 PE百分位: {valuation_data['pe_percentile']}%
⏰ 数据时间点: {valuation_data['data_time']}
------------------------------
🚀 今日策略: {strategy['action']}
💰 每日定投金额: 【{strategy['amount']} 元】
"""
    
    email_subject = f"💰 纳指定投: {strategy['action']} - {strategy['amount']}元"
    print(f"\n📝 生成报告:\n{email_body}")
    send_email(email_subject, email_body)

if __name__ == "__main__":
    main()
