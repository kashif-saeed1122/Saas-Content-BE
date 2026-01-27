# SWITCH to Python 3.12 (Amazon Linux 2023) to get a newer GLIBC for Playwright
FROM public.ecr.aws/lambda/python:3.12

# Define function directory
ARG FUNCTION_DIR="/function"

# Set Cargo network retries
ENV CARGO_NET_RETRY=10

# Install system dependencies
# Amazon Linux 2023 uses 'dnf'.
# REMOVED 'curl' from install list because 'curl-minimal' is already installed in the base image
# and installing 'curl' causes a conflict.
RUN dnf install -y \
    nss nspr atk cups-libs dbus-glib libXcomposite libXcursor libXdamage libXext libXi libXrender libXtst pango at-spi2-atk libXrandr mesa-libgbm alsa-lib \
    tar gzip unzip \
    gcc gcc-c++ make \
    rust cargo openssl-devel \
    && dnf clean all

# Install AWS Lambda Runtime Interface Emulator (RIE)
ADD https://github.com/aws/aws-lambda-runtime-interface-emulator/releases/latest/download/aws-lambda-rie /usr/bin/aws-lambda-rie
RUN chmod 755 /usr/bin/aws-lambda-rie

# Create function directory
WORKDIR ${FUNCTION_DIR}

COPY requirements.txt .

# Upgrade pip
RUN pip install --upgrade pip setuptools wheel

# Install tiktoken as binary to avoid Rust compilation issues
RUN pip install tiktoken --target ${FUNCTION_DIR} --only-binary=:all:

# Install remaining dependencies
RUN pip install -r requirements.txt --target ${FUNCTION_DIR}

# --- MANUAL BROWSER DOWNLOAD FIX ---
# Set a fixed location for browsers
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright
RUN mkdir -p /ms-playwright

# 1. Download Chromium Build 1148 (matches Playwright 1.49.0) using CURL (more reliable than internal downloader)
# 2. Unzip specifically to 'chromium-1148' folder
RUN curl -Lo /tmp/chromium.zip https://playwright.azureedge.net/builds/chromium/1148/chromium-linux.zip \
    && unzip /tmp/chromium.zip -d /ms-playwright/chromium-1148 \
    && rm /tmp/chromium.zip

# Register the browser. 
# Since files are already there, this command should verify checksums and finish instantly without downloading.
ENV PYTHONPATH=${FUNCTION_DIR}
RUN python -m playwright install chromium

# Copy application code
COPY . ${FUNCTION_DIR}

CMD [ "graph.handler" ]