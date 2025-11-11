import pdfkit

html_content = "<h1>Olá, PDF!</h1><p>Gerado com pdfkit + wkhtmltopdf</p>"

# Passando o caminho do executável
config = pdfkit.configuration(wkhtmltopdf=r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe")

pdfkit.from_string(html_content, "saida.pdf", configuration=config)
print("PDF gerado com sucesso!")
