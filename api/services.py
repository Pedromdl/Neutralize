import os
import json
from django.conf import settings
from .models import IADataUsuario

# Remova chamadas diretas a SDKs em favor de função wrapper que centraliza env vars
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

PROMPT_BASE = '''
Você é um assistente clínico que extrai dados estruturados de textos (anamnese, sessão, treino, avaliação).

Entrada: {texto}
Tipo: {tipo}

Retorne apenas JSON com o formato:
{{
    "identificacao": {{"idade": null, "sexo": null, "profissao": null}},
    "historico_medico": [ ... ],
    "dores": [{{"local": "joelho", "intensidade": "3/10", "padrao": "aguda", "fatores_agravantes: quando agacha ou deita", "data_inicio": "2025-01-10"}}],
    "cirurgias": [...],
    "restricoes": [...],
    "respostas_ao_tratamento": [...],
    "exercicios_eficazes": [...],
    "outros": {{}}
}}

Use formatos de data ISO (YYYY-MM-DD) quando possível. Não retorne texto fora do JSON.
'''


def chamar_openai(prompt_text):
# wrapper mínimo — aqui exemplificamos com requests para a API oficial
    import requests
    headers = {
        'Authorization': f'Bearer {OPENAI_API_KEY}',
        'Content-Type': 'application/json'
        }
    body = {
        'model': 'gpt-4o-mini',
        'messages': [{'role':'user','content': prompt_text}],
        'temperature': 0
        }
    resp = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=body)
    resp.raise_for_status()
    j = resp.json()
    content = j['choices'][0]['message']['content']
    return content

def merge_kb(kb: IADataUsuario, novo_bloco: dict) -> dict:
    kb_dict = kb.dados or {}


    # Regras de merge (exemplos)
    # - Campos simples: sobrescrever se não-nulo
    for key, val in novo_bloco.items():
        if isinstance(val, list):
            existing = kb_dict.get(key, [])
            # concat sem duplicatas (por identidade simples)
            combined = existing + [v for v in val if v not in existing]
            kb_dict[key] = combined
        elif isinstance(val, dict):
            existing = kb_dict.get(key, {})
            merged = {**existing, **val}
            kb_dict[key] = merged
        else:
            # sobrescrever apenas se valor novo for não-nulo
            if val is not None:
                kb_dict[key] = val


    kb.dados = kb_dict
    kb.save(update_fields=['dados'])
    return kb.dados

PROMPT_INSIGHTS = """
Você é um sistema avançado de análise clínica especializado em identificar padrões de evolução e sugerir próximos passos baseados em dados reais do paciente.

A seguir está o CONHECIMENTO ESTRUTURADO do paciente (KB):

{kb}

TAREFA:
Analise o KB focando em:

1. Progresso clínico desde a última atualização
2. Mudanças observadas nos sintomas, dores e capacidade física
3. Fatores que pioraram ou melhoraram recentemente
4. Comportamentos que aceleram a evolução
5. Riscos atuais baseados na progressão
6. Previsão aproximada de evolução considerando:
   - tempo desde o início dos sintomas
   - tempo da última consulta ou atualização
   - respostas ao tratamento
7. Sugestões práticas para próximas sessões
8. Em qual camada (fundamental, intermediária, superior) o paciente está e qual a próxima etapa recomendada

FORMATO DA RESPOSTA (JSON):
{{
  "resumo_evolucao": "...",
  "melhoras_observadas": [...],
  "pontos_de_alerta": [...],
  "mudancas_recentes": [...],
  "estimativa_prognostica": "...",
  "foco_proxima_sessao": [...],
  "proxima_etapa_camadas": "fundamental | intermediária | superior"
}}
"""



def build_insights_prompt(contexto: dict):
    kb = contexto.get("kb", {})

    prompt = PROMPT_INSIGHTS.format(
        kb=json.dumps(kb, ensure_ascii=False, indent=2)
    )

    return prompt

PROMPT_QUESTION_CHAT = """
Você é um assistente clínico avançado. 
Baseie TODA a resposta APENAS no KB do paciente fornecido abaixo. 
Se a pergunta não puder ser respondida com os dados disponíveis, diga exatamente:
"Nenhuma informação suficiente no KB para responder com segurança."

KB DO PACIENTE:
{kb}

PERGUNTA DO PROFISSIONAL:
{pergunta}

RESPOSTA (texto objetivo e baseado em evidências clínicas):
"""

def build_chat_prompt(kb: dict, pergunta: str):
    return PROMPT_QUESTION_CHAT.format(
        kb=json.dumps(kb, indent=2, ensure_ascii=False),
        pergunta=pergunta
    )


def interpretar_texto_e_salvar(kb: IADataUsuario, texto: str, tipo: str):
    prompt = PROMPT_BASE.format(texto=texto, tipo=tipo)
    content = chamar_openai(prompt)


    # tentar parsear JSON; tolerância a texto adicional
    try:
        novo = json.loads(content)
    except Exception:
    # heurística: extrair primeiro bloco JSON
        import re
        m = re.search(r"\{.*\}", content, flags=re.DOTALL)
        if not m:
            raise ValueError('Resposta da IA não continha JSON parseável')
            novo = json.loads(m.group(0))

    merged = merge_kb(kb, novo)
    return {'status': 'ok', 'merged': merged}