FROM python:3.7-buster

WORKDIR /usr/local/src/botto_app
RUN pip install pipenv
COPY Pipfile Pipfile
RUN pipenv install
COPY . .

CMD [ "pipenv", "run", "python", "-m", "botto" ]