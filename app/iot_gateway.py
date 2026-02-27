import json
import time
import random
import os
from datetime import datetime, timezone
from kafka import KafkaProducer
from app.config_loader import ConfigLoader

class IoTGateway:
    def __init__(self, kafka_bootstrap=None):
        self.bootstrap_servers = kafka_bootstrap or os.getenv("KAFKA_BOOTSTRAP", "localhost:9092")
        self.producer = None
        self.config_loader = ConfigLoader()
        self.model_config = self.config_loader.load_model_config()
        self.target_topic = "belt-data"
        
        # Extract base sensor names from model features
        # e.g., "temperature_head_inside/temperature_avg_value" -> "temperature_head_inside/temperature"
        self.valid_sensors = set()
        for feature in self.model_config.get("features", []):
            if "_avg_value" in feature:
                self.valid_sensors.add(feature.split("_avg_value")[0])
            elif "_warning_flag" in feature:
                self.valid_sensors.add(feature.split("_warning_flag")[0])
            elif "_critical_flag" in feature:
                self.valid_sensors.add(feature.split("_critical_flag")[0])

    def connect(self):
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=self.bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                retries=5,
                request_timeout_ms=5000
            )
            print(f"Connected to Kafka at {self.bootstrap_servers}")
        except Exception as e:
            print(f"Warning: Failed to connect to Kafka: {e}")
            print("Running in DRY-RUN mode (logging only)")
            self.producer = None

    def ingest(self, record):
        """
        Ingests a single record, validates it, and pushes to Kafka.
        record format: {sensorid, @timestamp, max_value, min_value, avg_value, std_deviation}
        """
        sensor_id = record.get("sensorid")
        if sensor_id not in self.valid_sensors:
            return False

        if self.producer:
            try:
                self.producer.send(self.target_topic, record)
                return True
            except Exception as e:
                print(f"Error sending to Kafka: {e}")
                return False
        else:
            print(f"[Dry-Run] Sent: {sensor_id} @ {record.get('@timestamp')}")
            return True

    def simulate(self, interval=1.0):
        """
        Simulates a continuous stream of IoT data.
        """
        print(f"Starting simulation for {len(self.valid_sensors)} sensors...")
        belt_id = "BELT_001" 
        
        try:
            while True:
                for sensor in self.valid_sensors:
                    avg = 50.0 + random.uniform(-5, 5)
                    record = {
                        "sensorid": sensor,
                        "@timestamp": datetime.now(timezone.utc).isoformat(),
                        "max_value": avg + random.uniform(0, 2),
                        "min_value": avg - random.uniform(0, 2),
                        "avg_value": avg,
                        "std_deviation": random.uniform(0.1, 0.5),
                        "belt_id": belt_id
                    }
                    self.ingest(record)
                
                if self.producer:
                    self.producer.flush()
                
                time.sleep(interval)
        except KeyboardInterrupt:
            print("Simulation stopped.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--simulate", action="store_true", help="Run in simulation mode")
    parser.add_argument("--interval", type=float, default=1.0, help="Simulation interval")
    parser.add_argument("--kafka", type=str, help="Kafka bootstrap server")
    
    args = parser.parse_args()
    
    gateway = IoTGateway(kafka_bootstrap=args.kafka)
    
    if args.simulate:
        gateway.connect()
        gateway.simulate(interval=args.interval)
    else:
        print("IoT Gateway ready. Use --simulate to start generating data.")
