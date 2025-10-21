from django.contrib import admin
from .models import EventoAgenda

# Register your models here.
@admin.register(EventoAgenda)
class EventoAgendaAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'data', 'status', 'responsavel')
    list_filter = ('status', 'data')
    search_fields = ('paciente__nome', 'responsavel') 
