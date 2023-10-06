FROM edoburu/pgbouncer:1.18.0

# Don't copy pgbouncer.ini, as then it won't be auto-created by entrypoint.
# Settings have to be configured through env vars.
COPY userlist.txt /etc/pgbouncer/
# Change UID of postgres user to 100000
USER root
RUN deluser postgres && \
    addgroup -g 100000 -S postgres && \
    adduser -u 100000 -S -D -H -h /var/lib/postgresql -g "Postgres user" -s /bin/bash -G postgres postgres && \
    chown -R postgres /var/run/pgbouncer /etc/pgbouncer

# The relationship between users:
# 1. admin is for logging to pgbouncer admin. First shell to pgbouncer container, and:
#    PGPASSWORD=pgb-NgbMrknv5rsp9E2b psql -h localhost -p $LISTEN_PORT -U admin -d pgbouncer
#    Then you can do "show stats;", "show clients;" and other commands.
# 2. postgres is container user for pgbouncer to manage files and run process.

USER postgres
