start:
	python manage.py runserver

migrate:
	python manage.py makemigrations
	python manage.py migrate

activate:
	source ./venv/bin/activate

setup: requirements.txt
    pip install -r requirements.txt

docker-build:
	docker build .

prod:
	docker-compose up

test:
	python3 manage.py test

user:
	python3 manage.py createsuperuser
