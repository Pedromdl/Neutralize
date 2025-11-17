from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Clinica

@admin.register(Clinica)
class ClinicaAdmin(admin.ModelAdmin):
    list_display = ("nome", "cnpj", "telefone", "data_criacao")
    search_fields = ("nome", "cnpj")
    list_filter = ("data_criacao",)
    ordering = ("nome",)
    readonly_fields = ("data_criacao",)


class CustomUserAdmin(UserAdmin):
    model = CustomUser

    list_display = ("id", "email", "first_name", "last_name", "clinica", "is_staff", "is_active")
    list_filter = ("is_staff", "is_active", "clinica")
    search_fields = ("email", "first_name", "last_name")
    ordering = ("email",)

    fieldsets = (
        (None, {"fields": ("email", "password", "role", "clinica")}),
        ("Informações Pessoais", {
            "fields": ("first_name", "last_name", "cpf", "address", "phone", "birth_date")
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
