FROM ros:humble
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-gpiozero \
    python3-lgpio \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /ros2_ws
