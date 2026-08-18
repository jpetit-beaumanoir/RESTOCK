from django.contrib import admin
from django.urls import path
from core.views import home, filtrar, movimientos

urlpatterns = [
    path('', home, name='home'),
    path('api/filtros/', filtrar),
    path('api/movimientos/', movimientos),
]