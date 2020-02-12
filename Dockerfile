FROM python:3.7-buster

WORKDIR /usr/local/src/botto_app
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
COPY . .

CMD [ "python", "-m", "botto" ]