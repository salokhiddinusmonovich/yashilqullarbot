from django.shortcuts import render

# Create your views here.


# views.py
from django.shortcuts import render, get_object_or_404
from .models import ProjectParticipation

def qr_check(request, token):
    participation = get_object_or_404(ProjectParticipation, qr_token=token)

    return render(request, "idk/qr_check.html", {
        "user": participation.user,
        "project": participation.project,
        "status": participation.status,
    })
