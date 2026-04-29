from django.shortcuts import render


def frontend_app(request):
    return render(request, "webapp/index.html")
