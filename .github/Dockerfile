FROM docker.io/alpine:3.14
RUN echo "hello world"
ENTRYPOINT [ "sh", "-c", "echo -n 'Machine: ' && uname -m && echo -n 'Bits: ' && getconf LONG_BIT && echo 'goodbye world'" ]
