#FROM python:3.7
FROM simonsobs/ocs:v0.10.3

WORKDIR /primecam_readout

COPY requirements.txt .
COPY ./src ./src
COPY ./cfg ./cfg

RUN pip install -r requirements.txt

# CMD ["python", "./primecam_readout/queen_agent.py"]

ENTRYPOINT ["dumb-init", "ocs-agent-cli"]
CMD ["--agent", "/src/queen_agent.py", "--entrypoint", "main"]