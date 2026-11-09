"""Opt-in real-model diagnostic: can the only A+B candidate survive top-10?

Run explicitly with SQLBOT_RUN_METADATA_CONJUNCTION=1 and
SQLBOT_TEST_DATABASE_URL pointing at an authorized disposable PostgreSQL DB.
Optionally set SQLBOT_METADATA_CONJUNCTION_REPORT to an external JSON file.
This deliberately asserts retrieval quality, so failures are findings, not
infrastructure failures or claims that all customer questions must succeed.
Synthetic keywords are supplied; no LLM, HTTP or customer-data acceptance.
"""

import hashlib
import importlib.metadata
import json
import os
import random
import subprocess
import time
import uuid
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("SQLBOT_RUN_METADATA_CONJUNCTION") != "1",
    reason="explicit disposable PostgreSQL/local-model quality evaluation required",
)

CASES = {
    "region_recovery": (
        "业务大区",
        "质保追偿金额",
        "按业务大区统计质保追偿金额",
        "按地区汇总向供应商追回的质量损失款",
        "地区,质量损失款",
    ),
    "contract_receipts": (
        "合同签订金额",
        "回款到账金额",
        "对比合同签订金额与回款到账金额",
        "签下的合同金额和实际收到的款项分别有多少",
        "合同金额,实收款项",
    ),
    "refund_ratio": (
        "售后退款金额",
        "订单实收金额",
        "计算售后退款金额占订单实收金额的比例",
        "退给客户的钱占实际收到订单款项的比例",
        "退款,实收",
    ),
    "credit_overdue": (
        "客户信用等级",
        "逾期应收金额",
        "按客户信用等级统计逾期应收金额",
        "按客户信用评级汇总过期未收回的欠款",
        "信用评级,欠款",
    ),
}
LAYOUTS = ("wide_adjacent", "wide_split", "short_decoys_split")
MODES = ("table_hybrid", "table_vector", "datasource_vector")


@pytest.fixture(scope="module")
def conjunction_results(tmp_path_factory):
    # Import through normal application bootstrap, never AST-load the scorer.
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("HF_HUB_OFFLINE", "1")
        patch.setenv("TRANSFORMERS_OFFLINE", "1")
        import torch
        from sqlalchemy import text
        from sqlalchemy.orm import scoped_session, sessionmaker
        from sqlmodel import Session, create_engine

        import main  # noqa: F401
        from apps.ai_model.embedding import EmbeddingModelCache
        from apps.datasource.crud.embedding_state import invalidate_metadata
        from apps.datasource.crud.table import (
            _resource_input,
            _table_input,
            save_ds_embedding,
            save_table_embedding,
        )
        from apps.datasource.embedding.ds_embedding import get_ds_embedding
        from apps.datasource.embedding.metadata_chunks import chunk_text, read_metadata
        from apps.datasource.embedding.table_embedding import calc_table_embedding
        from apps.datasource.models.datasource import (
            CoreDatasource,
            CoreField,
            CoreTable,
        )
        from apps.datasource.models.metadata_embedding import MetadataEmbedding
        from common.core.config import settings
        from common.core.embedding_config import EmbeddingConfig

        torch.set_num_threads(4)
        patch.setattr(settings, "TABLE_EMBEDDING_ENABLED", True)
        config = EmbeddingConfig(True, 0.4, 5, 0.4, 5, True, 10, 0.4, True, 10)
        real = EmbeddingModelCache.get_model()
        transformer = real._client._first_module()
        observed = {"blocks": 0, "max_tokens": 0}
        queries = {}

        class ObservedModel:
            _client = real._client

            def embed_documents(self, values):
                prepared = [value.replace("\n", " ").strip() for value in values]
                if transformer.do_lower_case:
                    prepared = [value.lower() for value in prepared]
                lengths = [
                    len(
                        transformer.tokenizer(
                            value,
                            truncation=False,
                            verbose=False,
                            add_special_tokens=True,
                        )["input_ids"]
                    )
                    for value in prepared
                ]
                actual = (
                    real._client.tokenize(prepared)["attention_mask"]
                    .sum(dim=1)
                    .tolist()
                )
                assert lengths == actual and max(actual) <= transformer.max_seq_length
                observed["blocks"] += len(values)
                observed["max_tokens"] = max(observed["max_tokens"], max(actual))
                return real.embed_documents(values)

            def embed_query(self, value):
                if value not in queries:
                    queries[value] = real.embed_query(value)
                return queries[value]

        provider = ObservedModel()
        patch.setattr(EmbeddingModelCache, "get_model", lambda: provider)
        url = os.environ["SQLBOT_TEST_DATABASE_URL"]
        assert url.startswith("postgresql+psycopg://")
        admin = create_engine(url)
        schema = "metadata_conjunction_" + uuid.uuid4().hex
        with admin.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        database = create_engine(
            url, connect_args={"options": f"-csearch_path={schema},public"}
        )
        sessions = scoped_session(sessionmaker(bind=database, class_=Session))
        report = {
            "revision": subprocess.check_output(
                ["git", "rev-parse", "HEAD"], text=True
            ).strip(),
            "test_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "versions": {
                name: importlib.metadata.version(name)
                for name in (
                    "sentence-transformers",
                    "transformers",
                    "torch",
                    "sqlbot-xpack",
                )
            },
            "candidate_count": 25,
            "top_count": 10,
            "alpha": 0.4,
            "negative_candidates": {"a_only": 11, "b_only": 11, "neither": 2},
            "cases": CASES,
            "rows": [],
            "coverage": [],
            "observed": observed,
        }
        started = time.perf_counter()
        try:
            for model in (CoreDatasource, CoreTable, CoreField, MetadataEmbedding):
                model.__table__.create(database)
            with database.begin() as connection:
                connection.execute(
                    text(
                        "CREATE TABLE sys_arg (id BIGINT PRIMARY KEY, pkey VARCHAR(255), pval VARCHAR(255), ptype VARCHAR(255), sort_no INTEGER NOT NULL DEFAULT 0)"
                    )
                )

            def add_table(session, ds_id, index, a, b, *, auxiliary=False):
                table = CoreTable(
                    ds_id=ds_id,
                    table_name=f"{'aux' if auxiliary else 'detail'}_{index:03}",
                    table_comment="经营统计明细",
                    checked=True,
                )
                session.add(table)
                session.flush()
                for position in range(8 if auxiliary else 120):
                    label = f"经营辅助指标{position:03}"
                    if (
                        not auxiliary
                        and position == 1
                        and (index == 0 or 1 <= index <= 11)
                    ):
                        label = a
                    if (
                        not auxiliary
                        and position == 2
                        and (index == 0 or 12 <= index <= 22)
                    ):
                        label = b
                    session.add(
                        CoreField(
                            ds_id=ds_id,
                            table_id=table.id,
                            field_name=f"metric_{position:03}",
                            field_index=position,
                            field_type="DECIMAL",
                            field_comment=label,
                            checked=True,
                        )
                    )
                return table.id

            for case_number, (
                case,
                (a, b, exact, paraphrase, paraphrase_keywords),
            ) in enumerate(CASES.items()):
                with Session(database) as session:
                    pool = CoreDatasource(
                        name="表候选集合", description="经营分析", type="pg", oid=1
                    )
                    session.add(pool)
                    session.flush()
                    table_ids, source_table_ids, ds_ids = [], [], []
                    for index in range(25):
                        source = CoreDatasource(
                            name=f"业务资料_{index:03}",
                            description="经营分析",
                            type="pg",
                            oid=1,
                        )
                        session.add(source)
                        session.flush()
                        ds_ids.append(source.id)
                        table_ids.append(add_table(session, pool.id, index, a, b))
                        source_table_ids.append(
                            add_table(session, source.id, index, a, b)
                        )
                        add_table(session, source.id, index, a, b, auxiliary=True)
                    session.commit()
                for layout in LAYOUTS:
                    if layout != "wide_adjacent":
                        changed = (
                            [table_ids[0], source_table_ids[0]]
                            if layout == "wide_split"
                            else table_ids[1:] + source_table_ids[1:]
                        )
                        with Session(database) as session:
                            for key in changed:
                                table = session.get(CoreTable, key)
                                invalidate_metadata(session, table.ds_id, [key])
                                fields = (
                                    session.query(CoreField)
                                    .filter(CoreField.table_id == key)
                                    .all()
                                )
                                for field in fields:
                                    if layout == "wide_split":
                                        if field.field_index == 2:
                                            field.field_index = 119
                                        elif field.field_index == 119:
                                            field.field_index = 2
                                    elif field.field_index >= 3:
                                        field.checked = False
                                    session.add(field)
                            session.commit()
                    save_table_embedding(sessions, table_ids)
                    save_ds_embedding(sessions, ds_ids)
                    with Session(database) as session:
                        tables = []
                        for key in table_ids:
                            table = session.get(CoreTable, key)
                            fields = (
                                session.query(CoreField)
                                .filter(
                                    CoreField.table_id == key,
                                    CoreField.checked.is_(True),
                                )
                                .all()
                            )
                            tables.append(
                                {
                                    "id": key,
                                    "table_name": table.table_name,
                                    "table_comment": table.table_comment,
                                    "schema_table": _table_input(session, table),
                                    "fields": [
                                        {
                                            "field_name": f.field_name,
                                            "field_comment": f.field_comment,
                                            "custom_comment": f.custom_comment,
                                        }
                                        for f in fields
                                    ],
                                }
                            )
                        sources = [
                            {
                                "id": key,
                                "name": session.get(CoreDatasource, key).name,
                                "description": "经营分析",
                            }
                            for key in ds_ids
                        ]
                        random.Random(17 + case_number).shuffle(tables)
                        random.Random(17 + case_number).shuffle(sources)
                        for kind, keys, cls in (
                            ("table", table_ids, CoreTable),
                            ("datasource", ds_ids, CoreDatasource),
                        ):
                            counts = []
                            for key in keys:
                                content = _resource_input(
                                    session, session.get(cls, key)
                                )
                                counts.append(
                                    len(read_metadata(session, kind, key, content))
                                )
                            target_input = _resource_input(
                                session, session.get(cls, keys[0])
                            )
                            chunks = chunk_text(target_input, provider)
                            a_chunks = [
                                i for i, value in enumerate(chunks) if a in value
                            ]
                            b_chunks = [
                                i for i, value in enumerate(chunks) if b in value
                            ]
                            assert a_chunks and b_chunks
                            assert bool(set(a_chunks) & set(b_chunks)) == (
                                layout == "wide_adjacent"
                            )
                            report["coverage"].append(
                                {
                                    "case": case,
                                    "layout": layout,
                                    "resource": kind,
                                    "target_chunks": counts[0],
                                    "decoy_min_chunks": min(counts[1:]),
                                    "decoy_max_chunks": max(counts[1:]),
                                    "a_chunks": a_chunks,
                                    "b_chunks": b_chunks,
                                }
                            )
                        for style, question, keywords in (
                            ("exact", exact, f"{a},{b}"),
                            ("paraphrase", paraphrase, paraphrase_keywords),
                        ):
                            for mode in MODES:
                                if mode == "datasource_vector":
                                    chosen = get_ds_embedding(
                                        session, sources, None, question, config=config
                                    )
                                    target = ds_ids[0]
                                else:
                                    chosen = calc_table_embedding(
                                        tables,
                                        question,
                                        session=session,
                                        keywords=keywords
                                        if mode == "table_hybrid"
                                        else None,
                                        config=config,
                                    )
                                    target = table_ids[0]
                                selected = [item["id"] for item in chosen]
                                assert len(selected) == 10, (
                                    "Fallback/invalid setup must not look like a quality pass"
                                )
                                report["rows"].append(
                                    {
                                        "case": case,
                                        "layout": layout,
                                        "style": style,
                                        "mode": mode,
                                        "question": question,
                                        "keywords": keywords,
                                        "target_hit": target in selected,
                                        "target_rank": selected.index(target) + 1
                                        if target in selected
                                        else None,
                                        "selected_indices": [
                                            (
                                                ds_ids
                                                if mode == "datasource_vector"
                                                else table_ids
                                            ).index(key)
                                            for key in selected
                                        ],
                                    }
                                )
                    print(f"evaluated {case} {layout}", flush=True)
        finally:
            report["elapsed_seconds"] = time.perf_counter() - started
            sessions.remove()
            database.dispose()
            with admin.begin() as connection:
                connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
            admin.dispose()
            destination = Path(
                os.environ.get(
                    "SQLBOT_METADATA_CONJUNCTION_REPORT",
                    str(tmp_path_factory.mktemp("conjunction") / "report.json"),
                )
            )
            destination.write_text(
                json.dumps(report, ensure_ascii=False, indent=2) + "\n"
            )
            print(f"conjunction report: {destination}", flush=True)
        return report["rows"]


@pytest.mark.parametrize("case", CASES)
@pytest.mark.parametrize("layout", LAYOUTS)
@pytest.mark.parametrize("style", ("exact", "paraphrase"))
@pytest.mark.parametrize("mode", MODES)
def test_joint_requirement_keeps_the_only_complete_candidate(
    conjunction_results, case, layout, style, mode
):
    row = next(
        row
        for row in conjunction_results
        if (row["case"], row["layout"], row["style"], row["mode"])
        == (case, layout, style, mode)
    )
    assert row["target_hit"], json.dumps(row, ensure_ascii=False)
