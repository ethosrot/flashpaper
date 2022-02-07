FROM python:3.9.5

WORKDIR /usr/src/app

ENV PYTHONUNBUFFERED 1
ENV FLASK_ENV production

COPY requirements.txt /usr/src/app/requirements.txt
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY cli.py /usr/src/app/cli.py
COPY config.py /usr/src/app/config.py
COPY wsgi.py /usr/src/app/wsgi.py

COPY application /usr/src/app/application

RUN mkdir /usr/src/app/data
RUN mkdir /usr/src/app/avatars

EXPOSE 5000
ENTRYPOINT ["gunicorn", "--bind", "0.0.0.0:5000", "--access-logfile", "-", "wsgi:app"]
