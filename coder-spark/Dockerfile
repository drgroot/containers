FROM rclone/rclone AS rclone
FROM spark:3.5.6 AS spark

# base image for coder
FROM codercom/code-server

USER root

COPY --from=rclone /usr/local/bin/rclone /bin/rclone
COPY --from=spark /opt/spark /opt/spark
COPY --from=spark /opt/java /opt/java

ENV DEBIAN_FRONTEND=noninteractive
ENV PYENV_ROOT="/opt/pyenv"
ENV JAVA_HOME=/opt/java/openjdk
ENV SPARK_HOME=/opt/spark
ENV NVM_DIR=/usr/local/nvm
ENV PATH=$PYENV_ROOT/bin:$SPARK_HOME/bin:$JAVA_HOME/bin:$PATH

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git \
        git-lfs \
        tmux \
        curl \
        wget \
        build-essential \
        vim \
        make \
        libssl-dev \
        zlib1g-dev \
        libbz2-dev \
        libreadline-dev \
        libsqlite3-dev \
        libncursesw5-dev \
        xz-utils \
        tk-dev \
        libxml2-dev \
        libxmlsec1-dev \
        libffi-dev \
        liblzma-dev \
        gnupg \
        tmux

RUN git lfs install --system

# setup for google-chrome
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub \
    | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/google-chrome.gpg] https://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# RUN apt-get update && apt-get install -y --no-install-recommends \
#    ca-certificates \
#    gnupg \
#    wget \
#    && rm -rf /var/lib/apt/lists/*

# Add NVIDIA package repositories (for CUDA 12.1.1)
# RUN wget -q https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb && \
#     dpkg -i cuda-keyring_1.1-1_all.deb && \
#     rm -f cuda-keyring_1.1-1_all.deb && \
#     apt-get update

# # Install the CUDA **runtime** for 12.1 (no compiler)
# RUN apt-get install -y --no-install-recommends cuda-runtime-12-8 && \
#     rm -rf /var/lib/apt/lists/*

# install kubectl
RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" && \
    chmod +x kubectl && \
    mv kubectl /usr/bin/.

# install docker
RUN curl -fsSL https://get.docker.com -o get-docker.sh && \
    sudo sh ./get-docker.sh && \
    rm get-docker.sh

# install python
RUN git clone https://github.com/pyenv/pyenv.git /opt/pyenv
RUN eval "$(pyenv init -)" && \
    pyenv install 3.12 && \
    echo 'export PATH="$PYENV_ROOT/bin:$PATH"' > /etc/profile.d/pyenv.sh && \
    echo '' >> /etc/profile.d/pyenv.sh && \
    echo 'eval "$(pyenv init -)"' >> /etc/profile.d/pyenv.sh

# install nodejs
RUN mkdir -p $NVM_DIR && \
    curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.4/install.sh | bash && \
    echo 'export NVM_DIR="/usr/local/nvm"' >> /etc/profile.d/nvm.sh && \
    echo '[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"' >> /etc/profile.d/nvm.sh && \
    [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh" && \
    nvm install --lts && \
    npm install -g @openai/codex

# setup main bashrc
RUN echo 'export PATH=$PYENV_ROOT/bin:$SPARK_HOME/bin:$JAVA_HOME/bin:$PATH:$HOME/bin:/common-bin/bin' >> /etc/profile.d/spark.sh

RUN mkdir -p /opt/spark/conf
RUN chown -R coder /opt/pyenv /opt/spark/conf /usr/local/nvm

RUN apt-get remove -y nano*

USER coder

ENV PYENV_ROOT="/opt/pyenv"
ENV JAVA_HOME=/opt/java/openjdk
ENV SPARK_HOME=/opt/spark
ENV CUDA_HOME=/usr/local/cuda-12.8
ENV PATH=${CUDA_HOME}/bin:$PYENV_ROOT/bin:$SPARK_HOME/bin:$JAVA_HOME/bin:$PATH
ENV LD_LIBRARY_PATH="${CUDA_HOME}/lib64"
