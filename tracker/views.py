from datetime import date, timedelta

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.generic import CreateView

from . import openfoodfacts
from .forms import EntryForm, SignUpForm
from .models import Entry, Food
from .reports import build_weekly_report, week_bounds

FOOD_FIELDS = (
    "off_code",
    "name",
    "brand",
    "nova_group",
    "nutriscore_grade",
    "energy_kcal",
    "protein_g",
    "fiber_g",
    "sugars_g",
    "salt_g",
    "plant_key",
)


class SignUpView(CreateView):
    form_class = SignUpForm
    template_name = "registration/signup.html"
    success_url = reverse_lazy("dashboard")

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        return response


def home(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "tracker/home.html")


@login_required
def dashboard(request):
    try:
        anchor = date.fromisoformat(request.GET["week"])
    except (KeyError, ValueError):
        anchor = timezone.localdate()

    start, end = week_bounds(anchor)
    entries = (
        Entry.objects.filter(user=request.user, eaten_on__range=(start, end))
        .select_related("food")
        .order_by("eaten_on")
    )
    report = build_weekly_report(entries, start=start, end=end)

    return render(
        request,
        "tracker/dashboard.html",
        {
            "report": report,
            "prev_week": start - timedelta(days=7),
            "next_week": start + timedelta(days=7),
            "is_current_week": start == week_bounds(timezone.localdate())[0],
        },
    )


@login_required
def log_view(request):
    return render(request, "tracker/log.html", _log_context(request))


@login_required
def food_search(request):
    query = request.GET.get("q", "").strip()
    barcode = request.GET.get("barcode", "").strip()

    if barcode:
        product = openfoodfacts.get_by_barcode(barcode)
        results = [product] if product else []
    else:
        results = openfoodfacts.search(query) if query else []

    return render(
        request,
        "tracker/_search_results.html",
        {"results": results, "form": EntryForm(), "query": query or barcode},
    )


@login_required
@require_POST
def add_entry(request):
    off_code = request.POST.get("off_code", "").strip()
    if not off_code:
        return redirect("log")

    defaults = {}
    for name in FOOD_FIELDS:
        if name == "off_code":
            continue
        value = request.POST.get(name, "").strip()
        if name == "nova_group":
            defaults[name] = int(value) if value.isdigit() else None
        elif name.endswith("_g") or name == "energy_kcal":
            defaults[name] = _as_float(value)
        else:
            defaults[name] = value

    food, _ = Food.objects.get_or_create(off_code=off_code, defaults=defaults)

    form = EntryForm(request.POST)
    if form.is_valid():
        entry = form.save(commit=False)
        entry.user = request.user
        entry.food = food
        entry.save()

    if request.htmx:
        return render(request, "tracker/_day_entries.html", _log_context(request))
    return redirect("log")


@login_required
@require_POST
def delete_entry(request, pk):
    get_object_or_404(Entry, pk=pk, user=request.user).delete()
    if request.htmx:
        return render(request, "tracker/_day_entries.html", _log_context(request))
    return redirect("log")


def _log_context(request):
    today = timezone.localdate()
    entries = (
        Entry.objects.filter(user=request.user, eaten_on=today).select_related("food").order_by("created_at")
    )
    return {"today": today, "day_entries": entries, "form": EntryForm()}


def _as_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
