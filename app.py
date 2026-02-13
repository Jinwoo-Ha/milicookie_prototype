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
import resend     # Resend 라이브러리 추가
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, jsonify, request

# 프로젝트 소스 경로 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

app = Flask(__name__)

# 한국 시간대 (UTC+9)
KST = timezone(timedelta(hours=9))

# 자동 발송 수신자 목록
SCHEDULED_RECIPIENTS = [
    "jinwooh0608@naver.com",
    "jinwooha79@gmail.com",
]

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
    """Resend API를 통해 이메일 발송 (SMTP 차단 우회)"""
    api_key = os.getenv("RESEND_API_KEY")
    if not api_key:
        return {"success": False, "error": "RESEND_API_KEY가 설정되지 않았습니다."}

    resend.api_key = api_key

    # HTML 본문 구성
    today = datetime.now().strftime("%Y년 %m월 %d일")
    time_now = datetime.now().strftime("%H:%M")

    # 본문 텍스트를 단락별로 HTML 변환
    paragraphs = body_text.split("\n")
    html_content_lines = []
    for line in paragraphs:
        stripped = line.strip()
        if not stripped:
            html_content_lines.append('<div style="height: 12px;"></div>')
        elif stripped == '---' or stripped == '***' or stripped == '___':
            continue
        elif stripped.startswith("Original Source:"):
            # 출처 라인 — 본문과 동일한 스타일
            html_content_lines.append(
                f'<p style="margin: 0 0 10px 0; color: #37474f; font-size: 16px; '
                f'line-height: 1.85;">{stripped}</p>'
            )
        elif stripped.startswith("#") or (len(stripped) < 80 and not stripped.endswith(".")):
            # 제목/소제목 스타일
            clean = stripped.lstrip("#").strip()
            # <배경>, <기사> 등 꺾쇠 괄호를 이스케이프하여 Gmail에서 태그로 해석되지 않도록 처리
            clean = clean.replace("<", "&lt;").replace(">", "&gt;")
            html_content_lines.append(
                f'<h2 style="color: #1a237e; font-size: 20px; font-weight: 700; '
                f'margin: 28px 0 12px 0; padding-bottom: 8px; '
                f'border-bottom: 2px solid #e8eaf6;">{clean}</h2>'
            )
        else:
            # 본문 내에도 <배경>, <기사> 등이 포함될 수 있으므로 이스케이프
            safe = stripped.replace("<", "&lt;").replace(">", "&gt;")
            html_content_lines.append(
                f'<p style="margin: 0 0 10px 0; color: #37474f; font-size: 16px; '
                f'line-height: 1.85;">{safe}</p>'
            )
    html_content = "\n".join(html_content_lines)

    html_body = f"""\
    <html>
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 0; background-color: #f0f2f5; font-family: -apple-system, 'Malgun Gothic', 'Noto Sans KR', 'Segoe UI', sans-serif; -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%;">
      <!-- 외부 컨테이너 -->
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color: #f0f2f5;">
        <tr>
          <td align="center" style="padding: 20px 12px;">
            <!-- 메인 카드 -->
            <table role="presentation" cellpadding="0" cellspacing="0" style="width: 100%; max-width: 680px; background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 24px rgba(0,0,0,0.08);">

              <!-- 헤더 배너 -->
              <tr>
                <td style="background: linear-gradient(135deg, #0d1b2a 0%, #1b3a5c 50%, #274472 100%); padding: 28px 24px 24px 24px;">
                  <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                    <tr>
                      <td>
                        <h1 style="margin: 0; font-size: 22px; font-weight: 800; color: #ffffff; letter-spacing: -0.5px;">🍪 밀리쿠키</h1>
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>

              <!-- 헤더 배너 끝 -->

              <!-- 본문 콘텐츠 -->
              <tr>
                <td style="padding: 20px 24px 28px 24px;">
                  {html_content}
                </td>
              </tr>

              <!-- 푸터 -->
              <tr>
                <td style="background-color: #fafafa; border-top: 1px solid #eeeeee; padding: 20px 24px;">
                  <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                    <tr>
                    </tr>
                  </table>
                </td>
              </tr>

            </table>
            <!-- 메인 카드 끝 -->
          </td>
        </tr>
      </table>
    </body>
    </html>
    """

    params = {
        "from": "MiliCookie <noreply@milicookie.cloud>",
        "to": [to_email],
        "subject": subject,
        "html": html_body,
        "text": body_text,
    }

    try:
        # Resend API 호출
        email = resend.Emails.send(params)
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.route("/send-email", methods=["POST"])
def send_email():
    """결과를 이메일로 발송하기"""
    data = request.get_json()
    to_email = data.get("to", "").strip() if data else ""

    if not to_email:
        return jsonify({"success": False, "message": "수신자 이메일 주소를 입력해 주세요."}), 400

    with execution_lock:
        result = execution_state.get("result")

    if not result:
        return jsonify({"success": False, "message": "발송할 결과가 없습니다. 먼저 실행을 완료해 주세요."}), 400

    subject = f"🍪 밀리쿠키 - {datetime.now(KST).strftime('%Y-%m-%d')}"
    send_result = send_gmail(to_email, subject, result)

    if send_result["success"]:
        return jsonify({"success": True, "message": f"{to_email}으로 발송 완료되었습니다."})
    else:
        return jsonify({"success": False, "message": f"발송 실패: {send_result['error']}"}), 500


def scheduled_crew_and_send():
    """스케줄러에 의해 호출: CrewAI 실행 후 자동 이메일 발송"""
    global execution_state
    now_kst = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[Scheduler] 자동 실행 시작 - {now_kst}")

    with execution_lock:
        if execution_state["status"] == "running":
            print("[Scheduler] 이미 실행 중이므로 건너뜁니다.")
            return

        execution_state = {
            "status": "running",
            "result": None,
            "error": None,
            "started_at": now_kst,
            "completed_at": None,
        }

    try:
        from defense_news_korean_daily_digest.crew import DefenseNewsKoreanDailyDigestCrew

        crew_instance = DefenseNewsKoreanDailyDigestCrew().crew()
        result = crew_instance.kickoff(inputs={})
        result_text = str(result)

        with execution_lock:
            execution_state["status"] = "completed"
            execution_state["result"] = result_text
            execution_state["completed_at"] = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")

        # 자동 이메일 발송
        subject = f"🍪 밀리쿠키 - {datetime.now(KST).strftime('%Y-%m-%d')}"
        for recipient in SCHEDULED_RECIPIENTS:
            send_result = send_gmail(recipient, subject, result_text)
            if send_result["success"]:
                print(f"[Scheduler] 이메일 발송 완료: {recipient}")
            else:
                print(f"[Scheduler] 이메일 발송 실패: {recipient} - {send_result.get('error')}")

    except Exception as e:
        with execution_lock:
            execution_state["status"] = "error"
            execution_state["error"] = str(e)
            execution_state["completed_at"] = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S")
        print(f"[Scheduler] 실행 오류: {e}")


def daily_scheduler():
    """매일 KST 21:10에 scheduled_crew_and_send를 실행하는 스케줄러"""
    TARGET_HOUR = 21
    TARGET_MINUTE = 10

    while True:
        now = datetime.now(KST)
        # 오늘 06:30 KST
        target = now.replace(hour=TARGET_HOUR, minute=TARGET_MINUTE, second=0, microsecond=0)

        # 이미 지났으면 내일 06:30으로 설정
        if now >= target:
            target += timedelta(days=1)

        wait_seconds = (target - now).total_seconds()
        next_run = target.strftime("%Y-%m-%d %H:%M:%S KST")
        print(f"[Scheduler] 다음 실행: {next_run} ({int(wait_seconds)}초 대기)")

        time.sleep(wait_seconds)

        # 별도 스레드에서 실행 (스케줄러 루프 차단 방지)
        thread = threading.Thread(target=scheduled_crew_and_send, daemon=True)
        thread.start()


if __name__ == "__main__":
    # 스케줄러 시작 (매일 KST 21:10 자동 실행)
    scheduler_thread = threading.Thread(target=daily_scheduler, daemon=True)
    scheduler_thread.start()
    print(f"[Scheduler] 스케줄러 시작됨 - 매일 KST 21:10 자동 실행")

    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
