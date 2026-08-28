FROM jenkins/jenkins:lts-jdk21
USER root
RUN apt-get update && \
    apt-get install -y --no-install-recommends docker.io rsync && \
    rm -rf /var/lib/apt/lists/* && \
    usermod -aG docker jenkins
USER jenkins
