FROM spark:3.5.6 AS spark-image

# base image for runner
FROM yusufali/runner

COPY --from=spark-image /opt/spark /opt/spark
COPY --from=spark-image /opt/java /opt/java

ENV SPARK_HOME /opt/spark
ENV JAVA_HOME /opt/java/openjdk