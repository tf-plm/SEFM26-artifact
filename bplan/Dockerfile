FROM ubuntu:jammy

WORKDIR /bplan

RUN apt-get update && \
    apt-get install -y python3 wget unzip parallel time

COPY . .

RUN ./scripts/install-exp.sh

ENTRYPOINT ["/bin/bash"]

