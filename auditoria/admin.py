from django.contrib import admin
from auditoria.models import AuditLog, Consentimento, RelatorioAcessoDados, PolíticaRetencaoDados


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('get_acao_display', 'usuario', 'modelo', 'objeto_id', 'timestamp', 'ip_address', 'removido')
    list_filter = ('acao', 'timestamp', 'removido', 'contem_dado_sensivel')
    search_fields = ('usuario__username', 'modelo', 'objeto_id', 'ip_address')
    readonly_fields = ('timestamp', 'hash_integridade', 'dados_antes', 'dados_depois')
    date_hierarchy = 'timestamp'

    fieldsets = (
        ('Ação', {
            'fields': ('acao', 'usuario', 'modelo', 'objeto_id')
        }),
        ('Dados', {
            'fields': ('dados_antes', 'dados_depois'),
            'classes': ('collapse',)
        }),
        ('Contexto', {
            'fields': ('ip_address', 'user_agent')
        }),
        ('LGPD', {
            'fields': ('consentimento', 'contem_dado_sensivel', 'data_retencao', 'removido', 'hash_integridade')
        }),
        ('Timestamp', {
            'fields': ('timestamp',),
            'classes': ('collapse',)
        }),
    )

    def has_add_permission(self, request):
        return False  # Logs não podem ser criados manualmente no admin

    def has_delete_permission(self, request, obj=None):
        return False  # Logs não podem ser deletados manualmente


@admin.register(Consentimento)
class ConsentimentoAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'tipo', 'consentido', 'data_consentimento', 'data_revogacao')
    list_filter = ('tipo', 'consentido', 'data_consentimento')
    search_fields = ('usuario__username', 'descricao')
    readonly_fields = ('data_consentimento',)
    date_hierarchy = 'data_consentimento'

    fieldsets = (
        ('Usuário e Tipo', {
            'fields': ('usuario', 'tipo', 'descricao')
        }),
        ('Status', {
            'fields': ('consentido', 'data_consentimento', 'data_revogacao')
        }),
        ('Contexto', {
            'fields': ('ip_consentimento', 'user_agent'),
            'classes': ('collapse',)
        }),
    )


@admin.register(RelatorioAcessoDados)
class RelatorioAcessoDadosAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'data_geracao', 'data_inicio', 'data_fim', 'acessos_registrados')
    list_filter = ('data_geracao', 'usuario')
    search_fields = ('usuario__username',)
    readonly_fields = ('data_geracao', 'hash_integridade')
    date_hierarchy = 'data_geracao'

    fieldsets = (
        ('Usuário', {
            'fields': ('usuario',)
        }),
        ('Período', {
            'fields': ('data_inicio', 'data_fim', 'data_geracao')
        }),
        ('Resultado', {
            'fields': ('acessos_registrados', 'hash_integridade')
        }),
    )

    def has_add_permission(self, request):
        return False  # Relatórios são gerados automaticamente


@admin.register(PolíticaRetencaoDados)
class PolíticaRetencaoDadosAdmin(admin.ModelAdmin):
    list_display = ('get_tipo_acao_display', 'dias_retencao', 'ativo')
    list_filter = ('ativo',)
    list_editable = ('dias_retencao', 'ativo')

    fieldsets = (
        ('Política', {
            'fields': ('tipo_acao', 'dias_retencao', 'ativo')
        }),
        ('Descrição', {
            'fields': ('descricao',)
        }),
    )
