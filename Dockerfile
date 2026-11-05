FROM docker.iscinternal.com/docker-intersystems/intersystems/iris-community:2027.1.0AI.109.0

USER root

COPY src/python/langchain_intersystems-0.0.1-py3-none-any.whl /tmp/langchain_intersystems-0.0.1-py3-none-any.whl
COPY requirements.txt /tmp/requirements.txt

RUN mkdir -p /opt/irisapp/python-packages \
    && python3 -m pip install \
        --target /opt/irisapp/python-packages \
        /usr/irissys/dev/python/intersystems_irispython-5.4.0-cp39.cp310.cp311.cp312.cp313.cp314-cp39.cp310.cp311.cp312.cp313.cp314-manylinux2014_x86_64.manylinux_2_17_x86_64.whl \
        /tmp/langchain_intersystems-0.0.1-py3-none-any.whl \
        -r /tmp/requirements.txt \
    && rm -f \
        /tmp/langchain_intersystems-0.0.1-py3-none-any.whl \
        /tmp/requirements.txt

ENV PYTHONPATH="/opt/irisapp/python-packages:/opt/irisapp/src/python"

USER irisowner