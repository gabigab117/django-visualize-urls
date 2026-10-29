from django.http import HttpResponse


def archive(request, year):
    return HttpResponse(f"Orders of {year}")
