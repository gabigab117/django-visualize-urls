from django.contrib.auth.middleware import LoginRequiredMiddleware


class ShopLoginRequiredMiddleware(LoginRequiredMiddleware):
    redirect_field_name = "back_to"
