import json
import os
import requests
import threading
import re
import time
import random
from openai import OpenAI
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from .models import Mensagem, EstadoIA
from django.utils.timezone import localtime

# -------------------------
# Configurações e tokens
# -------------------------
VERIFY_TOKEN = "neutralize_webhook"
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

CHATGPT_MODEL = "gpt-4o-mini"
client = OpenAI(api_key=OPENAI_API_KEY)

# -------------------------
# Caminho do arquivo TXT
# -------------------------
caminho_arquivo = os.path.join(os.path.dirname(__file__), "informacoes_clinica.txt")
try:
    with open(caminho_arquivo, "r", encoding="utf-8") as f:
        INFORMACOES_CLINICA = f.read()
except Exception as e:
    print("Erro ao ler arquivo de informações da clínica:", e)
    INFORMACOES_CLINICA = "Informações da clínica não disponíveis no momento."

# -------------------------
# Respostas fixas
# -------------------------
RESPOSTAS_FIXAS = {
    "valor": "Aqui estão os valores dos nossos serviços...",
    "horario": "Nosso horário de atendimento é de Segunda a Quinta-feira, das 8h às 11h e das 15h às 20h e na Sexta-Feira até às 19 horas.",
    "servico": "Oferecemos serviços de fisioterapia, avaliações biomecânicas e tratamentos personalizados.",
    "agendamento": "Encaminhei seu contato para o responsável por agendar a consulta. Em breve ele entrará em contato com você para confirmar o melhor dia e horário.",
    "convenio": "Trabalhamos apenas com atendimentos particulares para garantir atenção individualizada."
}

# -------------------------
# Funções auxiliares
# -------------------------
def salvar_mensagem(numero, texto, resposta):
    try:
        Mensagem.objects.create(numero=numero, texto=texto, resposta=resposta)
        print(f"💾 Mensagem salva: {numero} -> {texto}")
    except Exception as e:
        print("Erro ao salvar mensagem:", e)

def extrair_texto_mensagem(message):
    if "text" in message and "body" in message["text"]:
        return message["text"]["body"], "texto"
    elif "audio" in message:
        return "Paciente enviou um áudio.", "audio"
    elif "image" in message:
        return "Paciente enviou uma imagem.", "imagem"
    elif "sticker" in message:
        return "Paciente enviou um sticker.", "sticker"
    else:
        return "Paciente enviou uma mensagem não reconhecida.", "desconhecido"

def enviar_resposta_whatsapp(numero, mensagem):
    url = f"https://graph.facebook.com/v17.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    data = {"messaging_product": "whatsapp", "to": numero, "type": "text", "text": {"body": mensagem}}
    try:
        response = requests.post(url, headers=headers, json=data)
        print(f"📤 Mensagem enviada para {numero}: {mensagem}")
        return response.json()
    except Exception as e:
        print("Erro WhatsApp:", e)
        return {"error": str(e)}

def enviar_com_delay(numero, mensagem):
    delay = random.uniform(2.0, 3.5)
    time.sleep(delay)
    enviar_resposta_whatsapp(numero, mensagem)

def enviar_alerta_celular(titulo, mensagem):
    url = "https://api.pushover.net/1/messages.json"
    data = {
        "token": os.environ.get("PUSHOVER_API_TOKEN"),
        "user": os.environ.get("PUSHOVER_USER_KEY"),
        "title": titulo,
        "message": mensagem,
        "priority": 1
    }
    try:
        requests.post(url, data=data)
        print(f"📲 Alerta enviado: {mensagem}")
    except Exception as e:
        print("Erro ao enviar alerta:", e)

# -------------------------
# Leitura de seções do arquivo TXT
# -------------------------
def ler_secao(secao):
    try:
        conteudo = INFORMACOES_CLINICA
        padrao = rf"\[{secao}\](.*?)(?=\[\w+\]|$)"
        resultado = re.search(padrao, conteudo, re.DOTALL)
        if resultado:
            return resultado.group(1).strip()
        return ""
    except Exception as e:
        print(f"Erro ao ler seção {secao}:", e)
        return ""

# -------------------------
# Geração de respostas com ChatGPT
# -------------------------
def gerar_resposta_chatgpt(pergunta, system_prompt=None):
    try:
        prompt = system_prompt or f"""
Você é Nia, assistente inteligente da clínica Neutralize.
Seja cordial, empática e clara. Use informações da clínica apenas quando necessário.
Se não souber a resposta, diga que um profissional do consultório irá ajudá-lo.
Evite respostas robotizadas.
"""
        response = client.chat.completions.create(
            model=CHATGPT_MODEL,
            messages=[{"role": "system", "content": prompt}, {"role": "user", "content": pergunta}],
            max_tokens=300,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print("Erro ChatGPT:", e)
        return "Desculpe, ocorreu um erro ao processar sua pergunta."

# -------------------------
# Detecção semântica contextual
# -------------------------
def detectar_intencao_semantica(numero, texto):
    try:
        # Pega as últimas 4 mensagens do paciente
        historico = list(Mensagem.objects.filter(numero=numero).order_by('-id')[:4])

        # Cria contexto para o ChatGPT
        if historico:
            # Monta contexto como string
            contexto = ""
            print("=== Histórico do paciente ===")
            for mensagem in reversed(historico):
                print("Paciente:", mensagem.texto)  # print seguro
                contexto += f"Paciente: {mensagem.texto}\n"
            print("============================")
        else:
            contexto = ""
            print("=== Sem histórico do paciente ===")

        # Prompt para identificar intenção
        prompt = f"""
Você é Nia, assistente da clínica Neutralize.
Com base no histórico da conversa:
{contexto}

Mensagem atual:
"{texto}"

Identifique a intenção principal da mensagem.
Responda apenas com uma palavra entre:
["sintoma","agendamento","horario_funcionamento",
"horario_disponibilidade","servico","valor",
"convenio","encaminhar_profissional","geral"]
"""

        response = client.chat.completions.create(
            model=CHATGPT_MODEL,
            messages=[{"role": "system", "content": prompt}],
            max_tokens=10,
            temperature=0
        )

        intencao = response.choices[0].message.content.strip().lower()
        opcoes = ["sintoma","agendamento","horario_funcionamento",
                  "horario_disponibilidade","servico","valor",
                  "convenio","encaminhar_profissional","geral"]

        # Retorna intenção válida
        if intencao in opcoes:
            return intencao
        else:
            return "geral"

    except Exception as e:
        print("Erro na detecção semântica:", e)
        return "geral"

# -------------------------
# Respostas contextuais
# -------------------------
def gerar_resposta_contextual(intencao, texto):
    info = ler_secao(intencao) or ""
    print("Conteúdo da seção:", info)

    prompt = f"""
Você é Nia, assistente inteligente da clínica Neutralize.
Responda apenas com base nestas informações:
{info}

O paciente enviou: "{texto}"
A intenção identificada foi: "{intencao}"

Se não houver informação suficiente, diga:
"Infelizmente não tenho essa informação, mas posso te ajudar com horários de funcionamento, serviços ou dúvidas em relação ao nosso trabalho! 😊"

⚠️ Dicas: 
- Não inclua sugestões de agendamento se o paciente não mencionou agendar. Seja cordial e objetiva.
- Se o usuario relatar sintoma ou interesse em falar com profissional, dizer que encaminhara o numero e em breve ele entrara em contato.
- Se o usuario enviar  alguma saudacao, faca o mesmo e de seguimento na conversa falando sobre as informacoes da clinica.
⚠️ Responda de forma cordial, empática e natural, no máximo 600 caracteres.
"""
    return gerar_resposta_chatgpt(texto, prompt)

# -------------------------
# Responder profissional
# -------------------------
def responder_profissional(numero):
    mensagem = "Certo! Vou encaminhar seu contato para um fisioterapeuta. Em breve ele entrará em contato. 💬"
    enviar_com_delay(numero, mensagem)
    EstadoIA.objects.filter(numero=numero).update(ia_ativa=False)
    return mensagem

# -------------------------
# Geração principal de resposta
# -------------------------
def gerar_resposta(texto, numero):
    contato_existente = Mensagem.objects.filter(numero=numero).exists()
    saudacao = "" if contato_existente else "Olá! Sou a Nia, assistente da Neutralize. Posso te ajudar com horários, serviços e convênios. Para falar com um profissional, diga 'profissional'.\n\n"
    
    intencao = detectar_intencao_semantica(numero, texto)
    print("Intenção detectada:", intencao)

    # -----------------------------
    # Respostas fixas
    # -----------------------------
    if intencao == "sintoma":
        resposta = "Entendo! Não consigo avaliar sua dor, mas irei encaminhar seu contato para um fisioterapeuta da Neutralize. 💬"
        enviar_alerta_celular("Paciente relatou dor", f"Paciente {numero} relatou um sintoma: {texto}")
    
    elif intencao == "encaminhar_profissional":
        # Ação fixa: envia mensagem para o profissional
        return responder_profissional(numero)
    
    elif intencao == "agendamento":
        # Ação fixa: mensagem pré-definida sobre agendamento
        resposta = "Encaminhei seu contato para o responsável pelo agendamento. Em breve ele entrará em contato."
    
    # -----------------------------
    # Respostas informativas (usa ChatGPT ou TXT)
    # -----------------------------
    elif intencao in ["valor", "horario_funcionamento", "horario_disponibilidade", "servico", "convenio", "agendamento", "geral"]:
        resposta = gerar_resposta_contextual(intencao, texto)
    
    # -----------------------------
    # Caso geral
    # -----------------------------
    else:
        resposta = "Infelizmente não consigo te ajudar com isso, mas posso te informar sobre horários, serviços ou agendamentos. 😊"

    return f"{saudacao}{resposta}" if not contato_existente else resposta

# -------------------------
# Processamento em segundo plano
# -------------------------
def processar_mensagem_em_thread(data):
    try:
        if "entry" in data:
            for entry in data["entry"]:
                for change in entry.get("changes", []):
                    value = change.get("value", {})

                    if "messages" not in value:
                        continue

                    messages = value.get("messages", [])
                    for message in messages:
                        numero = message.get("from", "")
                        texto, tipo = extrair_texto_mensagem(message)
                        print(f"👤 Paciente {numero} enviou ({tipo}): {texto}")

                        if not Mensagem.objects.filter(numero=numero).exists():
                            enviar_alerta_celular(
                                "📞 Novo contato no WhatsApp!",
                                f"Um novo número entrou em contato pela primeira vez:\n\nNúmero: {numero}\nMensagem: {texto}"
                            )

                        # Removida a criação direta para evitar duplicação
                        # Mensagem.objects.create(numero=numero, texto=texto, resposta="")

                        estado, _ = EstadoIA.objects.get_or_create(numero=numero)
                        if not estado.ia_ativa:
                            salvar_mensagem(numero, texto, "Aguardando resposta manual.")
                            continue

                        if tipo in ["audio", "imagem", "sticker", "desconhecido"]:
                            aviso = "Desculpe, consigo compreender apenas mensagens em texto."
                            enviar_com_delay(numero, aviso)
                            salvar_mensagem(numero, texto, aviso)
                            continue

                        if texto.lower() == "profissional":
                            responder_profissional(numero)
                            continue

                        resposta = gerar_resposta(texto, numero)
                        enviar_com_delay(numero, resposta)
                        salvar_mensagem(numero, texto, resposta)

    except Exception as e:
        print("❌ Erro na thread de processamento:", e)

# -------------------------
# Webhook principal
# -------------------------
@csrf_exempt
def webhook(request):
    if request.method == "GET":
        token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")
        mode = request.GET.get("hub.mode")
        if token == VERIFY_TOKEN and mode == "subscribe":
            print("✅ Webhook verificado!")
            return HttpResponse(challenge, status=200)
        return HttpResponse("Erro de verificação", status=403)

    elif request.method == "POST":
        try:
            data = json.loads(request.body.decode("utf-8"))
            print("📩 Mensagem recebida:", json.dumps(data, indent=2))
            response_ok = JsonResponse({"status": "EVENT_RECEIVED"}, status=200)
            threading.Thread(target=processar_mensagem_em_thread, args=(data,)).start()
            return response_ok
        except Exception as e:
            print("Erro no webhook:", e)
            return JsonResponse({"status": "ERROR", "message": str(e)}, status=500)

# -------------------------
# Listar mensagens
# -------------------------
@csrf_exempt
@require_GET
def listar_mensagens(request):
    try:
        msgs = Mensagem.objects.all().order_by('data')
        lista = [{
            "id": m.id,
            "numero": m.numero,
            "texto": m.texto,
            "resposta": m.resposta,
            "ia_ativa": getattr(m, "ia_ativa", True),
            "data": localtime(m.data).isoformat()
        } for m in msgs]
        return JsonResponse(lista, safe=False)
    except Exception as e:
        print("Erro ao listar mensagens:", e)
        return JsonResponse({"status": "ERROR", "message": str(e)}, status=500)

# -------------------------
# Enviar mensagem manualmente
# -------------------------
@csrf_exempt
def enviar_mensagem_manual(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            numero = data.get("numero")
            mensagem = data.get("mensagem")
            if not numero or not mensagem:
                return JsonResponse({"error": "Número e mensagem são obrigatórios"}, status=400)
            enviar_resposta_whatsapp(numero, mensagem)
            salvar_mensagem(numero, "Mensagem enviada manualmente.", mensagem)
            return JsonResponse({"status": "ok"})
        except Exception as e:
            print("Erro ao enviar manual:", e)
            return JsonResponse({"error": str(e)}, status=500)

# -------------------------
# Alternar IA
# -------------------------
@csrf_exempt
def alternar_ia(request):
    data = json.loads(request.body)
    numero = data.get("numero")
    ativo = data.get("ativo")
    estado, _ = EstadoIA.objects.get_or_create(numero=numero)
    estado.ia_ativa = ativo
    estado.save()
    return JsonResponse({"success": True, "numero": numero, "ia_ativa": ativo})

@csrf_exempt
@require_GET
def estado_ia(request):
    numero = request.GET.get("numero")
    if not numero:
        return JsonResponse({"error": "Número é obrigatório"}, status=400)
    estado, _ = EstadoIA.objects.get_or_create(numero=numero)
    return JsonResponse({"numero": numero, "ia_ativa": estado.ia_ativa})
