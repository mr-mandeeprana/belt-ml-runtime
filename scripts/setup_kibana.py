import requests
import os
import time

KIBANA_URL = os.getenv("KIBANA_URL", "http://kibana.elastic.svc.cluster.local:5601")

INDEX_PATTERNS = [
    {"name": "belt-index*", "time_field": "@timestamp"},
    {"name": "belt-raw-data*", "time_field": "@timestamp"}
]

def setup_kibana():
    print(f"Connecting to Kibana at {KIBANA_URL}...")
    headers = {"kbn-xsrf": "true", "Content-Type": "application/json"}
    
    for pattern in INDEX_PATTERNS:
        url = f"{KIBANA_URL}/api/index_patterns/index_pattern"
        payload = {
            "index_pattern": {
                "title": pattern["name"],
                "timeFieldName": pattern["time_field"]
            }
        }
        
        try:
            resp = requests.post(url, headers=headers, json=payload)
            if resp.status_code in [200, 201]:
                print(f"✅ Created index pattern: {pattern['name']}")
            elif resp.status_code == 409:
                print(f"ℹ️ Index pattern {pattern['name']} already exists.")
            else:
                print(f"❌ Failed to create {pattern['name']}: {resp.status_code} {resp.text}")
        except Exception as e:
            print(f"❌ Error connecting to Kibana: {e}")

if __name__ == "__main__":
    # Wait for Kibana to be ready
    print("Waiting for Kibana service...")
    time.sleep(5)
    setup_kibana()
