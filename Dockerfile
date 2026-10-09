FROM python:3.12-slim
WORKDIR /app
ARG BWS_VERSION=2.1.0
ARG BWS_SHA256=ba8233c3a4aee5d43e3c73bbd04d99e9bc5aba13bbbfd06d89b073abe732b860
RUN apt-get update && apt-get install -y --no-install-recommends curl unzip ca-certificates \
 && curl -sSL -o /tmp/bws.zip https://github.com/bitwarden/sdk-sm/releases/download/bws-v${BWS_VERSION}/bws-x86_64-unknown-linux-gnu-${BWS_VERSION}.zip \
 && echo "${BWS_SHA256}  /tmp/bws.zip" | sha256sum -c - \
 && unzip -q /tmp/bws.zip -d /usr/local/bin && chmod +x /usr/local/bin/bws && rm /tmp/bws.zip \
 && apt-get purge -y curl unzip && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY grip ./grip
COPY start.sh .
CMD ["sh", "start.sh"]
