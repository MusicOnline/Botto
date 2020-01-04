FROM python:3.8.1-buster

WORKDIR /usr/local/src/botto_app
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
COPY . .

CMD [ "python", "-m", "botto" ]