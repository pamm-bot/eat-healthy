from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("log/", views.log_view, name="log"),
    path("log/search/", views.food_search, name="food_search"),
    path("log/add/", views.add_entry, name="add_entry"),
    path("log/entry/<int:pk>/delete/", views.delete_entry, name="delete_entry"),
]
