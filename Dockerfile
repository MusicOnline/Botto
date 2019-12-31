FROM python:3.8.1-buster

WORKDIR /usr/local/src/botto_app
COPY . .
RUN pip install -r requirements.txt

CMD [ "python", "-m", "botto" ]