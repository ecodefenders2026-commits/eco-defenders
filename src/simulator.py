"""
ECO DEFENDERS - Real-Time IoT Sensor Node Simulator
--------------------------------------------------
Simulates physical LoRa / Gateway IoT node telemetry streams for offline testing
and demonstration of disaster escalation scenarios.
"""

import sys
import time
import requests
import argparse

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

API_URL = "http://localhost:8000/api/v1/predict/flood"
SIMULATE_URL = "http://localhost:8000/api/v1/simulate"


def run_scenario_stream(node_id="NODE_017", scenario="FLOOD_WARNING"):
    print(f"\n[SIMULATOR] Launching simulated IoT Telemetry Stream for {node_id} (Scenario: {scenario})...")
    
    try:
        res = requests.post(f"{SIMULATE_URL}?scenario={scenario}&node_id={node_id}")
        data = res.json()
        print(f"[SIMULATOR] Server Response:")
        print(f"            Status: {res.status_code}")
        print(f"            Body  : {data}")
    except Exception as e:
        print(f"[SIMULATOR ERROR] Failed to connect to FastAPI server at {API_URL}. Is server running?")
        print(f"                  Error: {e}")


def run_demo_progression(node_id="NODE_001"):
    """
    Runs the full disaster escalation sequence:
    NORMAL -> HEAVY_RAIN -> RAPIDLY_RISING_WATER -> FLOOD_WARNING -> CRITICAL_FLOOD
    """
    scenarios = ["NORMAL", "HEAVY_RAIN", "RAPIDLY_RISING_WATER", "FLOOD_WARNING", "CRITICAL_FLOOD"]
    
    print(f"\n[DEMO MODE] Executing ECO DEFENDERS Live Disaster Escalation Sequence on {node_id}")
    print("==========================================================================")
    
    for step in scenarios:
        print(f"\n---> Triggering Stage: {step}")
        run_scenario_stream(node_id=node_id, scenario=step)
        time.sleep(2)
        
    print("\n[DEMO COMPLETE] Disaster progression simulated successfully. Check dashboard UI!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ECO DEFENDERS IoT Telemetry Simulator")
    parser.add_argument("--node", type=str, default="NODE_001", help="Node ID")
    parser.add_argument("--scenario", type=str, default="FLOOD_WARNING", help="Scenario name")
    parser.add_argument("--demo", action="store_true", help="Run full escalation demo sequence")
    
    args = parser.parse_args()
    
    if args.demo:
        run_demo_progression(args.node)
    else:
        run_scenario_stream(args.node, args.scenario)
