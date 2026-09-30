FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8981
CMD ["python", "-m", "streamlit", "run", "app.py", "--server.port=8981", "--server.address=0.0.0.0"]
