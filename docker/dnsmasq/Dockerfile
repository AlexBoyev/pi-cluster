FROM alpine:latest
RUN apk add --no-cache dnsmasq
ENTRYPOINT ["dnsmasq", "-k", "--log-facility=-"]
