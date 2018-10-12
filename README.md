# Bread-hacks

Create, handle, and store bread-recipes.

# Development environment

## System-requirements

* `docker-ce`
* `docker-compose`
* `python3`

## Set-up

* `docker-compose up`

    The application requires that the `db` service is up and awaiting
    for connections. It might be the case that the `web` service
    starts before the `mysql` server is initialized. This will
    result in exiting the service with errors. This can be handled
    more thoroughly as suggested [here](https://hub.docker.com/_/mysql/)
    and already implemented [here](https://github.com/docker-library/docs/blob/9660a0cccb87d8db842f33bc0578d769caaf3ba9/bonita/stack.yml#L28-L44).

    For the moment, a safe initialization could be attained
    through two commands in sequence:

    1. `docker-compose up [-d] db`, followed by
    2. `docker-compose up [-d] web`.

* Apply migrations

        docker-compose run web python manage.py migrate

  or

        docker exec django-project python manage.py migrate

    Migrations can be rolled back through

        docker exec django-project python manage.py migrate [<app-name>] zero

    Under linux OS, after migrations are applied run

        sudo chown -R $USER:$USER .

    so that ownership of the files is assigned to the current user.


* Grant the user `baker` the necessary permissions to create the test-database

  1. Login:

        docker-exec -it docker-mysql mysql -u<username> -p<password> breadhacks

  2. Grant permissions:

        mysql > GRANT ALL ON *.* to 'baker'@'%';

* Run tests:

        docker-exec django-project python manage.py test
