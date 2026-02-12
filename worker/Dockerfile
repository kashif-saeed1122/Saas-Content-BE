FROM public.ecr.aws/lambda/python:3.12

ARG FUNCTION_DIR="/function"

ENV CARGO_NET_RETRY=10


RUN dnf install -y \
    nss nspr atk cups-libs dbus-glib libXcomposite libXcursor libXdamage libXext libXi libXrender libXtst pango at-spi2-atk libXrandr mesa-libgbm alsa-lib \
    tar gzip unzip \
    gcc gcc-c++ make \
    rust cargo openssl-devel \
    && dnf clean all

ADD https://github.com/aws/aws-lambda-runtime-interface-emulator/releases/latest/download/aws-lambda-rie /usr/bin/aws-lambda-rie
RUN chmod 755 /usr/bin/aws-lambda-rie

# Create function directory
WORKDIR ${FUNCTION_DIR}

COPY requirements.txt .

# Upgrade pip
RUN pip install --upgrade pip setuptools wheel

RUN pip install tiktoken --target ${FUNCTION_DIR} --only-binary=:all:

RUN pip install -r requirements.txt --target ${FUNCTION_DIR}

ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN mkdir -p /ms-playwright

RUN curl -Lo /tmp/chromium.zip https://playwright.azureedge.net/builds/chromium/1148/chromium-linux.zip \
    && unzip /tmp/chromium.zip -d /ms-playwright/chromium-1148 \
    && rm /tmp/chromium.zip

ENV PYTHONPATH=${FUNCTION_DIR}
RUN python -m playwright install chromium

# Copy application code
COPY . ${FUNCTION_DIR}

CMD [ "graph.handler" ]