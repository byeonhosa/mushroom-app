# Backup sidecar: the same PostgreSQL major version as the `db` service, so
# pg_dump and pg_restore always match the server.
FROM postgres:16

COPY ops/backup/backup.sh /usr/local/bin/backup
RUN chmod 755 /usr/local/bin/backup

ENTRYPOINT ["/usr/local/bin/backup"]
CMD ["loop"]
