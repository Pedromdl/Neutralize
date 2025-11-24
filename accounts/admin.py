from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.db import models
from django import forms
from django.utils.html import format_html

from .models import CustomUser, Clinica, Plano, Assinatura

@admin.register(Clinica)
class ClinicaAdmin(admin.ModelAdmin):
    list_display = ("id", "nome", "cnpj", "telefone", "data_criacao")
    search_fields = ("nome", "cnpj")
    list_filter = ("data_criacao",)
    ordering = ("nome",)
    readonly_fields = ("data_criacao",)


class CustomUserAdmin(UserAdmin):
    model = CustomUser

    list_display = (
        "id",
        "email",
        "first_name",
        "last_name",
        "clinica_id_display",
        "role",
        "is_staff",
        "is_active",
    )

    list_filter = ("is_staff", "is_active", "clinica")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("email",)

    def clinica_id_display(self, obj):
        return obj.clinica.id if obj.clinica else "-"
    clinica_id_display.short_description = "Clinica ID"

    formfield_overrides = {
        models.ForeignKey: {'widget': forms.Select(attrs={'style': 'width: 200px;'})},
    }

    fieldsets = (
        (None, {"fields": ("email", "password", "role", "clinica")}),
        ("Informações Pessoais", {
            "fields": (
                "first_name",
                "last_name",
                "cpf",
                "address",
                "phone",
                "birth_date",
                "photo_google",  # ✅ adiciona aqui também
            )
        }),
        ("Permissões", {
            "fields": ("is_staff", "is_active", "is_superuser", "groups", "user_permissions")
        }),
        ("Datas Importantes", {"fields": ("last_login", "date_joined")}),
    )

    readonly_fields = ('date_joined', 'last_login')

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "password1", "password2", "role", "clinica", "is_staff", "is_active")
        }),
    )

admin.site.register(CustomUser, CustomUserAdmin)
@admin.register(Plano)
class PlanoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'tipo', 'preco_mensal', 'max_pacientes', 'ativo']
    list_filter = ['tipo', 'ativo']

@admin.register(Assinatura)  
class AssinaturaAdmin(admin.ModelAdmin):
    list_display = ['clinica', 'plano', 'status', 'data_inicio']
    list_filter = ['status', 'plano']
