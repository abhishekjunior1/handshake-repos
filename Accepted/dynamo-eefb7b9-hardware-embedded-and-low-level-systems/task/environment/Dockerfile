FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

RUN pip install --no-cache-dir pytest==8.4.1 pytest-json-ctrf==0.3.5

COPY data/pipeline.py /app/pipeline.py
COPY data/clock_config.py /app/clock_config.py
COPY data/bus_arbiter.py /app/bus_arbiter.py
COPY data/register_programmer.py /app/register_programmer.py
COPY data/device_enumerator.py /app/device_enumerator.py
COPY data/power_sequencer.py /app/power_sequencer.py
COPY data/init_reporter.py /app/init_reporter.py
COPY data/input.json /app/input.json

WORKDIR /app
