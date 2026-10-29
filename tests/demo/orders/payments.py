import hashlib
import hmac

from django.conf import settings
from django.core.exceptions import SuspiciousOperation


def verify_signature(request):
    expected = hmac.new(settings.PAYMENT_WEBHOOK_SECRET.encode(), request.body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, request.headers.get("X-Signature", "")):
        raise SuspiciousOperation("Invalid payment signature")
