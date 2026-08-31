FROM postgres:17-alpine AS builder

# 1. On installe uniquement les outils de base (plus besoin de se battre avec clang ou llvm)
RUN apk add --no-cache git build-base

# 2. Récupération du code source
WORKDIR /tmp
RUN git clone --branch v0.8.0 https://github.com/pgvector/pgvector.git
WORKDIR /tmp/pgvector

# 3. Compilation standard en désactivant explicitement LLVM
RUN make with_llvm=no && make install with_llvm=no

# 4. Image finale ultra-légère
FROM postgres:17-alpine
COPY --from=builder /usr/local/lib/postgresql/vector.so /usr/local/lib/postgresql/vector.so
COPY --from=builder /usr/local/share/postgresql/extension/vector* /usr/local/share/postgresql/extension/

COPY ./db-init/ /docker-entrypoint-initdb.d/