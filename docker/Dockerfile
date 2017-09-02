FROM python:3-stretch

COPY pip_requirements /tmp/pip_requirements

RUN pip install --no-cache-dir -Ur /tmp/pip_requirements

RUN mkdir /opt/frisbeer-bot

COPY *.py /opt/frisbeer-bot/

WORKDIR /opt/frisbeer-bot

ENTRYPOINT ["python3", "main.py"]
