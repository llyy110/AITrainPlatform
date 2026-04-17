FROM openjdk:8-jdk
ENV HADOOP_VERSION=3.4.2
ENV HADOOP_HOME=/usr/local/hadoop
RUN apt-get update && apt-get install -y wget ssh rsync
RUN wget https://mirrors.aliyun.com/apache/hadoop/common/hadoop-${HADOOP_VERSION}/hadoop-${HADOOP_VERSION}.tar.gz \
    && tar -xzf hadoop-${HADOOP_VERSION}.tar.gz \
    && mv hadoop-${HADOOP_VERSION} ${HADOOP_HOME} \
    && rm hadoop-${HADOOP_VERSION}.tar.gz
ENV PATH=$PATH:$HADOOP_HOME/bin:$HADOOP_HOME/sbin
RUN ssh-keygen -t rsa -P '' -f ~/.ssh/id_rsa \
    && cat ~/.ssh/id_rsa.pub >> ~/.ssh/authorized_keys
COPY core-site.xml hdfs-site.xml ${HADOOP_HOME}/etc/hadoop/
EXPOSE 9870 8088 9000
CMD ["bash", "-c", "service ssh start && bash"]
