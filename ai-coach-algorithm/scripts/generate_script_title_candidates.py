from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.llm.client import DEFAULT_MODEL, get_sync_client
from app.core.script_materials import _excerpt, _rule_based_display_title, _standard_speech
from app.utils.file_loader import now_iso, read_json, write_json


DEFAULT_CHUNKS_PATH = "data/marketing_chunks.json"
DEFAULT_CANDIDATES_PATH = "data/review/script_title_candidates.json"
DEFAULT_OVERRIDES_PATH = "data/script_title_overrides.json"


TITLE_SYSTEM_PROMPT = """你是一名金融陪练内容编辑，负责把原始话术资料标题改写成员工看得懂的卡片标题。

要求：
1. 标题必须面向员工动作，优先使用“客户……时怎么……”格式。
2. 不要保留原始编号、括号序号、章节名，例如“（十五）”“4、”“三、”。
3. 不要夸大产品收益，不要写保本、稳赚、保证收益。
4. 每个标题 10 到 24 个中文字符，简洁、自然、可直接展示在小程序卡片上。
5. 只输出 JSON，不要解释。格式：{"items":[{"chunkId":"MCH_000001","displayTitle":"客户担心风险时怎么说明","reason":"..."}]}
"""


def _load_chunks(path: str) -> list[dict[str, Any]]:
    data = read_json(path, default={}) or {}
    chunks = data.get("chunks") if isinstance(data, dict) else []
    return chunks if isinstance(chunks, list) else []


def _task_context_for_chunk(chunk: dict[str, Any]) -> dict[str, Any]:
    return {
        "taskId": None,
        "sceneId": chunk.get("scene_id"),
        "sceneName": chunk.get("scene_name"),
        "title": chunk.get("scene_name") or "",
        "description": chunk.get("customer_query") or chunk.get("title") or "",
        "direction": "",
        "directionLabel": "",
        "intentTags": [],
    }


def _candidate_record(
    chunk: dict[str, Any],
    *,
    display_title: str,
    source: str,
    reason: str = "",
) -> dict[str, Any]:
    speech = _standard_speech(chunk)
    return {
        "chunkId": chunk.get("chunk_id") or chunk.get("id"),
        "status": "pending",
        "candidateDisplayTitle": display_title,
        "reviewedDisplayTitle": "",
        "generationSource": source,
        "generationReason": reason,
        "sceneId": chunk.get("scene_id"),
        "sceneName": chunk.get("scene_name"),
        "knowledgeType": chunk.get("knowledge_type"),
        "sourceTitle": chunk.get("title"),
        "sourceFile": chunk.get("source_file"),
        "candidateStandardSpeech": speech,
        "reviewedStandardSpeech": "",
        "excerpt": _excerpt(speech, max_chars=140),
        "reviewNote": "",
    }


def _rule_title(chunk: dict[str, Any]) -> str:
    return _rule_based_display_title(chunk, _task_context_for_chunk(chunk))


def _parse_llm_response(raw: str) -> dict[str, tuple[str, str]]:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    items = data.get("items") if isinstance(data, dict) else []
    result: dict[str, tuple[str, str]] = {}
    if not isinstance(items, list):
        return result
    for item in items:
        if not isinstance(item, dict):
            continue
        chunk_id = str(item.get("chunkId") or "")
        title = str(item.get("displayTitle") or "").strip()
        reason = str(item.get("reason") or "").strip()
        if chunk_id and title:
            result[chunk_id] = (title, reason)
    return result


def _llm_titles_for_batch(batch: list[dict[str, Any]]) -> dict[str, tuple[str, str]]:
    client = get_sync_client()
    if client is None:
        raise RuntimeError("DEEPSEEK_API_KEY is not configured or openai SDK is unavailable")

    payload = [
        {
            "chunkId": chunk.get("chunk_id") or chunk.get("id"),
            "sceneName": chunk.get("scene_name"),
            "knowledgeType": chunk.get("knowledge_type"),
            "sourceTitle": chunk.get("title"),
            "excerpt": _excerpt(_standard_speech(chunk), max_chars=180),
        }
        for chunk in batch
    ]
    response = client.chat.completions.create(
        model=DEFAULT_MODEL,
        temperature=0.2,
        messages=[
            {"role": "system", "content": TITLE_SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps({"items": payload}, ensure_ascii=False)},
        ],
    )
    content = response.choices[0].message.content or ""
    return _parse_llm_response(content)


def generate_candidates(
    *,
    chunks_path: str,
    output_path: str,
    mode: str,
    batch_size: int,
    limit: int | None,
) -> dict[str, Any]:
    chunks = _load_chunks(chunks_path)
    if limit:
        chunks = chunks[: max(1, limit)]

    llm_titles: dict[str, tuple[str, str]] = {}
    if mode == "llm":
        for start in range(0, len(chunks), max(1, batch_size)):
            batch = chunks[start : start + max(1, batch_size)]
            llm_titles.update(_llm_titles_for_batch(batch))

    records = []
    for chunk in chunks:
        chunk_id = str(chunk.get("chunk_id") or chunk.get("id") or "")
        rule_title = _rule_title(chunk)
        if chunk_id in llm_titles:
            title, reason = llm_titles[chunk_id]
            records.append(
                _candidate_record(
                    chunk,
                    display_title=title,
                    source="llm",
                    reason=reason,
                )
            )
        else:
            records.append(
                _candidate_record(
                    chunk,
                    display_title=rule_title,
                    source="rule",
                    reason="local rule fallback",
                )
            )

    output = {
        "meta": {
            "version": 1,
            "generatedAt": now_iso(),
            "mode": mode,
            "model": DEFAULT_MODEL if mode == "llm" else None,
            "source": chunks_path,
            "total": len(records),
            "reviewInstructions": [
                "Review candidateDisplayTitle and candidateStandardSpeech together as the employee-facing script card.",
                "Fill reviewedDisplayTitle when the display title needs manual edits.",
                "Fill reviewedStandardSpeech only when the standard speech needs manual edits.",
                "Set status to approved or locked for cards that can be used by the API.",
                "Set status to rejected for cards that should not be used.",
                "Run this script with --promote-approved after review.",
            ],
        },
        "items": records,
    }
    write_json(output_path, output)
    return output


def promote_approved(*, candidates_path: str, output_path: str) -> dict[str, Any]:
    data = read_json(candidates_path, default={}) or {}
    items = data.get("items") if isinstance(data, dict) else []
    overrides: dict[str, dict[str, Any]] = {}
    for item in items or []:
        if not isinstance(item, dict):
            continue
        status = str(item.get("status") or "").lower()
        if status not in {"approved", "locked", "rejected"}:
            continue
        chunk_id = str(item.get("chunkId") or "")
        if not chunk_id:
            continue
        if status == "rejected":
            overrides[chunk_id] = {
                "status": status,
                "source": "offline_review",
                "sourceTitle": item.get("sourceTitle"),
                "sourceFile": item.get("sourceFile"),
                "reviewNote": item.get("reviewNote", ""),
                "updatedAt": now_iso(),
            }
            continue

        title = str(item.get("reviewedDisplayTitle") or item.get("candidateDisplayTitle") or "").strip()
        if not title:
            continue
        override_item = {
            "displayTitle": title,
            "status": status,
            "source": "offline_review",
            "sourceTitle": item.get("sourceTitle"),
            "sourceFile": item.get("sourceFile"),
            "reviewNote": item.get("reviewNote", ""),
            "updatedAt": now_iso(),
        }
        speech = str(item.get("reviewedStandardSpeech") or "").strip()
        if speech:
            override_item["standardSpeech"] = speech
        overrides[chunk_id] = override_item

    output = {
        "meta": {
            "version": 1,
            "generatedAt": now_iso(),
            "source": candidates_path,
            "totalApproved": len(overrides),
        },
        "overrides": overrides,
    }
    write_json(output_path, output)
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate reviewed display-title candidates for script cards.")
    parser.add_argument("--chunks", default=DEFAULT_CHUNKS_PATH)
    parser.add_argument("--output", default=DEFAULT_CANDIDATES_PATH)
    parser.add_argument("--mode", choices=["rule", "llm"], default="rule")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--promote-approved", action="store_true")
    parser.add_argument("--candidates", default=DEFAULT_CANDIDATES_PATH)
    parser.add_argument("--overrides", default=DEFAULT_OVERRIDES_PATH)
    args = parser.parse_args()

    if args.promote_approved:
        output = promote_approved(candidates_path=args.candidates, output_path=args.overrides)
        print(f"Promoted {output['meta']['totalApproved']} approved titles to {args.overrides}")
        return

    output = generate_candidates(
        chunks_path=args.chunks,
        output_path=args.output,
        mode=args.mode,
        batch_size=args.batch_size,
        limit=args.limit,
    )
    print(f"Generated {output['meta']['total']} title candidates to {args.output}")


if __name__ == "__main__":
    main()
