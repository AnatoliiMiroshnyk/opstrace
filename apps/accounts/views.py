from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from apps.accounts.forms import RegistrationForm


@require_http_methods(["GET", "POST"])
def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user, workspace = form.save()
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        request.session["workspace_id"] = workspace.pk
        messages.success(request, "Робочий простір створено. Вітаємо в OpsTrace!")
        return redirect("dashboard")
    return render(request, "accounts/register.html", {"form": form})
