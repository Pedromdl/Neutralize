from django.contrib import admin

# Register your models here.
from .models import (Usuário, ForcaMuscular, Mobilidade, Estabilidade, CategoriaTeste, TodosTestes, TesteFuncao, TesteDor, PreAvaliacao, Anamnese,
                     Evento, Sessao)

@admin.register(Usuário)
class UsuárioAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome', 'data_de_nascimento', 'organizacao')

@admin.register(Mobilidade)
class MobilidadeAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'nome', 'data_avaliacao', 'lado_esquerdo', 'lado_direito')
    search_fields = ('paciente__nome', 'nome')
    list_filter = ('paciente__nome', 'data_avaliacao')
    ordering = ('data_avaliacao',)

@admin.register(ForcaMuscular)
class ForcaMuscularAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'movimento_forca', 'data_avaliacao', 'lado_esquerdo', 'lado_direito', 'observacao')
    search_fields = ('paciente__nome', 'movimento_forca')
    list_filter = ('paciente__nome', 'data_avaliacao')

@admin.register(Estabilidade)
class EstabilidadeAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'movimento_estabilidade', 'data_avaliacao', 'lado_esquerdo', 'lado_direito', 'observacao')
    search_fields = ('paciente__nome', 'movimento_estabilidade')
    list_filter = ('paciente__nome', 'data_avaliacao')

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "movimento_estabilidade":
            try:
                categoria_estabilidade = CategoriaTeste.objects.get(nome__iexact="Testes de Estabilidade")
                kwargs["queryset"] = TodosTestes.objects.filter(categoria=categoria_estabilidade)
            except CategoriaTeste.DoesNotExist:
                kwargs["queryset"] = TodosTestes.objects.none()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

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

admin.site.register(Evento)
@admin.register(Sessao)
class SessaoAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'data', 'titulo', 'descricao')
    search_fields = ('paciente__nome', 'titulo')
    list_filter = ('paciente__nome', 'data')
