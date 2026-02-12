#!/usr/bin/env python
"""
방산 뉴스 한국어 일일 다이제스트 - 웹 인터페이스
Flask 기반 단일 웹페이지로 CrewAI 실행 및 결과 확인
"""
import os
import sys
import smtplib
import threading
import time
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, jsonify, request

# 프로젝트 소스 경로 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

app = Flask(__name__)

# 실행 상태 관리
execution_state = {
    "status": "idle",       # idle | running | completed | error
    "result": None,
    "error": None,
    "started_at": None,
    "completed_at": None,
}
execution_lock = threading.Lock()


def run_crew_task():
    """백그라운드에서 CrewAI crew를 실행"""
    global execution_state
    try:
        from defense_news_korean_daily_digest.crew import DefenseNewsKoreanDailyDigestCrew

        crew_instance = DefenseNewsKoreanDailyDigestCrew().crew()
        result = crew_instance.kickoff(inputs={})

        with execution_lock:
            execution_state["status"] = "completed"
            execution_state["result"] = str(result)
            execution_state["completed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    except Exception as e:
        with execution_lock:
            execution_state["status"] = "error"
            execution_state["error"] = str(e)
            execution_state["completed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@app.route("/")
def index():
    """메인 웹페이지"""
    return render_template("index.html")


@app.route("/run", methods=["POST"])
def run_crew():
    """CrewAI 실행 트리거"""
    global execution_state

    with execution_lock:
        if execution_state["status"] == "running":
            return jsonify({"success": False, "message": "이미 실행 중입니다."}), 409

        execution_state = {
            "status": "running",
            "result": None,
            "error": None,
            "started_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "completed_at": None,
        }

    thread = threading.Thread(target=run_crew_task, daemon=True)
    thread.start()

    return jsonify({"success": True, "message": "실행이 시작되었습니다."})


@app.route("/status")
def get_status():
    """현재 실행 상태 반환"""
    with execution_lock:
        return jsonify(execution_state)


def send_gmail(to_email: str, subject: str, body_text: str) -> dict:
    """Gmail SMTP를 통해 이메일 발송"""
    gmail_address = os.getenv("GMAIL_ADDRESS")
    gmail_password = os.getenv("GMAIL_APP_PASSWORD")

    if not gmail_address or not gmail_password:
        return {"success": False, "error": "GMAIL_ADDRESS 또는 GMAIL_APP_PASSWORD가 .env에 설정되지 않았습니다."}

    # HTML 본문 구성
    html_body = f"""\
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: 'Malgun Gothic', sans-serif; background: #f5f5f5; padding: 20px;">
      <div style="max-width: 700px; margin: 0 auto; background: #fff; border-radius: 12px; padding: 30px; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
        <h1 style="color: #1565c0; border-bottom: 2px solid #1565c0; padding-bottom: 12px;">🛡️ 방산 뉴스 한국어 일일 다이제스트</h1>
        <p style="color: #888; font-size: 14px;">발행일: {datetime.now().strftime("%Y년 %m월 %d일 %H:%M")}</p>
        <div style="white-space: pre-wrap; line-height: 1.8; font-size: 15px; color: #333;">{body_text}</div>
        <hr style="margin-top: 30px; border: none; border-top: 1px solid #eee;">
        <p style="color: #aaa; font-size: 12px;">이 뉴스레터는 AI 에이전트에 의해 자동 생성되었습니다.</p>
      </div>
    </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = gmail_address
    msg["To"] = to_email

    msg.attach(MIMEText(body_text, "plain", "utf-8"))
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(gmail_address, gmail_password)
            server.sendmail(gmail_address, to_email, msg.as_string())
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.route("/send-email", methods=["POST"])
def send_email():
    """결과를 이메일로 발송"""
    data = request.get_json()
    to_email = data.get("to", "").strip() if data else ""

    if not to_email:
        return jsonify({"success": False, "message": "수신자 이메일 주소를 입력해 주세요."}), 400

    with execution_lock:
        result = execution_state.get("result")

    if not result:
        return jsonify({"success": False, "message": "발송할 결과가 없습니다. 먼저 실행을 완료해 주세요."}), 400

    subject = f"🛡️ 방산 뉴스 한국어 일일 다이제스트 - {datetime.now().strftime('%Y-%m-%d')}"
    send_result = send_gmail(to_email, subject, result)

    if send_result["success"]:
        return jsonify({"success": True, "message": f"{to_email}으로 발송 완료되었습니다."})
    else:
        return jsonify({"success": False, "message": f"발송 실패: {send_result['error']}"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
