FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb

RUN pip install --no-cache-dir pytest==8.4.1 pytest-json-ctrf==0.3.5

WORKDIR /app

COPY data/descriptor_parser.py /app/descriptor_parser.py
COPY data/address_translator.py /app/address_translator.py
COPY data/burst_calculator.py /app/burst_calculator.py
COPY data/chain_linker.py /app/chain_linker.py
COPY data/alignment_engine.py /app/alignment_engine.py
COPY data/scatter_gather_validator.py /app/scatter_gather_validator.py
COPY data/pipeline.py /app/pipeline.py
COPY data/dma_config.json /app/dma_config.json
