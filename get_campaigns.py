from google.ads.googleads.client import GoogleAdsClient

# Carrega as credenciais do arquivo google-ads.yaml
client = GoogleAdsClient.load_from_storage("google-ads.yaml")

# Cria o serviço de consulta
ga_service = client.get_service("GoogleAdsService")

# Substitua pelo seu ID de conta (sem hífen)
CUSTOMER_ID = "3442835619"

# Consulta básica de campanhas
query = """
    SELECT
      campaign.id,
      campaign.name,
      campaign.status,
      metrics.impressions,
      metrics.clicks,
      metrics.cost_micros
    FROM campaign
    ORDER BY campaign.id
    LIMIT 10
"""

# Executa a busca
response = ga_service.search(customer_id=CUSTOMER_ID, query=query)

# Exibe os resultados
for row in response:
    cost = row.metrics.cost_micros / 1_000_000  # converte micros para unidades
    print(f"Campanha: {row.campaign.name}")
    print(f"  ID: {row.campaign.id}")
    print(f"  Status: {row.campaign.status.name}")
    print(f"  Impressões: {row.metrics.impressions}")
    print(f"  Cliques: {row.metrics.clicks}")
    print(f"  Custo (R$): {cost:.2f}")
    print("-" * 40)
