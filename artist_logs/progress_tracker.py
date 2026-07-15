# artist_logs/progress_tracker.py
import json
import time
from django.http import StreamingHttpResponse, HttpResponseForbidden, HttpResponse
from django.views.decorators.http import require_GET
from django.contrib.auth.models import AnonymousUser

# Global progress tracker
upload_progress = {
    'current': 0,
    'total': 0,
    'status': 'idle',  # 'idle', 'processing', 'complete'
    'imported': 0,
    'errors': [],
    'time': 0
}

@require_GET
def sse_upload_progress(request):
    """Dedicated endpoint for SSE progress updates"""
    # Debug: Check if we're getting here
    print("DEBUG: SSE endpoint called")

    # Check authentication
    if not hasattr(request, 'user') or isinstance(request.user, AnonymousUser):
        print("DEBUG: User not authenticated for SSE")
        return HttpResponseForbidden("Not authenticated")

    # Set headers for SSE
    response = StreamingHttpResponse(
        progress_generator(),
        content_type='text/event-stream'
    )
    response['Cache-Control'] = 'no-cache'
    response['Connection'] = 'keep-alive'
    return response

def progress_generator():
    """Generator function for SSE updates"""
    print("DEBUG: Starting progress generator")
    try:
        # Send initial state
        yield f"data: {json.dumps(upload_progress)}\n\n"

        # Keep connection open and send updates
        while upload_progress['status'] != 'complete':
            time.sleep(0.5)
            yield f"data: {json.dumps(upload_progress)}\n\n"

        # Send final state
        yield f"data: {json.dumps(upload_progress)}\n\n"
        print("DEBUG: Upload complete, closing SSE connection")

    except GeneratorExit:
        print("DEBUG: Client disconnected from SSE")
    except Exception as e:
        print(f"DEBUG: Error in progress generator: {str(e)}")