from django.contrib import admin

from .models import Entry, Food


@admin.register(Food)
class FoodAdmin(admin.ModelAdmin):
    list_display = ("name", "brand", "nova_group", "nutriscore_grade", "plant_key")
    search_fields = ("name", "brand", "off_code")


@admin.register(Entry)
class EntryAdmin(admin.ModelAdmin):
    list_display = ("user", "food", "grams", "meal", "eaten_on")
    list_filter = ("meal", "eaten_on")
    search_fields = ("food__name",)
