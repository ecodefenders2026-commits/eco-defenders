"""
ECO DEFENDERS — One-Click Prototype Execution & Demonstration Script
------------------------------------------------------------------
Checks dependencies, trains XGBoost model if missing, starts FastAPI server,
populates active IoT telemetry, and opens the live web dashboard in browser.
"""

import sys
import os
import time
import subprocess
import webbrowser
import requests

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(PROJECT_DIR, "models")
XGB_MODEL_PATH = os.path.join(MODELS_DIR, "xgboost_flood_v1.json")


def check_and_train():
    if not os.path.exists(XGB_MODEL_PATH):
        print("[DEMO] Model artifacts missing. Training XGBoost flood model pipeline...")
        subprocess.run([sys.executable, "src/train.py"], cwd=PROJECT_DIR, check=True)
    else:
        print("[DEMO] XGBoost production model pipeline verified.")


def start_server():
    print("[DEMO] Starting FastAPI Inference Server on http://localhost:8000...")
    cmd = [sys.executable, "-m", "uvicorn", "backend.app:app", "--host", "127.0.0.1", "--port", "8000"]
    proc = subprocess.Popen(cmd, cwd=PROJECT_DIR)
    
    # Wait for server readiness
    for _ in range(15):
        time.sleep(1)
        try:
            r = requests.get("http://127.0.0.1:8000/api/v1/health", timeout=1)
            if r.status_code == 200:
                print("[DEMO] Server successfully started and online!")
                return proc
        except Exception:
            pass
    return proc


def seed_initial_telemetry():
    print("[DEMO] Seeding initial node telemetry via API...")
    try:
        from src.simulator import run_scenario_stream
        for node in ["NODE_001", "NODE_002", "NODE_003", "NODE_004", "NODE_005"]:
            run_scenario_stream(node_id=node, scenario="NORMAL")
    except Exception as e:
        print(f"[DEMO WARN] Telemetry seed warning: {e}")


def main():
    print("==========================================================================")
    print("             ECO DEFENDERS — AI MULTI-HAZARD FLOOD ENGINE")
    print("==========================================================================")
    
    check_and_train()
    server_proc = start_server()
    
    seed_initial_telemetry()
    
    url = "http://localhost:8000/"
    print(f"\n[DEMO] Opening ECO DEFENDERS Live Dashboard at {url}...")
    webbrowser.open(url)
    
    print("\n[DEMO SERVER ACTIVE] Press Ctrl+C in terminal to stop server.")
    try:
        server_proc.wait()
    except KeyboardInterrupt:
        print("\n[DEMO] Stopping server...")
        server_proc.terminate()


if __name__ == "__main__":
    main()
