"""
Analytics service for tracking URL redirects.
"""
import json
from typing import Optional, Dict, Any
from datetime import datetime
import pika

from app.core.config import settings
from app.core.request_id import generate_request_id

def track_click(
    short_code: str,
    request_headers: Optional[Dict[str, str]] = None,
    request_id: Optional[str] = None
) -> str:
    """
    Track a click on a short URL.
    
    Args:
        short_code: The short code that was clicked
        request_headers: HTTP headers from the request (for analytics)
        request_id: Optional request ID for idempotency
        
    Returns:
        The request ID used for tracking
    """
    if request_id is None:
        request_id = generate_request_id()
    
    # Prepare click event data
    click_event = {
        "event_type": "click",
        "timestamp": datetime.utcnow().isoformat(),
        "request_id": request_id,
        "short_code": short_code,
        "user_agent": request_headers.get("user-agent") if request_headers else None,
        "ip_address": request_headers.get("x-forwarded-for") if request_headers else None,
        "referrer": request_headers.get("referer") if request_headers else None,
    }
    
    # Publish to message queue
    try:
        # Using BlockingConnection in a separate thread to avoid blocking
        import threading
        
        def publish_event():
            try:
                connection = pika.BlockingConnection(
                    pika.URLParameters(settings.RABBITMQ_URL)
                )
                channel = connection.channel()
                channel.exchange_declare(exchange='analytics', exchange_type='direct')
                channel.queue_declare(queue='click_events', durable=True)
                channel.queue_bind(exchange='analytics', queue='click_events', routing_key='click')
                
                channel.basic_publish(
                    exchange='analytics',
                    routing_key='click',
                    body=json.dumps(click_event),
                    properties=pika.BasicProperties(
                        delivery_mode=2,  # Make message persistent
                        message_id=request_id,
                    )
                )
                connection.close()
            except Exception as e:
                # Log the error but don't fail the request
                print(f"Failed to publish analytics event: {e}")
        
        # Start a new thread to publish the event
        thread = threading.Thread(target=publish_event)
        thread.daemon = True
        thread.start()
        
    except Exception as e:
        # Log the error but don't fail the request
        print(f"Error in analytics tracking: {e}")
    
    return request_id
