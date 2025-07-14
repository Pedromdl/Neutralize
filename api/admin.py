from django.contrib import admin

# Register your models here.
from .models import (Usuário, ForcaMuscular, Mobilidade, CategoriaTeste, TodosTestes, TesteFuncao, TesteDor, PreAvaliacao, Anamnese, Pasta,
                     Secao, Orientacao)

@admin.register(Usuário)
class UsuárioAdmin(admin.ModelAdmin):
    list_display = ('nome', 'data_de_nascimento',)

@admin.register(Mobilidade)
class MobilidadeAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'nome', 'data_avaliacao', 'lado_esquerdo', 'lado_direito', 'observacao')
    search_fields = ('paciente__nome', 'nome')
    list_filter = ('paciente__nome', 'data_avaliacao')

@admin.register(ForcaMuscular)
class ForcaMuscularAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'musculatura', 'data_avaliacao', 'lado_esquerdo', 'lado_direito', 'observacao')
    search_fields = ('paciente__nome', 'musculatura')
    list_filter = ('paciente__nome', 'data_avaliacao')

@admin.register(CategoriaTeste)
class CategoriaTesteAdmin(admin.ModelAdmin):
    list_display = ('nome',)
    search_fields = ('nome',)

@admin.register(TodosTestes)
class TodosTestesAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome', 'categoria')
    search_fields = ('nome',)
    list_filter = ('categoria',)

@admin.register(PreAvaliacao)
class PreAvaliacaoAdmin(admin.ModelAdmin):
    list_display = ('id', 'titulo', 'texto',)
    search_fields = ('titulo',)
    list_filter = ('titulo',)

@admin.register (Anamnese) 
class AnamneseAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'data_avaliacao')
    search_fields = ('paciente__nome',)
    list_filter = ('data_avaliacao',)

@admin.register(Pasta)
class PastaAdmin(admin.ModelAdmin):
    list_display = ('id','nome', 'paciente')
    search_fields = ('nome',)

admin.site.register(Secao)
admin.site.register(Orientacao)


@admin.register(TesteFuncao)
class TesteFuncaoAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'teste', 'data_avaliacao', 'lado_esquerdo', 'lado_direito', 'observacao')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "teste":
            try:
                categoria_funcao = CategoriaTeste.objects.get(nome__iexact="Testes de Função")
                kwargs["queryset"] = TodosTestes.objects.filter(categoria=categoria_funcao)
            except CategoriaTeste.DoesNotExist:
                kwargs["queryset"] = TodosTestes.objects.none()  # vazio se não existir
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

@admin.register(TesteDor)
class TesteDorAdmin(admin.ModelAdmin):
    list_display = ['id', 'paciente', 'teste', 'data_avaliacao', 'resultado', 'observacao']

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "teste":
            try:
                categoria_dor = CategoriaTeste.objects.get(nome__iexact="Testes de Dor")
                kwargs["queryset"] = TodosTestes.objects.filter(categoria=categoria_dor)
            except CategoriaTeste.DoesNotExist:
                kwargs["queryset"] = TodosTestes.objects.none()  # vazio se não existir
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
