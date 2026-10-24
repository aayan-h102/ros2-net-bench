FROM ros:jazzy-ros-base

# iproute2 provides `tc` (netem link simulation).
# rmw_zenoh lets the same benchmark run over Zenoh instead of DDS.
RUN apt-get update \
    && apt-get install -y --no-install-recommends iproute2 ros-jazzy-rmw-zenoh-cpp \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /ws
COPY net_bench/ src/net_bench/
RUN . /opt/ros/jazzy/setup.sh \
    && colcon build --packages-select net_bench \
    && rm -rf build log

COPY config/fastdds_udp.xml /config/fastdds_udp.xml
COPY scripts/entrypoint.sh scripts/netem.sh /scripts/
RUN chmod +x /scripts/*.sh

ENV FASTRTPS_DEFAULT_PROFILES_FILE=/config/fastdds_udp.xml \
    FASTDDS_DEFAULT_PROFILES_FILE=/config/fastdds_udp.xml \
    RMW_IMPLEMENTATION=rmw_fastrtps_cpp \
    ROS_DOMAIN_ID=42 \
    PYTHONUNBUFFERED=1

ENTRYPOINT ["/scripts/entrypoint.sh"]
CMD ["python3", "-m", "net_bench.echo_node"]
