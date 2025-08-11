from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ("email", "first_name", "last_name", "is_staff", "is_active")
    list_filter = ("is_staff", "is_active")
    search_fields = ("email",)
    ordering = ("email",)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Informações Pessoais", {"fields": ("first_name", "last_name", "cpf", "address", "phone", "birth_date")}),
        ("Permissões", {"fields": ("is_staff", "is_active", "is_superuser", "groups", "user_permissions")}),
        ("Datas Importantes", {"fields": ("last_login", "date_joined")}),
    )
    readonly_fields = ('date_joined', 'last_login')
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "password1", "password2", "is_staff", "is_active")}
        ),
    )


admin.site.register(CustomUser, CustomUserAdmin)
