#!/usr/bin/env python
"""
방산 뉴스 한국어 일일 다이제스트 - 웹 인터페이스
Flask 기반 단일 웹페이지로 CrewAI 실행 및 결과 확인
"""
import os
import sys
import threading
import time
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, jsonify

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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
