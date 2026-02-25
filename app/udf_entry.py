# app/udf_entry.py

import json
import traceback
from pynumaflow.function import Messages, Message, Datum, Server
from app.runtime import MLRuntime


_runtime = None


def get_runtime():
    global _runtime
    if _runtime is None:
        _runtime = MLRuntime()
    return _runtime


def handler(keys: list, datum: Datum) -> Messages:
    try:
        if not datum.value:
            return Messages(Message.to_all(b"{}"))

        raw_event = json.loads(datum.value.decode("utf-8"))
        result = get_runtime().process(raw_event)

        return Messages(Message.to_all(json.dumps(result).encode("utf-8")))

    except Exception as e:
        error_payload = json.dumps({
            "status": "error",
            "message": str(e),
            "trace": traceback.format_exc()
        }).encode("utf-8")
        return Messages(Message.to_all(error_payload))


if __name__ == "__main__":
    server = Server(map_handler=handler)
    server.start()
