FROM python:3.11.6-slim-bullseye

WORKDIR /app

COPY hasker/requirements.txt .

RUN pip install 'gunicorn==21.2.0'

RUN pip install -r requirements.txt

COPY hasker .

COPY prestart.sh .

RUN chmod +x ./prestart.sh
ENTRYPOINT ["./prestart.sh"]

CMD gunicorn hasker.wsgi:application --bind 0.0.0.0:80
