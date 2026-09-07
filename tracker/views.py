from datetime import date, timedelta

from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST
from django.views.generic import CreateView

from . import openfoodfacts
from .forms import EntryForm, SignUpForm
from .models import Entry, Food
from .reports import build_weekly_report, week_bounds


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


def _logged_days(user, start, end):
    entries = Entry.objects.filter(user=user, eaten_on__range=(start, end))
    return entries.values("eaten_on").distinct().count()


def _default_week(user, start, end, *, min_days=3, look_back_weeks=8):
    """The week to open the dashboard on when none was requested: the current
    week, unless it's nearly empty (the first day or two of a fresh week) —
    then the most recent earlier week with at least ``min_days`` days logged."""
    current = (start, end)
    for _week in range(look_back_weeks + 1):
        if _logged_days(user, start, end) >= min_days:
            return start, end
        start, end = start - timedelta(days=7), end - timedelta(days=7)
    return current  # nothing better — stay on the current week


@login_required
def dashboard(request):
    try:
        anchor = date.fromisoformat(request.GET["week"])
        start, end = week_bounds(anchor)
    except (KeyError, ValueError):
        start, end = _default_week(request.user, *week_bounds(timezone.localdate()))

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

    # The nutrition data is resolved server-side from the barcode, never read
    # from the POST — the browser only gets to say *which* product and how much.
    food = Food.objects.filter(off_code=off_code).first()
    if food is None:
        product = openfoodfacts.resolve(off_code)
        if product is None:
            return render(
                request,
                "tracker/_day_entries.html",
                _log_context(request, error=_("Couldn't look that product up just now — try again.")),
            )
        food, _created = Food.objects.get_or_create(
            off_code=off_code,
            defaults={key: value for key, value in product.items() if key != "off_code"},
        )

    form = EntryForm(request.POST)
    error = None
    if form.is_valid():
        entry = form.save(commit=False)
        entry.user = request.user
        entry.food = food
        entry.save()
    else:
        error = _("Enter a portion in grams — a whole number, 1 or more.")

    if request.htmx:
        return render(request, "tracker/_day_entries.html", _log_context(request, error=error))
    return redirect("log")


@login_required
@require_POST
def delete_entry(request, pk):
    get_object_or_404(Entry, pk=pk, user=request.user).delete()
    if request.htmx:
        return render(request, "tracker/_day_entries.html", _log_context(request))
    return redirect("log")


def _log_context(request, error=None):
    today = timezone.localdate()
    entries = (
        Entry.objects.filter(user=request.user, eaten_on=today).select_related("food").order_by("created_at")
    )
    return {"today": today, "day_entries": entries, "form": EntryForm(), "error": error}
