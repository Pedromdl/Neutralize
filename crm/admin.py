from django.contrib import admin
from .models import Contact, Interacao, AcaoPlanejada

# Register your models here.
@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'user')
    search_fields = ('name', 'email', 'phone', 'user__username')

@admin.register(Interacao)
class InteracaoAdmin(admin.ModelAdmin):
    list_display = ('pessoa', 'tipo', 'descricao', 'data')
    search_fields = ('pessoa', 'tipo')

@admin.register(AcaoPlanejada)
class AcaoPlanejadaAdmin(admin.ModelAdmin):
    list_display = ('pessoa', 'descricao', 'data_planejada')
    search_fields = ('pessoa', 'descricao')