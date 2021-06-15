FROM apache/nifi

# Install python3
USER root
RUN apt-get update -y
RUN apt-get install -y python3

# Create log folder and copy script
RUN mkdir -p /var/log/jsonFormatter
RUN chown nifi:nifi /var/log/jsonFormatter
COPY --chown=nifi:nifi jsonFormatter.py /home/nifi/
