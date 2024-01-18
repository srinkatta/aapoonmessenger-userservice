import json
from datetime import datetime, time

import pytz
from django.http import HttpResponse


class AppAvailabilityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = None
        if hasattr(self, "process_request"):
            response = self.process_request(request)
        if not response:
            response = self.get_response(request)
        if hasattr(self, "process_response"):
            response = self.process_response(request, response)
        return response

    def process_request(self, request):
        utc_now = datetime.now(tz=pytz.timezone("UTC"))
        ist_timezone = pytz.timezone("Asia/Kolkata")
        current_time_ist = utc_now.astimezone(ist_timezone)

        # Check if it's within the allowed time range and day
        if self.is_app_available(current_time_ist):
            return None  # Continue with the request
        else:
            return HttpResponse(
                json.dumps(
                    {
                        "detail": "APSCHE Messenger is offline between 9 PM and 9 AM IST, Monday to Friday, and on weekends."
                    }
                ),
                status=403,
                content_type="application/json",
            )

    def is_app_available(self, current_time_ist):
        # Check if it's within the allowed time range (9AM to 9PM IST)
        is_within_time_range = time(9, 0) <= current_time_ist.time() <= time(21, 0)

        # Return True if it's a weekday and within the time range
        # or if it's a weekend (as the app is available on weekends)
        return is_within_time_range
