"""Order views of the demo shop: one function view for each way of protecting it."""

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_not_required
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.views import redirect_to_login
from django.http import HttpResponse
from django.views.decorators.cache import cache_page
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from tests.demo.decorators import ajax_only
from tests.demo.decorators import api_key_required
from tests.demo.decorators import returns_manager_required
from tests.demo.decorators import staff_required
from tests.demo.orders.payments import verify_signature


@login_required
@never_cache
def order_list(request):
    return HttpResponse("Your orders")


@permission_required(["orders.change_order", "orders.refund_order"])
def order_refund(request, pk):
    return HttpResponse(f"Order {pk} refunded")


@staff_member_required
def order_export(request):
    return HttpResponse("orders.csv")


@staff_required
def order_stats(request):
    return HttpResponse("Statistics")


@user_passes_test(lambda user: user.is_superuser)
def order_purge(request):
    return HttpResponse("Old orders purged")


@login_required
@require_POST
def order_cancel(request, pk):
    return HttpResponse(f"Order {pk} cancelled")


@csrf_exempt
def payment_webhook(request):
    verify_signature(request)
    return HttpResponse(status=204)


def order_track(request, pk):
    if not request.user.is_authenticated:
        return redirect_to_login(request.get_full_path())
    return HttpResponse(f"Tracking of order {pk}")


@ajax_only
def order_summary(request, pk):
    return HttpResponse(f"Summary of order {pk}")


@api_key_required
def partner_feed(request):
    return HttpResponse("feed.xml")


@login_not_required
def order_receipt(request, token):
    return HttpResponse(f"Receipt {token}")


@cache_page(60 * 15)
def order_help(request):
    return HttpResponse("How to order")


@login_required
def return_list(request):
    return HttpResponse("Your returns")


@returns_manager_required
def return_create(request):
    return HttpResponse("New return")
