# AWS vector store provisioned

2026-07-13 20:05

Previous: [2026-07-13-1949-all-thirteen-items-built.md](entries/2026-07-13-1949-all-thirteen-items-built.md)

Sandip approved the cost, so the RAG vector store is now real AWS, not the local
fallback. Item 2 is fully done, both the code and the infrastructure.

What went up: a CloudFormation stack, sentinel-vectordb, with RDS PostgreSQL 16 on
a db.t4g.micro, pgvector enabled. The master password is generated and managed by
RDS in Secrets Manager, so I never handled it in plaintext. The security group
allows only my ingest IP and the Elastic Beanstalk app instance. Embeddings run
through Bedrock Titan Embed Text v2 at 1024 dimensions.

Ingested the fifteen corpus chunks and verified dense retrieval end to end. The
fairness query returns the four-fifths rule as the top hit with a cosine score
around 0.39, then Reg B. The app's retrieve() reports backend pgvector when the
env is set. This is the same corpus and the same citations as the local store,
now served by dense embeddings from a real AWS vector database.

The design keeps the demo safe. The default is still the free local store, so the
public link needs no AWS and nothing breaks if the DB is down. pgvector activates
only when SENTINEL_VECTOR_STORE=pgvector and the connection env is set, and the
password is read from Secrets Manager at connect time, never stored in config.
psycopg and boto3 are an optional extra, kept out of the deployed app.

Cost is about thirteen to fifteen dollars a month. Teardown is one command:
delete the sentinel-vectordb stack.

What is left is one deliberate step: deploy. The live app at sentinel.sandip.dev
is still the pre-platform version. Wiring the deployed EB app to the pgvector
store would also need the env vars, the pgvector extra, and IAM permission for
Bedrock and Secrets Manager on the instance role. None of that is done, because
deploy is its own decision and has not been asked for.
