# n8n's official image is now a hardened Alpine image without a package
# manager (no apk). Build the sqlite3 CLI + its shared libs in a normal
# Alpine stage and copy them into the n8n image.
FROM alpine:3.22 AS sqlite-tools
RUN apk add --no-cache sqlite

FROM docker.n8n.io/n8nio/n8n:latest

USER root
COPY --from=sqlite-tools /usr/bin/sqlite3 /usr/local/bin/sqlite3
COPY --from=sqlite-tools /usr/lib/libreadline.so* /usr/lib/
COPY --from=sqlite-tools /usr/lib/libncursesw.so* /usr/lib/
USER node
