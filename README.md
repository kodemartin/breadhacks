# Bread-hacks

Create, handle, and store bread-recipes.

# Development environment

## System-requirements

* `docker-ce`
* `docker-compose`

## Set-up

* `docker-compose up`
* Apply migrations

        docker-compose run web python manage.py migrate

  or

        docker exec django-project python manage.py migrate

