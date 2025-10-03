"""
Analytics service for tracking URL redirects via Kafka.
"""
import json
from typing import Optional, Dict
from datetime import datetime

from aiokafka import AIOKafkaProducer

from app.core.config import settings
from app.core.request_id import generate_request_id

async def track_click_async(
    producer: AIOKafkaProducer,
    short_code: str,
    request_headers: Optional[Dict[str, str]] = None,
    request_id: Optional[str] = None,
) -> str:
    """
    Track a click on a short URL by publishing to Kafka asynchronously.
    """
    if request_id is None:
        request_id = generate_request_id()

    event = {
        "event_type": "click",
        "timestamp": datetime.utcnow().isoformat(),
        "request_id": request_id,
        "short_code": short_code,
        "user_agent": request_headers.get("user-agent") if request_headers else None,
        "ip_address": request_headers.get("x-forwarded-for") if request_headers else None,
        "referrer": request_headers.get("referer") if request_headers else None,
    }

    try:
        await producer.send_and_wait(
            topic=settings.KAFKA_TOPIC_CLICK_EVENTS,
            value=json.dumps(event).encode("utf-8"),
            key=short_code.encode("utf-8"),
        )
    except Exception as e:
        # Log but do not fail the request
        print(f"Kafka publish failed: {e}")

    return request_id
