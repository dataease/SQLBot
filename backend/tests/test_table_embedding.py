"""表匹配融合评分测试。

测试覆盖：
1. calc_keyword_score - 纯函数，无外部依赖
2. expand_with_terminology - 需要 mock 数据库
3. calc_table_embedding - 集成测试，mock 所有依赖
"""
import json
from unittest.mock import MagicMock, patch

import pytest

from apps.datasource.embedding.table_embedding import (
    calc_keyword_score,
    calc_table_embedding,
)
from apps.terminology.curd.terminology import expand_with_terminology

# mock 目标路径
EMBEDDING_CACHE_PATCH = 'apps.datasource.embedding.table_embedding.EmbeddingModelCache'
SETTINGS_PATCH = 'apps.datasource.embedding.table_embedding.settings'
TERMINOLOGY_PATCH = 'apps.terminology.curd.terminology'


# =============================================================================
# calc_keyword_score 测试（纯函数，无需 mock）
# =============================================================================

class TestCalcKeywordScore:
    """关键词匹配分数计算测试。"""

    def test_full_table_name_match(self):
        """表名完整匹配关键词 -> 1.0"""
        score = calc_keyword_score(
            question="sales_order",
            table_name="sales_order",
            table_comment="销售订单",
            fields=[]
        )
        assert score == 1.0

    def test_full_table_name_match_case_insensitive(self):
        """表名匹配应忽略大小写。"""
        score = calc_keyword_score(
            question="Sales_Order",
            table_name="sales_order",
            table_comment="",
            fields=[]
        )
        assert score == 1.0

    def test_full_table_name_match_among_multiple_keywords(self):
        """多个关键词时，表名完整匹配仍返回 1.0。"""
        score = calc_keyword_score(
            question="sales_order,本月,销售额",
            table_name="sales_order",
            table_comment="",
            fields=[]
        )
        assert score == 1.0

    def test_table_comment_full_match(self):
        """表注释完整匹配关键词 -> 0.9"""
        score = calc_keyword_score(
            question="销售订单",
            table_name="so_header",
            table_comment="销售订单",
            fields=[]
        )
        assert score == 0.9

    def test_table_comment_full_match_custom_comment_priority(self):
        """自定义备注应作为 table_comment 使用（调用方负责合并）。"""
        # 调用方传入已合并的注释，这里模拟该场景
        score = calc_keyword_score(
            question="销售订单",
            table_name="so_header",
            table_comment="自定义备注",
            fields=[]
        )
        # "销售订单" != "自定义备注"，不匹配注释
        assert score == 0.0

    def test_partial_table_name_match_single_keyword(self):
        """关键词匹配表名部分 -> 0.25~0.5（按覆盖比例）。"""
        # "sales" 匹配 "sales_order" 的一部分（2 个部分：sales, order）
        # 覆盖率 = 1/2 = 0.5 -> 0.25 + 0.25*0.5 = 0.375
        score = calc_keyword_score(
            question="sales",
            table_name="sales_order",
            table_comment="",
            fields=[]
        )
        assert score == 0.38  # 0.25 + 0.25 * 0.5 = 0.375，四舍五入为 0.38

    def test_partial_table_name_match_full_coverage(self):
        """表名所有部分都被关键词覆盖 -> 0.5。"""
        # "sales" 和 "order" 覆盖了 "sales_order" 的所有部分
        score = calc_keyword_score(
            question="sales,order",
            table_name="sales_order",
            table_comment="",
            fields=[]
        )
        assert score == 0.5

    def test_field_comment_match(self):
        """关键词匹配字段注释 -> 0.5"""
        fields = [
            {"field_name": "amount", "field_comment": "销售额", "custom_comment": ""},
            {"field_name": "qty", "field_comment": "数量", "custom_comment": ""},
        ]
        score = calc_keyword_score(
            question="销售额",
            table_name="order_detail",
            table_comment="",
            fields=fields
        )
        assert score == 0.5

    def test_field_custom_comment_priority(self):
        """自定义注释应优先于字段注释。"""
        fields = [
            {"field_name": "amount", "field_comment": "原始注释", "custom_comment": "销售额"},
        ]
        score = calc_keyword_score(
            question="销售额",
            table_name="order_detail",
            table_comment="",
            fields=fields
        )
        assert score == 0.5

    def test_field_name_match(self):
        """关键词匹配字段名部分 -> 0.3"""
        fields = [
            {"field_name": "order_amount", "field_comment": "", "custom_comment": ""},
        ]
        score = calc_keyword_score(
            question="amount",
            table_name="transactions",
            table_comment="",
            fields=fields
        )
        assert score == 0.3

    def test_field_name_match_no_duplicate(self):
        """同一词根匹配多个字段时只计算一次。"""
        fields = [
            {"field_name": "order_amount", "field_comment": "", "custom_comment": ""},
            {"field_name": "total_amount", "field_comment": "", "custom_comment": ""},
        ]
        # "amount" 匹配了两个字段，但仍应返回 0.3（不会更高）
        score = calc_keyword_score(
            question="amount",
            table_name="transactions",
            table_comment="",
            fields=fields
        )
        assert score == 0.3

    def test_no_match(self):
        """无匹配 -> 0.0"""
        fields = [
            {"field_name": "id", "field_comment": "主键", "custom_comment": ""},
        ]
        score = calc_keyword_score(
            question="销售额",
            table_name="users",
            table_comment="用户表",
            fields=fields
        )
        assert score == 0.0

    def test_empty_question(self):
        """空问题 -> 0.0"""
        score = calc_keyword_score(
            question="",
            table_name="sales_order",
            table_comment="",
            fields=[]
        )
        assert score == 0.0

    def test_empty_keywords_after_split(self):
        """问题只有逗号/空格 -> 0.0"""
        score = calc_keyword_score(
            question=",, ,",
            table_name="sales_order",
            table_comment="",
            fields=[]
        )
        assert score == 0.0

    def test_priority_table_name_over_comment(self):
        """表名匹配应优先于注释匹配。"""
        score = calc_keyword_score(
            question="sales_order,销售订单",
            table_name="sales_order",
            table_comment="销售订单",
            fields=[]
        )
        assert score == 1.0

    def test_priority_comment_over_field_comment(self):
        """注释匹配（0.9）应优先于字段注释匹配（0.5）。"""
        fields = [
            {"field_name": "amt", "field_comment": "金额", "custom_comment": ""},
        ]
        score = calc_keyword_score(
            question="销售订单",
            table_name="so_detail",
            table_comment="销售订单",
            fields=fields
        )
        assert score == 0.9

    def test_priority_field_comment_over_field_name(self):
        """字段注释匹配（0.5）应优先于字段名匹配（0.3）。"""
        fields = [
            {"field_name": "销售额_column", "field_comment": "", "custom_comment": ""},
            {"field_name": "amt", "field_comment": "销售额", "custom_comment": ""},
        ]
        # 字段注释匹配 "销售额" -> 0.5
        score = calc_keyword_score(
            question="销售额",
            table_name="detail",
            table_comment="",
            fields=fields
        )
        assert score == 0.5

    def test_multiple_keywords_best_score_wins(self):
        """多个关键词时，返回最佳匹配分数。"""
        fields = [
            {"field_name": "qty", "field_comment": "数量", "custom_comment": ""},
        ]
        # "sales_order" 匹配表名 -> 1.0
        # "数量" 匹配字段注释 -> 0.5
        # 最佳为 1.0
        score = calc_keyword_score(
            question="sales_order,数量",
            table_name="sales_order",
            table_comment="",
            fields=fields
        )
        assert score == 1.0

    def test_underscore_table_name_parts(self):
        """带下划线的表名应正确分割。"""
        # "sales_order_detail" -> 部分: {"sales", "order", "detail"}
        # "sales" 覆盖 1/3 -> 0.25 + 0.25*(1/3) ≈ 0.33
        score = calc_keyword_score(
            question="sales",
            table_name="sales_order_detail",
            table_comment="",
            fields=[]
        )
        assert 0.3 <= score <= 0.35

    def test_field_name_with_underscores(self):
        """带下划线的字段名应正确分割。"""
        fields = [
            {"field_name": "customer_order_count", "field_comment": "", "custom_comment": ""},
        ]
        score = calc_keyword_score(
            question="order",
            table_name="stats",
            table_comment="",
            fields=fields
        )
        assert score == 0.3

    def test_real_scenario_sales_query(self):
        """真实场景：'查询销售额' 应匹配包含 '销售额' 字段的表。"""
        fields = [
            {"field_name": "id", "field_comment": "主键", "custom_comment": ""},
            {"field_name": "order_amount", "field_comment": "订单金额", "custom_comment": ""},
            {"field_name": "sales_amount", "field_comment": "销售额", "custom_comment": ""},
        ]
        score = calc_keyword_score(
            question="销售额",
            table_name="daily_report",
            table_comment="日报表",
            fields=fields
        )
        assert score == 0.5  # 字段注释匹配

    def test_real_scenario_table_name_query(self):
        """真实场景：'查 sales_order 表最近的订单' -> 提取 'sales_order'。"""
        score = calc_keyword_score(
            question="sales_order,订单",
            table_name="sales_order",
            table_comment="销售订单",
            fields=[]
        )
        assert score == 1.0  # 表名完整匹配


# =============================================================================
# expand_with_terminology 测试（mock 数据库）
# =============================================================================

class TestExpandWithTerminology:
    """术语同义词扩展测试。"""

    def _make_term(self, id, word, pid=None, enabled=True, oid=1):
        """创建 mock 术语对象的辅助方法。"""
        term = MagicMock()
        term.id = id
        term.word = word
        term.pid = pid
        term.enabled = enabled
        term.oid = oid
        return term

    def test_expand_hit(self):
        """匹配术语的关键词应扩展同义词。"""
        session = MagicMock()
        session.query.return_value.filter.return_value.limit.return_value.all.return_value = [
            self._make_term(1, "销售", pid=None),
            self._make_term(2, "sales", pid=1),
            self._make_term(3, "selling", pid=1),
        ]

        result = expand_with_terminology("销售", session, oid=1)
        keywords = [kw.strip() for kw in result.split(',')]
        assert "销售" in keywords
        assert "sales" in keywords
        assert "selling" in keywords

    def test_no_hit(self):
        """未匹配任何术语的关键词应保持不变。"""
        session = MagicMock()
        session.query.return_value.filter.return_value.limit.return_value.all.return_value = [
            self._make_term(1, "客户", pid=None),
        ]

        result = expand_with_terminology("销售额", session, oid=1)
        assert result == "销售额"

    def test_max_10_keywords(self):
        """扩展后的关键词总数不应超过 10 个。"""
        session = MagicMock()
        # 创建一个有多个同义词的术语
        terms = [self._make_term(1, "销售", pid=None)]
        for i in range(15):
            terms.append(self._make_term(100 + i, f"synonym_{i}", pid=1))
        session.query.return_value.filter.return_value.limit.return_value.all.return_value = terms

        result = expand_with_terminology("销售", session, oid=1)
        keywords = [kw.strip() for kw in result.split(',') if kw.strip()]
        assert len(keywords) <= 10

    def test_empty_terminology(self):
        """空术语表应返回原始关键词。"""
        session = MagicMock()
        session.query.return_value.filter.return_value.limit.return_value.all.return_value = []

        result = expand_with_terminology("销售额,部门", session, oid=1)
        assert result == "销售额,部门"

    def test_none_session(self):
        """session 为 None 时应返回原始关键词。"""
        result = expand_with_terminology("销售额", None, oid=1)
        assert result == "销售额"

    def test_none_oid(self):
        """oid 为 None 时应返回原始关键词。"""
        session = MagicMock()
        result = expand_with_terminology("销售额", session, oid=None)
        assert result == "销售额"

    def test_oid_zero_should_still_query(self):
        """oid=0 不应被视为假值 — 它是有效的组织 ID。"""
        session = MagicMock()
        session.query.return_value.filter.return_value.limit.return_value.all.return_value = [
            self._make_term(1, "销售", pid=None, oid=0),
            self._make_term(2, "revenue", pid=1, oid=0),
        ]
        result = expand_with_terminology("销售", session, oid=0)
        keywords = [kw.strip() for kw in result.split(',')]
        assert "销售" in keywords
        assert "revenue" in keywords

    def test_empty_keywords(self):
        """空关键词字符串应原样返回。"""
        session = MagicMock()
        result = expand_with_terminology("", session, oid=1)
        assert result == ""

    def test_case_insensitive_match(self):
        """术语匹配应忽略大小写。"""
        session = MagicMock()
        session.query.return_value.filter.return_value.limit.return_value.all.return_value = [
            self._make_term(1, "Sales", pid=None),
            self._make_term(2, "revenue", pid=1),
        ]

        result = expand_with_terminology("sales", session, oid=1)
        keywords = [kw.strip() for kw in result.split(',')]
        # "sales"（输入）匹配 "Sales"（术语），忽略大小写
        # "Sales" 不会被添加，因为 "sales" 已在列表中（避免重复）
        # "revenue"（子术语同义词）被添加
        assert "sales" in keywords
        assert "revenue" in keywords
        assert len(keywords) == 2

    def test_multiple_keywords_expansion(self):
        """多个关键词应各自独立扩展。"""
        session = MagicMock()
        session.query.return_value.filter.return_value.limit.return_value.all.return_value = [
            self._make_term(1, "销售", pid=None),
            self._make_term(2, "sales", pid=1),
            self._make_term(3, "部门", pid=None),
            self._make_term(4, "department", pid=3),
        ]

        result = expand_with_terminology("销售,部门", session, oid=1)
        keywords = [kw.strip() for kw in result.split(',')]
        assert "sales" in keywords
        assert "department" in keywords

    def test_child_term_word_also_matches(self):
        """如果关键词匹配子术语的词，应扩展父术语和兄弟术语。"""
        session = MagicMock()
        session.query.return_value.filter.return_value.limit.return_value.all.return_value = [
            self._make_term(1, "销售", pid=None),
            self._make_term(2, "sales", pid=1),
            self._make_term(3, "selling", pid=1),
        ]

        # "sales" 匹配子术语，应扩展包含父术语 "销售" 和兄弟术语 "selling"
        result = expand_with_terminology("sales", session, oid=1)
        keywords = [kw.strip() for kw in result.split(',')]
        assert "sales" in keywords
        assert "销售" in keywords
        assert "selling" in keywords


# =============================================================================
# calc_table_embedding 集成测试（mock embedding）
# =============================================================================

class TestCalcTableEmbedding:
    """融合评分管线集成测试。"""

    def _make_table(self, id, table_name, schema_table, embedding, table_comment="", fields=None):
        return {
            "id": id,
            "table_name": table_name,
            "schema_table": schema_table,
            "embedding": json.dumps(embedding),
            "table_comment": table_comment,
            "fields": fields or []
        }

    @patch('apps.datasource.embedding.table_embedding.settings')
    @patch('apps.datasource.embedding.table_embedding.EmbeddingModelCache')
    def test_exact_table_name_match_ranks_first(self, mock_embed_cache, mock_settings):
        """表名完整匹配关键词时，应排第一。"""
        mock_settings.TABLE_EMBEDDING_KEYWORD_ENABLED = True
        mock_settings.TABLE_EMBEDDING_ALPHA = 0.4
        mock_settings.TABLE_EMBEDDING_COUNT = 10

        mock_model = MagicMock()
        mock_model.embed_query.return_value = [1.0, 0.0, 0.0]
        mock_embed_cache.get_model.return_value = mock_model

        tables = [
            self._make_table(1, "customer", "# Table: customer", [0.0, 1.0, 0.0], "客户表",
                           [{"field_name": "name", "field_comment": "姓名", "custom_comment": ""}]),
            self._make_table(2, "product", "# Table: product", [0.0, 0.0, 1.0], "产品表",
                           [{"field_name": "name", "field_comment": "产品名", "custom_comment": ""}]),
            self._make_table(3, "sales_order", "# Table: sales_order", [0.9, 0.1, 0.0], "销售订单",
                           [{"field_name": "amount", "field_comment": "金额", "custom_comment": ""}]),
        ]

        # 直接传入已提取的关键词
        result = calc_table_embedding(tables, "查 sales_order 表最近的订单",
                                      keywords="sales_order,订单")

        # sales_order 应排第一，因为 keyword_score=1.0
        assert result[0]['table_name'] == "sales_order"
        assert result[0].get('keyword_score') == 1.0

    @patch('apps.datasource.embedding.table_embedding.settings')
    @patch('apps.datasource.embedding.table_embedding.EmbeddingModelCache')
    def test_keyword_disabled_uses_vector_only(self, mock_embed_cache, mock_settings):
        """关键词匹配关闭时，应使用纯向量匹配。"""
        mock_settings.TABLE_EMBEDDING_KEYWORD_ENABLED = False
        mock_settings.TABLE_EMBEDDING_COUNT = 10

        mock_model = MagicMock()
        mock_model.embed_query.return_value = [1.0, 0.0, 0.0]
        mock_embed_cache.get_model.return_value = mock_model

        tables = [
            self._make_table(1, "customer", "# Table: customer", [0.0, 1.0, 0.0]),
            self._make_table(2, "sales_order", "# Table: sales_order", [0.9, 0.1, 0.0]),
        ]

        result = calc_table_embedding(tables, "查 sales_order 表", keywords="sales_order,订单")

        # 关键词匹配关闭，即使传入了 keywords 也应使用纯向量匹配
        assert result[0]['table_name'] == "sales_order"

    @patch('apps.datasource.embedding.table_embedding.settings')
    @patch('apps.datasource.embedding.table_embedding.EmbeddingModelCache')
    def test_no_keywords_falls_back_to_vector(self, mock_embed_cache, mock_settings):
        """未传入 keywords 时，应回退到纯向量匹配。"""
        mock_settings.TABLE_EMBEDDING_KEYWORD_ENABLED = True
        mock_settings.TABLE_EMBEDDING_COUNT = 10

        mock_model = MagicMock()
        mock_model.embed_query.return_value = [1.0, 0.0, 0.0]
        mock_embed_cache.get_model.return_value = mock_model

        tables = [
            self._make_table(1, "customer", "# Table: customer", [0.0, 1.0, 0.0]),
            self._make_table(2, "sales_order", "# Table: sales_order", [0.9, 0.1, 0.0]),
        ]

        # 不传 keywords
        result = calc_table_embedding(tables, "查 sales_order 表")

        # 应回退到纯向量匹配
        assert result[0]['table_name'] == "sales_order"

    @patch('apps.datasource.embedding.table_embedding.settings')
    @patch('apps.datasource.embedding.table_embedding.EmbeddingModelCache')
    def test_multiple_exact_matches_all_rank_first(self, mock_embed_cache, mock_settings):
        """多个 keyword_score=1.0 的表都应排在其他表之前。"""
        mock_settings.TABLE_EMBEDDING_KEYWORD_ENABLED = True
        mock_settings.TABLE_EMBEDDING_ALPHA = 0.4
        mock_settings.TABLE_EMBEDDING_COUNT = 10

        mock_model = MagicMock()
        mock_model.embed_query.return_value = [1.0, 0.0, 0.0]
        mock_embed_cache.get_model.return_value = mock_model

        tables = [
            self._make_table(1, "product", "# Table: product", [0.0, 0.0, 1.0], "产品",
                           [{"field_name": "name", "field_comment": "名称", "custom_comment": ""}]),
            self._make_table(2, "sales_order", "# Table: sales_order", [0.9, 0.1, 0.0], "",
                           [{"field_name": "amount", "field_comment": "", "custom_comment": ""}]),
            self._make_table(3, "customer", "# Table: customer", [0.8, 0.2, 0.0], "",
                           [{"field_name": "name", "field_comment": "", "custom_comment": ""}]),
        ]

        result = calc_table_embedding(tables, "查 sales_order 和 customer",
                                      keywords="sales_order,customer")

        # 前两个应是精确匹配（它们之间的顺序无所谓）
        exact_match_names = {result[0]['table_name'], result[1]['table_name']}
        assert exact_match_names == {"sales_order", "customer"}
        # product 应排最后
        assert result[2]['table_name'] == "product"

    @patch('apps.datasource.embedding.table_embedding.settings')
    @patch('apps.datasource.embedding.table_embedding.EmbeddingModelCache')
    def test_fusion_score_formula(self, mock_embed_cache, mock_settings):
        """验证融合公式：final = α * vec + (1-α) * keyword。"""
        mock_settings.TABLE_EMBEDDING_KEYWORD_ENABLED = True
        mock_settings.TABLE_EMBEDDING_ALPHA = 0.4
        mock_settings.TABLE_EMBEDDING_COUNT = 10

        mock_model = MagicMock()
        mock_model.embed_query.return_value = [1.0, 0.0]
        mock_embed_cache.get_model.return_value = mock_model

        # 表的 vec_score=0.8（通过余弦相似度），keyword_score 来自部分匹配
        tables = [
            self._make_table(1, "sales_order", "# Table: sales_order", [0.8, 0.6], "",
                           [{"field_name": "id", "field_comment": "", "custom_comment": ""}]),
        ]

        result = calc_table_embedding(tables, "sales", keywords="sales")

        # "sales" 部分匹配 "sales_order"（2 个部分中的 1 个）
        # keyword_score = 0.25 + 0.25 * 0.5 = 0.375
        # vec_score = cosine([1,0], [0.8, 0.6]) = 0.8 / (1 * 1) = 0.8
        # final = 0.4 * 0.8 + 0.6 * 0.375 = 0.32 + 0.225 = 0.545
        assert len(result) == 1
        score = result[0]['cosine_similarity']
        assert 0.5 <= score <= 0.6  # 允许小的浮点误差

    @patch('apps.datasource.embedding.table_embedding.settings')
    @patch('apps.datasource.embedding.table_embedding.EmbeddingModelCache')
    def test_fallback_on_unexpected_error(self, mock_embed_cache, mock_settings):
        """遇到意外错误时，应回退到纯向量评分。"""
        mock_settings.TABLE_EMBEDDING_KEYWORD_ENABLED = True
        mock_settings.TABLE_EMBEDDING_ALPHA = 0.4
        mock_settings.TABLE_EMBEDDING_COUNT = 10

        # 让 embed_query 抛出意外错误
        mock_model = MagicMock()
        mock_model.embed_query.side_effect = RuntimeError("模型加载失败")
        mock_embed_cache.get_model.return_value = mock_model

        tables = [
            self._make_table(1, "t1", "# Table: t1", [0.8, 0.6]),
            self._make_table(2, "t2", "# Table: t2", [0.3, 0.7]),
        ]

        # 不应抛出异常，应回退到纯向量匹配
        result = calc_table_embedding(tables, "test", keywords="test")
        assert len(result) == 2


class TestExplicitTableSelection:
    """Retain explicitly named tables and comments even with low vector rankings."""

    TARGET = 'ads_jt_scm_purchase_process_chain_relation_detail_full_1d'
    COMMENT = '采购全链路数据各节点表'

    @pytest.fixture(autouse=True)
    def setup_models(self):
        with patch(EMBEDDING_CACHE_PATCH) as cache, patch(SETTINGS_PATCH) as config:
            config.TABLE_EMBEDDING_KEYWORD_ENABLED = True
            config.TABLE_EMBEDDING_COUNT = 10
            config.TABLE_EMBEDDING_ALPHA = 0.4
            cache.get_model.return_value.embed_query.return_value = [1.0, 0.0]
            self.cache, self.config = cache, config
            yield

    def table(self, name, comment='', embedding=None):
        return dict(id=name, table_name=name, table_comment=comment,
                    schema_table=f'# Table: {name}', fields=[],
                    embedding=json.dumps(embedding if embedding is not None else [0.95, 0.31225]))

    def candidates(self):
        return [self.table(f'{self.TARGET}_{i}', self.COMMENT + f'（环节{i}明细）')
                for i in range(19)] + [self.table(self.TARGET, self.COMMENT, [0.6, 0.8])]

    @pytest.mark.parametrize('keywords', [None, '采购,节点,金额', '查询采购金额'])
    @pytest.mark.parametrize('mention', ['name', 'comment'])
    def test_explicit_mention_survives_top_ten(self, keywords, mention):
        question = f'查询{self.TARGET if mention == "name" else self.COMMENT}的采购金额'
        result = calc_table_embedding(self.candidates(), question, keywords=keywords)
        assert len(result) == 10
        assert result[0]['table_name'] == self.TARGET

    @pytest.mark.parametrize('mention', ['name', 'comment'])
    def test_keyword_disabled(self, mention):
        self.config.TABLE_EMBEDDING_KEYWORD_ENABLED = False
        result = calc_table_embedding(self.candidates(),
                                      self.TARGET if mention == 'name' else self.COMMENT,
                                      keywords='采购')
        assert len(result) == 10
        assert result[0]['table_name'] == self.TARGET

    @pytest.mark.parametrize('failure', ['load', 'encode', 'invalid_embedding', 'missing_embedding'])
    def test_vector_failure_does_not_remove_explicit_table(self, failure):
        tables = self.candidates()
        if failure == 'load':
            self.cache.get_model.side_effect = RuntimeError('model unavailable')
        elif failure == 'encode':
            self.cache.get_model.return_value.embed_query.side_effect = RuntimeError('encoding failed')
        elif failure == 'invalid_embedding':
            tables[0]['embedding'] = 'invalid json'
        else:
            tables[-1]['embedding'] = None
        result = calc_table_embedding(tables, f'查询{self.COMMENT}', keywords='采购')
        assert len(result) == (10 if failure == 'missing_embedding' else len(tables))
        assert result[0]['table_name'] == self.TARGET

    @pytest.mark.parametrize('keywords', [None, '销售额'])
    @pytest.mark.parametrize('failure', ['load', 'encode', 'invalid_embedding'])
    def test_vector_failure_keeps_all_candidates_without_explicit_name(self, keywords, failure):
        tables = self.candidates()
        if failure == 'load':
            self.cache.get_model.side_effect = RuntimeError('model unavailable')
        elif failure == 'encode':
            self.cache.get_model.return_value.embed_query.side_effect = RuntimeError('encoding failed')
        else:
            tables[0]['embedding'] = 'invalid json'
        result = calc_table_embedding(tables, '统计本月销售额', keywords=keywords)
        assert [t['id'] for t in result] == [t['id'] for t in tables]

    @pytest.mark.parametrize('question,long_name,short_name', [
        ('查询订单明细', '订单明细', '订单'),
        ('查询 "sales-order"', 'sales-order', 'sales'),
        ('查询 `sales-order`', 'sales-order', 'sales'),
        ('查询 [sales-order]', 'sales-order', 'sales'),
        ('查询 public."sales-order"', 'sales-order', 'sales'),
    ])
    def test_long_physical_name_does_not_require_short_name(self, question, long_name, short_name):
        self.config.TABLE_EMBEDDING_COUNT = 1
        tables = [self.table(short_name), self.table(long_name, embedding=[0, 1])]
        result = calc_table_embedding(tables, question)
        assert [t['table_name'] for t in result] == [long_name]
        result = calc_table_embedding(tables, question + '，以及 ' + short_name)
        assert {t['table_name'] for t in result} == {long_name, short_name}

    @pytest.mark.parametrize('quoted', ['"sales-order"', '`sales-order`', '[sales-order]', '"订单明细"'])
    def test_unknown_quoted_identifier_does_not_match_part(self, quoted):
        self.config.TABLE_EMBEDDING_COUNT = 1
        tables = [self.table('other'), self.table('sales', embedding=[0, 1]),
                  self.table('订单', embedding=[0, 1])]
        assert calc_table_embedding(tables, '查询 ' + quoted)[0]['table_name'] == 'other'

    @pytest.mark.parametrize('name,quoted', [('a"b', '"a""b"'), ('a`b', '`a``b`'), ('a]b', '[a]]b]')])
    def test_escaped_quoted_identifier(self, name, quoted):
        self.config.TABLE_EMBEDDING_COUNT = 1
        tables = [self.table('other'), self.table(name, embedding=[0, 1])]
        assert calc_table_embedding(tables, '查询 ' + quoted)[0]['table_name'] == name

    @pytest.mark.parametrize('question,expected', [
        ('查询 SALES_ORDER 的金额', 'sales_order'),
        ('查询sales_order的金额', 'sales_order'),
        ('查询 public.sales_order 的金额', 'sales_order'),
        ('查询 "sales_order" 的金额', 'sales_order'),
        ('查询 `sales_order` 的金额', 'sales_order'),
        ('查询 [sales_order] 的金额', 'sales_order'),
        ('查询 sales_order_detail 的金额', 'other'),
        ('查询 old_sales_order 的金额', 'other'),
        ('查询 sales_order2 的金额', 'other'),
        ('查询 sales_order$backup 的金额', 'other'),
    ])
    def test_physical_name_boundaries(self, question, expected):
        self.config.TABLE_EMBEDDING_COUNT = 1
        tables = [self.table('other'), self.table('sales_order', embedding=[0, 1])]
        result = calc_table_embedding(tables, question)
        assert [t['table_name'] for t in result] == [expected]

    def test_longer_comment_wins_only_at_same_occurrence(self):
        self.config.TABLE_EMBEDDING_COUNT = 1
        tables = [self.table('short', '采购订单'), self.table('long', '采购订单明细', [0, 1])]
        result = calc_table_embedding(tables, '查询采购订单明细')
        assert [t['table_name'] for t in result] == ['long']
        result = calc_table_embedding(tables, '比较采购订单和采购订单明细')
        assert {t['table_name'] for t in result} == {'short', 'long'}

    def test_duplicate_comments_keep_all_candidates(self):
        self.config.TABLE_EMBEDDING_COUNT = 1
        tables = [self.table('other'), self.table('a', '采购订单'), self.table('b', '采购订单')]
        result = calc_table_embedding(tables, '查询采购订单')
        assert {t['table_name'] for t in result} == {'a', 'b'}

    def test_explicit_names_can_exceed_limit_without_duplicates(self):
        tables = [self.table(f'purchase_{i}') for i in range(20)]
        names = [t['table_name'] for t in tables[-12:]]
        result = calc_table_embedding(tables, '查询 ' + ','.join(names + names), keywords='采购')
        assert len(result) == 12
        assert {t['table_name'] for t in result} == set(names)

    def test_explicit_table_not_in_candidates_is_not_added(self):
        tables = self.candidates()[:-1]
        result = calc_table_embedding(tables, self.TARGET)
        assert len(result) == 10
        assert self.TARGET not in {t['table_name'] for t in result}

    def test_no_explicit_mention_keeps_existing_ranking(self):
        tables = self.candidates()
        result = calc_table_embedding(tables, '查询采购金额', keywords='采购,金额')
        assert [t['id'] for t in result] == [t['id'] for t in tables[:10]]

    def test_empty_candidates(self):
        assert calc_table_embedding([], self.TARGET, keywords='采购') == []


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
