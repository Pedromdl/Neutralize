from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.db import models
from django import forms
from django.utils.html import format_html

from .models import CustomUser, Organizacao


@admin.register(Organizacao)
class OrganizacaoAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'nome',
        'tipo_pessoa',
        'tipo',
        'cpf',
        'cnpj',
        'telefone',
        'data_criacao',
    )

    list_filter = (
        'tipo_pessoa',
        'tipo',
        'data_criacao',
    )

    search_fields = (
        'nome',
        'cpf',
        'cnpj',
        'telefone',
    )

    readonly_fields = ('data_criacao',)

    fieldsets = (
        ("Informações Básicas", {
            "fields": ("nome", "logo")
        }),
        ("Classificação", {
            "fields": ("tipo_pessoa", "tipo")
        }),
        ("Documentação", {
            "fields": ("cpf", "cnpj")
        }),
        ("Contato", {
            "fields": ("telefone",)
        }),
        ("Endereço", {
            "fields": ("endereco", "numero", "complemento")
        }),
        ("Integração Asaas", {
            "fields": ("asaas_customer_id", "credit_card_token")
        }),
        ("Meta", {
            "fields": ("data_criacao",),
        }),
    )



class CustomUserAdmin(UserAdmin):
    model = CustomUser

    list_display = (
        "id",
        "email",
        "first_name",
        "last_name",
        "organizacao_id_display",   # ✅ novo
        "role",
        "is_staff",
        "is_active",
    )

    list_filter = ("is_staff", "is_active", "organizacao")  # ✅ novo filtro
    search_fields = ("email", "first_name", "last_name")
    ordering = ("email",)

    # ----- MÉTODOS DE EXIBIÇÃO -----

    def organizacao_id_display(self, obj):  # ✅ novo método
        return obj.organizacao.id if obj.organizacao else "-"
    organizacao_id_display.short_description = "Organização ID"

    # ----- ESTILIZAÇÃO DE FOREIGNKEY -----
    formfield_overrides = {
        models.ForeignKey: {'widget': forms.Select(attrs={'style': 'width: 200px;'})},
    }

    # ----- FIELDSETS -----
    fieldsets = (
        (None, {
            "fields": (
                "email",
                "password",
                "role",
                "organizacao",  # ✅ novo campo
            )
        }),
        ("Informações Pessoais", {
            "fields": (
                "first_name",
                "last_name",
                "cpf",
                "address",
                "phone",
                "birth_date",
                "photo_google",
            )
        }),
        ("Permissões", {
            "fields": (
                "is_staff",
                "is_active",
                "is_superuser",
                "groups",
                "user_permissions",
            )
        }),
        ("Datas Importantes", {"fields": ("last_login", "date_joined")}),
    )

    readonly_fields = ("date_joined", "last_login")

    # ----- CAMPOS NA CRIAÇÃO DO USUÁRIO -----
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "email",
                "password1",
                "password2",
                "role",
                "organizacao",  # ✅ novo campo
                "is_staff",
                "is_active",
            ),
        }),
    )


admin.site.register(CustomUser, CustomUserAdmin)

