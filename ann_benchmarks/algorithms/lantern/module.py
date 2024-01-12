import subprocess
import sys

import psycopg
import time

from ..base.module import BaseANN


class Lantern(BaseANN):
    def __init__(self, metric, method_param):
        self._metric = metric
        self._m = method_param['M']
        self._ef_construction = method_param['efConstruction']
        self._cur = None

        if metric == "angular":
            self._query = "SELECT id FROM items ORDER BY embedding <=> %s::real[] LIMIT %s"
        elif metric == "euclidean":
            self._query = "SELECT id FROM items ORDER BY embedding <-> %s::real[] LIMIT %s"
        else:
            raise RuntimeError(f"unknown metric {metric}")

    def fit(self, X):
        subprocess.run("service postgresql start", shell=True, check=True, stdout=sys.stdout, stderr=sys.stderr)
        conn = psycopg.connect(user="ann", password="ann", dbname="ann", autocommit=True)
        cur = conn.cursor()
        cur.execute("DROP TABLE IF EXISTS items")
        cur.execute("CREATE TABLE items (id int, embedding real[%d])" % X.shape[1])
        cur.execute("ALTER TABLE items ALTER COLUMN embedding SET STORAGE PLAIN")
        print("copying data...")
        with cur.copy("COPY items (id, embedding) FROM STDIN") as copy:
            for i, embedding in enumerate(X):
                copy.write_row((i, embedding.tolist()))
        print("creating index...")
        if self._metric == "angular":
            build_ix_cmd = "/tmp/lantern/build/lantern-create-index --uri postgresql://ann:ann@127.0.0.1:5432/ann" \
                            " --table items" \
                            " --column embedding" \
                            " -m %d" \
                            " --efc %d" \
                            " -d %d" \
                            " --metric-kind cos" \
                            " --out /tmp/index.usearch" % (self._m, self._ef_construction, X.shape[1])
            subprocess.run(build_ix_cmd, shell=True, check=True, stdout=sys.stdout, stderr=sys.stderr)

            cur.execute(
                "CREATE INDEX ON items USING hnsw (embedding dist_cos_ops) WITH (_experimental_index_path='/tmp/index.usearch')"
            )

            #cur.execute(
            #    "CREATE INDEX ON items USING hnsw (embedding dist_cos_ops) WITH (M = %d, ef_construction = %d, dim = %d)" % (self._m, self._ef_construction, X.shape[1])
            #)
        elif self._metric == "euclidean":
            build_ix_cmd = "/tmp/lantern/build/lantern-create-index --uri postgresql://ann:ann@127.0.0.1:5432/ann" \
                            " --table items" \
                            " --column embedding" \
                            " -m %d" \
                            " --efc %d" \
                            " -d %d" \
                            " --metric-kind l2sq" \
                            " --out /tmp/index.usearch" % (self._m, self._ef_construction, X.shape[1])
            subprocess.run(build_ix_cmd, shell=True, check=True, stdout=sys.stdout, stderr=sys.stderr)
            cur.execute(
                "CREATE INDEX ON items USING hnsw (embedding dist_l2sq_ops) WITH (_experimental_index_path='/tmp/index.usearch')"
            )

            #cur.execute(
            #    "CREATE INDEX ON items USING hnsw (embedding dist_l2sq_ops) WITH (M = %d, ef_construction = %d, dim = %d)" % (self._m, self._ef_construction, X.shape[1])
            #)
        else:
            raise RuntimeError(f"unknown metric {self._metric}")
        print("done!")
        self._cur = cur

    def set_query_arguments(self, ef_search):
        self._ef_search = ef_search
        self._cur.execute("SET enable_seqscan = false")
        self._cur.execute("SET hnsw.ef = %d" % ef_search)

    def query(self, v, n):
        self._cur.execute(self._query, (v.tolist(), n), binary=True, prepare=True)
        return [id for id, in self._cur.fetchall()]

    def get_memory_usage(self):
        if self._cur is None:
            return 0
        self._cur.execute("SELECT pg_relation_size('items_embedding_idx')")
        return self._cur.fetchone()[0] / 1024

    def __str__(self):
        return f"Lantern(m={self._m}, ef_construction={self._ef_construction}, ef_search={self._ef_search})"
