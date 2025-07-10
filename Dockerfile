#FROM python:3.7
FROM simonsobs/ocs:v0.10.3

WORKDIR /primecam_readout

COPY requirements.txt .
COPY __init__.py /

RUN pip install -r requirements.txt

COPY ./src .

RUN mkdir -p tmp

# CMD ["python", "./primecam_readout/queen_agent.py"]

ENTRYPOINT ["dumb-init", "ocs-agent-cli"]
CMD ["--agent", "queen_agent.py", "--entrypoint", "main"]