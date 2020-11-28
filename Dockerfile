FROM python:3.6.12-alpine3.12
WORKDIR /usr/src/ics

# Copy the actual folder and install dependencies

COPY . ./
RUN pip3 install -r requirements.txt

# Mount the config volume

RUN mkdir /usr/src/ics/app/config
VOLUME [ "/usr/src/ics/app/config" ]

EXPOSE 8088

CMD ["python3", "./app/server.py"]

