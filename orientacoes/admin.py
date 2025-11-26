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
    fields = ('orientacao', 'series_planejadas', 'repeticoes_planejadas', 'carga_planejada', 'observacao')

# 🔹 Inline para visualizar Séries realizadas em uma execução de treino
class SerieRealizadaInline(admin.TabularInline):
    model = SerieRealizada
    extra = 1
    fk_name = "execucao"  # agora aponta para ExercicioExecutado

from django.utils.html import format_html

class ExercicioExecutadoInline(admin.TabularInline):
    model = ExercicioExecutado
    fields = ('exercicio_nome', 'rpe_display', 'seriess_display')
    readonly_fields = ('exercicio_nome', 'rpe_display', 'seriess_display')
    extra = 0
    can_delete = False
    show_change_link = True

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Pré-carrega tudo para evitar N+1
        return qs.select_related('exercicio', 'exercicio__orientacao')

    def exercicio_nome(self, obj):
        return obj.exercicio.orientacao.titulo if obj.exercicio and obj.exercicio.orientacao else "-"
    exercicio_nome.short_description = "Exercício"

    def rpe_display(self, obj):
        return obj.rpe if obj.rpe is not None else "-"
    rpe_display.short_description = "RPE"

    def seriess_display(self, obj):
        if not obj.seriess:
            return "-"
        # Renderiza todas as séries detalhadas
        return format_html(
            "<br>".join(
                f"Série {s.get('numero', i+1)}: {s.get('repeticoes', '-')} reps @ {s.get('carga', '-')}"
                for i, s in enumerate(obj.seriess)
            )
        )
    seriess_display.short_description = "Séries"


# 🔹 Admin do Treino (template)
@admin.register(Treino)
class TreinoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome', 'secao')
    list_filter = ('secao',)
    inlines = [ExercicioPrescritoInline]

# 🔹 Admin da Execução de Treino (cada vez que o paciente faz o treino)
@admin.register(TreinoExecutado)
class TreinoExecutadoAdmin(admin.ModelAdmin):
    list_display = ('id', 'treino', 'paciente', 'data', 'finalizado', 'tempo_total')
    list_filter = ('finalizado', 'data', 'paciente__organizacao__nome')
    search_fields = ('paciente__organizacao__nome',)
    inlines = [ExercicioExecutadoInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('treino', 'paciente').prefetch_related(
            'exercicios',                     # ExercicioExecutado
            'exercicios__exercicio',          # ExercicioPrescrito
            'exercicios__exercicio__orientacao'  # BancodeExercicio
        )

@admin.register(ExercicioExecutado)
class ExercicioExecutadoAdmin(admin.ModelAdmin):
    list_display = ('id', 'treino_executado', 'exercicio', 'rpe', 'seriess')
    list_filter = ('treino_executado', 'exercicio')

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
