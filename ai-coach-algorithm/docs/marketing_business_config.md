# 营销话术业务线配置

当前营销话术资料处理流程通过 `configs/marketing_business_config.json` 管理业务线。

新增业务时，优先修改配置文件，不需要改 `marketing_doc_processor.py` 的主流程代码。

## 配置字段

```json
{
  "businesses": {
    "CC": {
      "business_name": "信用卡营销",
      "folder": "信用卡营销话术",
      "default_scene": "CC_GENERAL",
      "scenes": {
        "CC_GENERAL": "信用卡综合营销"
      },
      "scene_rules": [
        {
          "scene_id": "CC_GENERAL",
          "keywords": ["办卡", "权益"],
          "source_keywords": ["信用卡"]
        }
      ]
    }
  }
}
```

- `business_type`: 外层 key，例如 `CC`。
- `business_name`: 展示名称。
- `folder`: 原始资料保存目录，上传接口会按这个字段落盘。
- `default_scene`: 没有命中任何规则时使用的默认场景。
- `scenes`: 场景 ID 到中文名称的映射。
- `scene_rules`: 初步场景分类规则，按顺序命中。

## 相关接口

- `GET /knowledge/marketing-businesses`: 查看当前支持的业务线。
- `POST /knowledge/marketing-docs/upload`: 上传新的原始话术资料。
- `POST /knowledge/marketing-docs/extract-text`: 抽取文本。
- `POST /knowledge/marketing-docs/clean-text`: 清洗文本。
- `POST /knowledge/marketing-docs/build-sections`: 生成可 review 的 section。
