"""Metricas personalizadas con Embedded Metric Format (sin dependencias)."""
import json
import time


def emit(service: str, **metrics: float) -> None:
    print(json.dumps({
        "_aws": {
            "Timestamp": int(time.time() * 1000),
            "CloudWatchMetrics": [{
                "Namespace": "ParlacheDelDia",
                "Dimensions": [["Service"]],
                "Metrics": [{"Name": k, "Unit": "Count"} for k in metrics],
            }],
        },
        "Service": service,
        **metrics,
    }))
