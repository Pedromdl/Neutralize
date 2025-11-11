from google.ads.googleads.client import GoogleAdsClient

client = GoogleAdsClient.load_from_storage("google-ads.yaml")
customer_service = client.get_service("CustomerService")

parent_customer_id = "4123714448"  # MCC que vai criar a test account

customer = client.get_type("Customer")
customer.descriptive_name = "Conta de Teste API"
customer.currency_code = "BRL"
customer.time_zone = "America/Sao_Paulo"
customer.tracking_url_template = ""

# Cria a test account
response = customer_service.create_customer_client(
    customer_id=parent_customer_id,
    customer_client=customer
)

print("Test Account criada, Customer ID:", response.resource_name)
