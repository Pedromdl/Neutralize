import os
import django
from datetime import date

# --- Carregar o Django ---
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.settings")  # ajuste se necessário
django.setup()

# --- Imports após django.setup() ---
from api.models import Usuário
from accounts.models import Clinica


# Selecionar a clínica de ID 3
clinica_demo = Clinica.objects.get(id=3)

usuarios_demo = [
    {
        "nome": "Ana Beatriz Souza",
        "cpf": "123.456.789-01",
        "email": "ana.souza@example.com",
        "telefone": "(11) 91234-5678",
        "cep": "01001-000",
        "rua": "Rua das Flores",
        "numero": "123",
        "bairro": "Centro",
        "cidade": "São Paulo",
        "estado": "SP",
        "complemento": "Apto 101",
        "data_de_nascimento": date(1985, 5, 21),
    },
    {
        "nome": "Bruno Carvalho",
        "cpf": "234.567.890-12",
        "email": "bruno.carvalho@example.com",
        "telefone": "(21) 98765-4321",
        "cep": "20010-000",
        "rua": "Avenida Atlântica",
        "numero": "456",
        "bairro": "Copacabana",
        "cidade": "Rio de Janeiro",
        "estado": "RJ",
        "complemento": "Cobertura",
        "data_de_nascimento": date(1990, 8, 15),
    },
    {
        "nome": "Carla Mendes",
        "cpf": "345.678.901-23",
        "email": "carla.mendes@example.com",
        "telefone": "(31) 99876-5432",
        "cep": "30110-000",
        "rua": "Rua da Bahia",
        "numero": "789",
        "bairro": "Savassi",
        "cidade": "Belo Horizonte",
        "estado": "MG",
        "complemento": "",
        "data_de_nascimento": date(1978, 3, 10),
    },
    {
        "nome": "Diego Lima",
        "cpf": "456.789.012-34",
        "email": "diego.lima@example.com",
        "telefone": "(41) 91234-5678",
        "cep": "80010-000",
        "rua": "Rua XV de Novembro",
        "numero": "321",
        "bairro": "Centro",
        "cidade": "Curitiba",
        "estado": "PR",
        "complemento": "",
        "data_de_nascimento": date(1988, 12, 5),
    },
    {
        "nome": "Eduarda Ribeiro",
        "cpf": "567.890.123-45",
        "email": "eduarda.ribeiro@example.com",
        "telefone": "(51) 98765-1234",
        "cep": "90010-000",
        "rua": "Avenida Borges de Medeiros",
        "numero": "654",
        "bairro": "Centro Histórico",
        "cidade": "Porto Alegre",
        "estado": "RS",
        "complemento": "Sala 2",
        "data_de_nascimento": date(1992, 7, 30),
    },
    {
        "nome": "Fábio Santos",
        "cpf": "678.901.234-56",
        "email": "fabio.santos@example.com",
        "telefone": "(71) 91234-8765",
        "cep": "40010-000",
        "rua": "Rua Chile",
        "numero": "987",
        "bairro": "Centro",
        "cidade": "Salvador",
        "estado": "BA",
        "complemento": "",
        "data_de_nascimento": date(1980, 1, 20),
    },
    {
        "nome": "Gabriela Torres",
        "cpf": "789.012.345-67",
        "email": "gabriela.torres@example.com",
        "telefone": "(61) 99876-4321",
        "cep": "70040-000",
        "rua": "Esplanada dos Ministérios",
        "numero": "100",
        "bairro": "Zona Cívico-Administrativa",
        "cidade": "Brasília",
        "estado": "DF",
        "complemento": "",
        "data_de_nascimento": date(1995, 9, 12),
    },
    {
        "nome": "Hugo Oliveira",
        "cpf": "890.123.456-78",
        "email": "hugo.oliveira@example.com",
        "telefone": "(85) 91234-5678",
        "cep": "60010-000",
        "rua": "Rua Barão do Rio Branco",
        "numero": "222",
        "bairro": "Centro",
        "cidade": "Fortaleza",
        "estado": "CE",
        "complemento": "Apto 303",
        "data_de_nascimento": date(1983, 11, 2),
    },
    {
        "nome": "Isabela Martins",
        "cpf": "901.234.567-89",
        "email": "isabela.martins@example.com",
        "telefone": "(27) 99876-5432",
        "cep": "29010-000",
        "rua": "Avenida Jerônimo Monteiro",
        "numero": "555",
        "bairro": "Centro",
        "cidade": "Vitória",
        "estado": "ES",
        "complemento": "",
        "data_de_nascimento": date(1991, 4, 18),
    },
    {
        "nome": "João Pedro Almeida",
        "cpf": "012.345.678-90",
        "email": "joao.almeida@example.com",
        "telefone": "(11) 97654-3210",
        "cep": "01310-000",
        "rua": "Avenida Paulista",
        "numero": "1000",
        "bairro": "Bela Vista",
        "cidade": "São Paulo",
        "estado": "SP",
        "complemento": "Conjunto 101",
        "data_de_nascimento": date(1987, 6, 25),
    },
]

# Criando os usuários
for u in usuarios_demo:
    usuario = Usuário.objects.create(
        nome=u["nome"],
        cpf=u["cpf"],
        email=u["email"],
        telefone=u["telefone"],
        cep=u["cep"],
        rua=u["rua"],
        numero=u["numero"],
        bairro=u["bairro"],
        cidade=u["cidade"],
        estado=u["estado"],
        complemento=u["complemento"],
        data_de_nascimento=u["data_de_nascimento"],
        clinica=clinica_demo
    )

    print(f"Usuário criado: {usuario.nome}")

print("\n🎉 Finalizado! 10 usuários fictícios foram criados com sucesso.\n")
