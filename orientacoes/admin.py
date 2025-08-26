from django.contrib import admin
from .models import Pasta, Secao, BancodeExercicio, Treino, ExercicioPrescrito, TreinoExecutado, SerieRealizada, ExercicioExecutado

# 🔹 Inline para exibir Seções dentro da Pasta
class SecaoInline(admin.TabularInline):
    model = Secao
    extra = 1

# 🔹 Inline para visualizar Exercícios de um Treino (template) diretamente no admin do Treino
class ExercicioPrescritoInline(admin.TabularInline):
    model = ExercicioPrescrito
    extra = 1
    fields = ('orientacao', 'series_planejadas', 'repeticoes_planejadas', 'carga_planejada')

# 🔹 Inline para visualizar Séries realizadas em uma execução de treino
class SerieRealizadaInline(admin.TabularInline):
    model = SerieRealizada
    extra = 1
    fk_name = "execucao"  # agora aponta para ExercicioExecutado

class ExercicioExecutadoInline(admin.TabularInline):
    model = ExercicioExecutado
    extra = 1

# 🔹 Admin do Treino (template)
@admin.register(Treino)
class TreinoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome', 'secao')
    list_filter = ('secao',)
    inlines = [ExercicioPrescritoInline]

# 🔹 Admin da Execução de Treino (cada vez que o paciente faz o treino)
@admin.register(TreinoExecutado)
class TreinoExecutadoAdmin(admin.ModelAdmin):
    list_display = ('treino', 'paciente', 'data', 'finalizado', 'tempo_total')
    list_filter = ('finalizado', 'data', 'treino')
    inlines = [ExercicioExecutadoInline]

@admin.register(ExercicioExecutado)
class ExercicioExecutadoAdmin(admin.ModelAdmin):
    list_display = ('id', 'treino_executado', 'exercicio', 'rpe')
    list_filter = ('treino_executado', 'exercicio')
    inlines = [SerieRealizadaInline]  # se quiser aninhar, precisa de NestedAdmin ou admin separado

@admin.register(SerieRealizada)
class SerieRealizadaAdmin(admin.ModelAdmin):
    list_display = ('id', 'execucao', 'exercicio', 'numero', 'repeticoes', 'carga')
    list_filter = ('execucao', 'exercicio')

# 🔹 Admin de Pasta
@admin.register(Pasta)
class PastaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'paciente')
    inlines = [SecaoInline]

# 🔹 Admin de Secao
@admin.register(Secao)
class SecaoAdmin(admin.ModelAdmin):
    list_display = ('id', 'titulo', 'pasta')
    list_filter = ('pasta',)

# 🔹 Admin de Banco de Exercício
@admin.register(BancodeExercicio)
class BancodeExercicioAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'descricao', 'video_url')
    search_fields = ('titulo',)
