# 🔐 Sistema de Auditoria LGPD - Documentação

## 📋 Visão Geral

Sistema completo de auditoria e rastreabilidade LGPD-compliant para sua plataforma. Registra todas as ações (CREATE, READ, UPDATE, DELETE, LOGIN, etc.) com:

✅ Criptografia de dados sensíveis  
✅ Rastreabilidade por usuário/IP  
✅ Direito ao esquecimento (Art. 17)  
✅ Direito de acesso (Art. 18)  
✅ Consentimento revogável (Art. 8)  
✅ Retenção automática conforme LGPD  

---

## 🚀 Como Usar

### 1️⃣ Executar Migrations

```bash
python manage.py makemigrations auditoria
python manage.py migrate auditoria
```

### 2️⃣ Endpoints Disponíveis

#### 📝 **Consentimentos (LGPD Art. 7, I)**
- `GET /api/auditoria/consentimentos/` - Listar meus consentimentos
- `POST /api/auditoria/consentimentos/` - Criar novo consentimento
- `POST /api/auditoria/consentimentos/{id}/revogar/` - Revogar consentimento

**Exemplo de criação:**
```json
{
    "tipo": "DADOS_PESSOAIS",
    "descricao": "Coleta de dados para avaliação físioterápica",
    "consentido": true
}
```

#### 🔍 **Logs de Auditoria**
- `GET /api/auditoria/logs/` - Meus logs (usuário normal) / Todos (admin)
- `GET /api/auditoria/logs/por_usuario/?usuario_id=123` - Logs de um usuário (admin)
- `GET /api/auditoria/logs/por_periodo/?data_inicio=2024-01-01&data_fim=2024-01-31` - Filtrar por período
- `GET /api/auditoria/logs/suspeitos/` - Detectar atividades suspeitas (admin)

**Resposta exemplo:**
```json
{
    "id": 1,
    "usuario": "pedro@example.com",
    "acao": "CREATE",
    "modelo": "api.Usuario",
    "objeto_id": "42",
    "timestamp": "2024-12-04T10:30:00Z",
    "ip_address": "192.168.1.1",
    "removido": false
}
```

#### 📊 **Relatório de Acesso (LGPD Art. 18)**
- `POST /api/auditoria/relatorios/gerar_relatorio/` - Gerar relatório "Quem acessou meus dados"

**Body (opcional):**
```json
{
    "data_inicio": "2024-11-01",
    "data_fim": "2024-12-04"
}
```

**Resposta:**
```json
{
    "relatorio": {
        "id": 1,
        "usuario": 2,
        "data_geracao": "2024-12-04T10:35:00Z",
        "acessos_registrados": 15
    },
    "acessos_detalhados": [...],
    "resumo": {
        "periodo": "2024-11-01 a 2024-12-04",
        "total_acessos": 15,
        "acessos_por_tipo": {
            "READ": 10,
            "UPDATE": 5
        }
    }
}
```

#### 🗑️ **Direito ao Esquecimento (LGPD Art. 17)**
- `POST /api/auditoria/direito-esquecimento/solicitar_anonimizacao/` - Solicitar anonimização
- `GET /api/auditoria/direito-esquecimento/status_anonimizacao/` - Verificar status

**Body:**
```json
{
    "motivo": "Quero remover meus dados da plataforma"
}
```

**Resposta:**
```json
{
    "mensagem": "Direito ao esquecimento processado com sucesso",
    "dados_anonimizados": 142,
    "consentimentos_revogados": 3,
    "data_processamento": "2024-12-04T10:40:00Z"
}
```

#### ⚙️ **Políticas de Retenção (Admin)**
- `GET /api/auditoria/politicas-retencao/` - Listar políticas
- `POST /api/auditoria/politicas-retencao/limpar_logs_expirados/` - Deletar logs expirados
- `GET /api/auditoria/politicas-retencao/relatorio_retencao/` - Relatório de retenção

---

## 🔒 Fluxo Automático

### O que é registrado automaticamente?

O middleware `AuditoriaMiddleware` registra **todas** as requisições HTTP:

| Método | Ação Registrada | Retenção |
|--------|-----------------|----------|
| POST | CREATE | 30 dias (padrão) |
| GET | READ | 30 dias (padrão) |
| PUT/PATCH | UPDATE | 30 dias (padrão) |
| DELETE | DELETE | 2 anos (Art. 16) |
| Login | LOGIN | 6 meses |
| Acesso negado | PERMISSAO_NEGADA | 30 dias |

### Dados Sensíveis

Endpoints que contêm data sensível são marcados automaticamente:

```python
ENDPOINTS_SENSIVEL = {
    'usuario': 'SAUDE',
    'sessao': 'SAUDE',
    'prescricao': 'SAUDE',
    'medicamento': 'SAUDE',
    'paciente': 'SAUDE',
}
```

Dados sensíveis têm retenção de **1 ano** (mais rigoroso).

---

## 🛡️ Segurança

### Criptografia

- **Dados antes/depois**: Criptografados no BD com `EncryptedTextField`
- **Integridade**: Hash SHA256 único por log (imutável)

### Permissões

- **Admin**: Vê todos os logs
- **User**: Vê apenas seus próprios logs
- **Público**: Acesso negado

---

## 📋 Admin Django

Acesse em `/admin/auditoria/` para:

✅ Visualizar todos os logs  
✅ Filtrar por período, usuário, ação  
✅ Gerenciar consentimentos  
✅ Gerar relatórios  

---

## ⚖️ Conformidade LGPD

| Artigo | Implementação |
|--------|---------------|
| Art. 5, XII | ✅ Rastreabilidade em `AuditLog` |
| Art. 7, I | ✅ Consentimento em `Consentimento` |
| Art. 8 | ✅ Revogação em `Consentimento.revogar()` |
| Art. 15 | ✅ Dados criptografados em `EncryptedTextField` |
| Art. 16 | ✅ Retenção automática em `data_retencao` |
| Art. 17 | ✅ Anonimização em `AuditLog.anonimizar()` |
| Art. 18 | ✅ Relatório em `RelatorioAcessoDados` |

---

## 🔧 Customizações

### Alterar Período de Retenção

Edite `auditoria/models.py`, método `AuditLog.save()`:

```python
if self.acao == 'DELETE':
    # Mudar de 2 anos para 3 anos
    self.data_retencao = timezone.now() + timedelta(days=1095)
```

### Adicionar Novos Tipos de Dados Sensíveis

```python
ENDPOINTS_SENSIVEL = {
    'usuario': 'SAUDE',
    'biometria': 'BIOMETRIA',  # ← novo
    'localizacao': 'LOCALIZACAO',  # ← novo
}
```

### Ignorar Endpoints da Auditoria

```python
ENDPOINTS_IGNORADOS = [
    '/static/',
    '/media/',
    '/meu/endpoint/custom/',  # ← novo
]
```

---

## 📚 Referências

- **LGPD**: Lei Geral de Proteção de Dados (Lei 13.709/2018)
- **Django Docs**: https://docs.djangoproject.com/
- **DRF**: https://www.django-rest-framework.org/

---

## ⚠️ Avisos Importantes

1. ⚠️ **Não delete logs manualmente** - Use anonimização
2. ⚠️ **Backup regular** - Logs são críticos para compliance
3. ⚠️ **Monitorar acessos suspeitos** - Endpoint `/logs/suspeitos/`
4. ⚠️ **GDPR**: Se usa EU data, aplicam mais restrições

---

## 🆘 Troubleshooting

**P: Os logs não estão sendo criados**  
R: Verifique se `AuditoriaMiddleware` está em `MIDDLEWARE` no settings.py

**P: Erro "EncryptedTextField not found"**  
R: Certifique-se que `django-encrypted-model-fields` está instalado

**P: Performance lenta com muitos logs**  
R: Rode `python manage.py migrate` e use índices (já configurados)

---

**Desenvolvido para LGPD Compliance ✅**
