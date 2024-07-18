FROM python:3.9-slim

WORKDIR /app

COPY . /app

RUN pip install flask

EXPOSE 5000

CMD ["python", "app.py"]

# docker build -t python-flask-app .
# docker run -d -p 5000:5000 python-flask-app