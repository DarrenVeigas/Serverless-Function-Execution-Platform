def handler(event, context):
    """
    Simple test function that echoes back the event data
    """
    return {
        "message": "Function executed successfully!",
        "event": event,
        "context": {
            "function_name": context.get("function_name"),
            "request_id": context.get("request_id")
        }
    }