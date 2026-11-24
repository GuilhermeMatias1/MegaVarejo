FROM python:3.11-slim

WORKDIR /app

# Instalar dependências necessárias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código-fonte da aplicação
COPY . .

# Porta padrão definida em ambiente de nuvem
ENV PORT=5000
EXPOSE 5000

# Inicialização com Gunicorn em produção
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "4", "--timeout", "120", "app:app"]
