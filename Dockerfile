FROM ros:humble
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-gpiozero \
    python3-lgpio \
    openssh-client \
    python3-opencv \
    ros-humble-cv-bridge \
    espeak \
    alsa-utils \
    ffmpeg \
    libportaudio2 \
    && rm -rf /var/lib/apt/lists/*
RUN pip install anthropic dashscope sounddevice
WORKDIR /ros2_ws
