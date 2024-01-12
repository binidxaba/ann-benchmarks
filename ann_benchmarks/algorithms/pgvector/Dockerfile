FROM ann-benchmarks

# https://github.com/pgvector/pgvector/blob/master/Dockerfile

RUN git clone https://github.com/pgvector/pgvector /tmp/pgvector && \
  cd /tmp/pgvector && \
  git checkout tags/v0.5.1 -b v0.5.1

RUN apt-get -y install lsb-release wget curl
RUN sh -c 'curl -fSsL https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor | tee /usr/share/keyrings/postgresql.gpg > /dev/null'
RUN sh -c 'echo deb [arch=amd64,arm64,ppc64el signed-by=/usr/share/keyrings/postgresql.gpg] http://apt.postgresql.org/pub/repos/apt/ $(lsb_release -cs)-pgdg main | tee /etc/apt/sources.list.d/postgresql.list'

RUN DEBIAN_FRONTEND=noninteractive apt-get -y install tzdata
RUN apt-get update && apt-get install -y --no-install-recommends build-essential postgresql-15 postgresql-server-dev-15
RUN sh -c 'echo "local all all trust" > /etc/postgresql/15/main/pg_hba.conf'
RUN cd /tmp/pgvector && \
	make clean && \
	make OPTFLAGS="-march=native -mprefer-vector-width=512" && \
	make install

USER postgres
RUN service postgresql start && \
    psql -c "CREATE USER ann WITH ENCRYPTED PASSWORD 'ann'" && \
    psql -c "CREATE DATABASE ann" && \
    psql -c "GRANT ALL PRIVILEGES ON DATABASE ann TO ann" && \
    psql -d ann -c "GRANT ALL ON SCHEMA public TO ann" && \
    psql -d ann -c "CREATE EXTENSION vector" && \
    psql -c "ALTER USER ann SET maintenance_work_mem = '5GB'" && \
    psql -c "ALTER USER ann SET work_mem = '2GB'" && \
    psql -c "ALTER SYSTEM SET shared_buffers = '12GB'"
USER root

RUN pip install psycopg[binary] pgvector
