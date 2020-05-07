from ubuntu:bionic

RUN apt-get update -qq && apt-get install -y \
    python3 \
    python3-pip \
    python3-yaml \
    git

RUN pip3 install discord.py==1.3.3 schedule py-spy

COPY bot /bot

ENV PYTHONIOENCODING UTF-8
WORKDIR /bot
ENTRYPOINT python3 marvin.py
