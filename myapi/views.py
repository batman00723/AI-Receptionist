from django.shortcuts import render

# Create your views here.
def dashboard(request):
    return render(request, "dashboard.html")

def demo_chat(request):
    return render(request, "demo.html")