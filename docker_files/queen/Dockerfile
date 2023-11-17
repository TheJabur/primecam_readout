#FROM python:3.7
FROM simonsobs/ocs:v0.10.3

WORKDIR /primecam_readout

COPY requirements.txt .
COPY ./primecam_readout ./primecam_readout

RUN pip install -r requirements.txt
CMD ["python", "./primecam_readout/queen_agent.py"]
