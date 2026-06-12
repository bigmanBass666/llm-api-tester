"""platforms/nvidia/merger.py 单元测试

覆盖 merge_models、build_api_index 的全部分支。
纯单元测试，构造 ModelInfo + ScrapedMetadata。
"""

import pytest
from src.models import ModelInfo, ModelType, ScrapedMetadata
from platforms.nvidia.merger import merge_models, build_api_index


# ── Helpers ────────────────────────────────────────

def make_model(model_id, call_volume="", created_at=None, owned_by=None,
               model_type=ModelType.TEXT, rank=0):
    scraped = ScrapedMetadata(
        call_volume=call_volume,
        created_at=created_at,
        api_owned_by=owned_by,
    )
    return ModelInfo(
        id=model_id, name=model_id.split("/")[-1],
        model_type=model_type, rank=rank, scraped=scraped,
    )


# ── build_api_index ────────────────────────────────

class TestBuildApiIndex:
    def test_basic_index(self):
        models = [make_model("a/m1"), make_model("a/m2")]
        idx = build_api_index(models)
        assert idx == {"a/m1": models[0], "a/m2": models[1]}

    def test_empty_list(self):
        assert build_api_index([]) == {}

    def test_duplicate_ids_last_wins(self):
        m1 = make_model("a/m1", call_volume="100K")
        m2 = make_model("a/m1", call_volume="200K")
        idx = build_api_index([m1, m2])
        assert len(idx) == 1
        assert idx["a/m1"].scraped.call_volume == "200K"


# ── merge_models ───────────────────────────────────

class TestMergeModels:
    def test_basic_merge_preserves_scraper_fields(self):
        """爬虫数据为主：name, vendor, category, tags"""
        scraper = [make_model("a/m1", call_volume="1M", rank=1)]
        api = [make_model("a/m1", created_at=1700000000, owned_by="vendor-a")]
        merged = merge_models(scraper, api)
        assert len(merged) == 1
        assert merged[0].scraped.call_volume == "1M"  # 来自爬虫
        assert merged[0].scraped.created_at == 1700000000  # 来自 API
        assert merged[0].scraped.api_owned_by == "vendor-a"  # 来自 API

    def test_api_only_models_appended(self):
        """API 有但爬虫没有的模型追加到末尾"""
        scraper = [make_model("a/m1")]
        api = [make_model("a/m1"), make_model("b/m2")]
        merged = merge_models(scraper, api)
        assert len(merged) == 2
        assert merged[0].id == "a/m1"
        assert merged[1].id == "b/m2"

    def test_no_duplicates(self):
        """相同 ID 不重复"""
        scraper = [make_model("a/m1"), make_model("a/m2")]
        api = [make_model("a/m1"), make_model("a/m2")]
        merged = merge_models(scraper, api)
        assert len(merged) == 2

    def test_empty_scraper_returns_api(self):
        """爬虫为空时，返回 API 模型"""
        api = [make_model("a/m1"), make_model("a/m2")]
        merged = merge_models([], api)
        assert len(merged) == 2

    def test_empty_api_returns_scraper(self):
        """API 为空时，返回爬虫模型"""
        scraper = [make_model("a/m1", call_volume="500K")]
        merged = merge_models(scraper, [])
        assert len(merged) == 1
        assert merged[0].scraped.call_volume == "500K"

    def test_both_empty(self):
        assert merge_models([], []) == []

    def test_scraped_fields_not_overwritten_by_none(self):
        """API scraped 有值但字段为 None 时，不覆盖爬虫的值"""
        scraper = [make_model("a/m1", call_volume="1M")]
        api = [make_model("a/m1")]  # call_volume=""
        merged = merge_models(scraper, api)
        assert merged[0].scraped.call_volume == "1M"

    def test_description_filled_from_api(self):
        """爬虫没有 description 时，从 API 填充"""
        s = make_model("a/m1")
        s.description = ""
        a = make_model("a/m1")
        a.description = "API description"
        merged = merge_models([s], [a])
        assert merged[0].description == "API description"

    def test_description_not_overwritten(self):
        """爬虫已有 description 时，不被 API 覆盖"""
        s = make_model("a/m1")
        s.description = "Scraper description"
        a = make_model("a/m1")
        a.description = "API description"
        merged = merge_models([s], [a])
        assert merged[0].description == "Scraper description"

    def test_merge_without_scraped_objects(self):
        """ModelInfo 没有 scraped 字段时也能合并"""
        s = ModelInfo(id="a/m1", name="m1")
        a = ModelInfo(id="a/m1", name="m1", scraped=ScrapedMetadata(created_at=100))
        merged = merge_models([s], [a])
        assert len(merged) == 1
        assert merged[0].scraped.created_at == 100

    def test_multiple_merge_order_preserved(self):
        """合并后爬虫模型顺序不变"""
        scraper = [make_model(f"v/m{i}", rank=i) for i in range(5)]
        api = [make_model(f"v/m{i}") for i in range(5)]
        merged = merge_models(scraper, api)
        ids = [m.id for m in merged]
        assert ids == ["v/m0", "v/m1", "v/m2", "v/m3", "v/m4"]
