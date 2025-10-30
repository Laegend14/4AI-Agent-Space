# read the doc: https://huggingface.co/docs/hub/spaces-sdks-docker
# you will also find guides on how best to write your Dockerfile

FROM us-docker.pkg.dev/colab-images/public/runtime:latest

RUN apt update; apt install libsndfile1-dev make autoconf automake libtool gcc pkg-config -y python3-dev

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Set up a new user named "user" with user ID 1000
RUN useradd -m -u 1000 user

# Switch to the "user" user
USER user

# Set home to the user's home directory
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# Set the working directory to the user's home directory
WORKDIR $HOME/app

# Copy the current directory contents into the container at $HOME/app setting the owner to the user
COPY --chown=user . $HOME/app

RUN bash ./build_ext.sh
RUN bash ./install_espeak_ng.sh
EXPOSE 7860
ENV GRADIO_SERVER_NAME="0.0.0.0"

ENTRYPOINT ["python", "app.py"]