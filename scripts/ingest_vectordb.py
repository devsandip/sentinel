"""Ingest the governed corpus into the RDS pgvector store (ideas.md item 2).

Reads the sentinel-vectordb CloudFormation outputs, wires the connection env
(password stays in Secrets Manager), creates the pgvector extension and table,
embeds each corpus chunk with Bedrock Titan, and loads them. Then runs a sample
query to confirm retrieval works against the real store.

Run: AWS_PROFILE=admin uv run --extra pgvector python scripts/ingest_vectordb.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

STACK = "sentinel-vectordb"


def _load_stack_env() -> None:
    import boto3

    cfn = boto3.client("cloudformation")
    stack = cfn.describe_stacks(StackName=STACK)["Stacks"][0]
    outs = {o["OutputKey"]: o["OutputValue"] for o in stack["Outputs"]}
    os.environ["SENTINEL_PGVECTOR_HOST"] = outs["Endpoint"]
    os.environ["SENTINEL_PGVECTOR_SECRET_ARN"] = outs["MasterUserSecretArn"]
    os.environ["SENTINEL_PGVECTOR_DBNAME"] = outs["DBName"]
    os.environ["SENTINEL_PGVECTOR_PORT"] = outs.get("Port", "5432")
    print(f"host: {outs['Endpoint']}  db: {outs['DBName']}")


def main() -> None:
    _load_stack_env()
    from sentinel.rag.store import PgVectorStore

    store = PgVectorStore()
    n = store.index()
    print(f"indexed {n} corpus chunks into pgvector")

    print("\nsample query: 'four-fifths rule adverse impact'")
    for sc in store.search("four-fifths rule adverse impact", k=3):
        print(f"  {sc.score:.4f}  [{sc.chunk.provenance}]  {sc.chunk.citation}")


if __name__ == "__main__":
    main()
