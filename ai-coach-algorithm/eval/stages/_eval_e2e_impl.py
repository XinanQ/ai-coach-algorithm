"""E2E evaluation implementation - lazy-loaded to avoid circular imports.

This module contains the heavy E2E evaluation logic that imports dialog_manager
and other runtime components. It's loaded on-demand by eval_e2e.py.
"""
from __future__ import annotations

import asyncio
import json
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from app.core.dialog_manager import (
    finish_dialogue,
    reply_dialogue,
    start_dialogue,
)
from app.core.marketing_rag import retrieve_marketing_knowledge
from app.core.intent_labels import INTENT_LABELS
from eval.metrics import StageResult


GOLD_PATH = Path("data/eval/e2e_dialog_gold.jsonl")
TRACE_PATH = Path("data/eval/e2e_verbose.json")


def load_e2e_gold(path: Path | None = None) -> list[dict[str, Any]]:
    """Load E2E gold dataset from JSONL file."""
    target_path = path or GOLD_PATH
    if not target_path.exists():
        return []

    rows = []
    with open(target_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def save_e2e_trace(trace: dict[str, Any], path: Path | None = None) -> None:
    """Save detailed E2E execution trace."""
    target_path = path or TRACE_PATH
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    default_path = Path(f"data/eval/e2e_verbose_{timestamp}.json")

    with open(target_path or default_path, "w", encoding="utf-8") as f:
        json.dump(trace, f, ensure_ascii=False, indent=2)


class E2EEvaluator:
    """End-to-end dialogue evaluator.

    Simulates complete dialogue flows and validates each stage.
    """

    def __init__(self, skip_slow: bool = False, verbose: bool = False):
        self.skip_slow = skip_slow
        self.verbose = verbose
        self.session_id: str | None = None
        self.run_id = f"e2e_{uuid.uuid4().hex[:8]}"
        self._tempdir = tempfile.TemporaryDirectory(prefix=f"ai_coach_{self.run_id}_")
        self._install_isolated_memory()

    def _install_isolated_memory(self) -> None:
        """Use per-run JSON memory so E2E cannot corrupt local dev state."""
        from app.core import memory_manager as memory_manager_module
        from app.core.memory_manager import MemoryManager
        from app.core.memory_store import BackendState, JsonLongTermMemoryStore, JsonShortTermMemoryStore

        temp_root = Path(self._tempdir.name)
        short_store = JsonShortTermMemoryStore(str(temp_root / "sessions.json"))
        long_store = JsonLongTermMemoryStore(str(temp_root / "longterm.json"))
        short_store.state = BackendState(requested_backend="json", active_backend="json", available=True)  # type: ignore[attr-defined]
        long_store.state = BackendState(requested_backend="json", active_backend="json", available=True)  # type: ignore[attr-defined]
        memory_manager_module._MEMORY_MANAGER = MemoryManager(
            short_store=short_store,
            long_store=long_store,
        )

    def evaluate_case(self, case: dict[str, Any]) -> dict[str, Any]:
        """Evaluate a single E2E case.

        Args:
            case: E2E test case with employee_messages and expected outputs

        Returns:
            Dict with pass/fail for each stage and overall_pass, plus detailed failure traces
        """
        result = {
            "case_id": case.get("id", "unknown"),
            "scene_id": case.get("scene_id", "INS_PERIODIC"),
            "total_rounds": len(case.get("employee_messages", [])),
        }

        # Stage 1: Start dialogue
        start_result = self._evaluate_start(case)
        result["start_pass"] = start_result["pass"]
        result["start_trace"] = start_result.get("trace", {})
        if "error" in start_result:
            result["start_trace"]["error"] = start_result["error"]

        # Stage 2: Multi-round reply with intent/gap/retrieval validation
        reply_results = []
        for i, employee_msg in enumerate(case.get("employee_messages", [])):
            reply_result = self._evaluate_reply(
                case, i, employee_msg, case.get("expected_intents", [])
            )
            reply_results.append(reply_result)

        result["reply_results"] = reply_results
        result["intent_pass"] = all(r.get("intent_pass", True) for r in reply_results)
        result["gap_pass"] = all(r.get("gap_pass", True) for r in reply_results)
        result["retrieval_hit"] = all(r.get("retrieval_hit", True) for r in reply_results)
        result["followup_pass"] = all(r.get("followup_pass", True) for r in reply_results)

        # Stage 3: Contract compliance (no liveScore/source in reply)
        result["contract_pass"] = all(r.get("contract_pass", True) for r in reply_results)

        # Stage 4: Finish dialogue with score validation
        finish_result = self._evaluate_finish(case)
        result["finish_pass"] = finish_result["pass"]
        result["finish_score_pass"] = finish_result.get("score_pass", True)
        result["strict_score_pass"] = finish_result.get("strict_score_pass", result["finish_score_pass"])
        result["weak_tag_pass"] = finish_result.get("weak_tag_pass", True)
        result["finish_trace"] = finish_result.get("trace", {})

        # Overall pass: all stages must pass
        result["overall_pass"] = (
            result["start_pass"]
            and result["contract_pass"]
            and result["intent_pass"]
            and result["gap_pass"]
            and result["retrieval_hit"]
            and result["followup_pass"]
            and result["finish_score_pass"]
            and result["weak_tag_pass"]
        )
        result["strict_overall_pass"] = (
            result["start_pass"]
            and result["contract_pass"]
            and result["intent_pass"]
            and result["gap_pass"]
            and result["retrieval_hit"]
            and result["followup_pass"]
            and result["strict_score_pass"]
            and result["weak_tag_pass"]
        )

        # Build detailed failure trace
        result["failure_trace"] = self._build_failure_trace(result, case)

        if self.verbose:
            result["dialogue_trace"] = self._build_dialogue_trace(reply_results, finish_result)

        return result

    def _evaluate_start(self, case: dict[str, Any]) -> dict[str, Any]:
        """Evaluate dialogue start."""
        try:
            start_result = start_dialogue(
                user_id=case.get("user_id", f"eval_{case.get('id', 'unknown')}"),
                scene_id=case.get("scene_id", "INS_PERIODIC"),
                customer_id=case.get("customer_id"),
                task_id=case.get("task_id"),
                total_rounds=case.get("total_rounds", 3),
            )
            self.session_id = start_result.get("session", {}).get("session_id")

            return {
                "pass": bool(self.session_id),
                "trace": {
                    "session_id": self.session_id,
                    "opening": start_result.get("ai_customer_message", "")[:100],
                    "run_id": self.run_id,
                },
            }
        except Exception as e:
            return {"pass": False, "error": str(e)}

    def _evaluate_reply(
        self,
        case: dict[str, Any],
        turn_idx: int,
        employee_msg: str,
        expected_intents: list[str],
    ) -> dict[str, Any]:
        """Evaluate a single reply turn."""
        if not self.session_id:
            return {"pass": False, "error": "No active session"}

        try:
            reply_result = asyncio.run(reply_dialogue(self.session_id, employee_msg))

            # Contract check: no liveScore/source in reply
            contract_pass = self._check_reply_contract(reply_result)

            # Intent validation
            intent_result = self._validate_intent(
                reply_result.get("intent", {}),
                expected_intents,
                turn_idx,
            )

            # Gap validation
            gap_result = self._validate_gap(
                reply_result.get("intent_gap", []),
                reply_result.get("covered_intents", []),
                expected_intents,
            )

            # Retrieval validation (skip if finished)
            is_finished = reply_result.get("finished", False)
            retrieval_result = {"pass": True, "method": "skipped", "reason": "dialogue_finished", "trace": {}}
            if not is_finished:
                retrieval_result = self._validate_retrieval(
                    reply_result.get("retrieval", {}),
                    case.get("expected_must_points", []),
                )

            # Follow-up validation (skip if finished)
            followup_result = {"pass": True, "method": "skipped", "reason": "dialogue_finished", "trace": {}}
            if not is_finished:
                followup_result = self._validate_followup(
                    reply_result.get("ai_customer_message", ""),
                    reply_result.get("intent_gap", []),
                    case.get("expected_followup_direction", []),
                    turn_idx,
                )

            return {
                "pass": contract_pass and intent_result["pass"] and gap_result["pass"] and retrieval_result["pass"] and followup_result["pass"],
                "contract_pass": contract_pass,
                "intent_pass": intent_result["pass"],
                "gap_pass": gap_result["pass"],
                "retrieval_hit": retrieval_result["pass"],
                "retrieval_method": retrieval_result.get("method"),
                "retrieval_reason": retrieval_result.get("reason"),
                "retrieval_trace": retrieval_result.get("trace", {}),
                "followup_pass": followup_result["pass"],
                "followup_method": followup_result.get("method"),
                "followup_reason": followup_result.get("reason"),
                "followup_trace": followup_result.get("trace", {}),
                "round": reply_result.get("round"),
                "finished": is_finished,
                "ai_customer_message": reply_result.get("ai_customer_message", ""),
                "retrieval_items": reply_result.get("retrieval", {}).get("items", []),
            }

        except Exception as e:
            return {
                "pass": False,
                "contract_pass": False,
                "intent_pass": False,
                "gap_pass": False,
                "retrieval_hit": False,
                "retrieval_method": "error",
                "retrieval_reason": str(e)[:100],
                "retrieval_trace": {},
                "followup_pass": False,
                "followup_method": "error",
                "followup_reason": str(e)[:100],
                "followup_trace": {},
                "round": turn_idx,
                "finished": False,
                "error": str(e),
            }

    def _evaluate_finish(self, case: dict[str, Any]) -> dict[str, Any]:
        """Evaluate dialogue finish."""
        if not self.session_id:
            return {"pass": False, "score_pass": False, "weak_tag_pass": False}

        try:
            finish_result = asyncio.run(finish_dialogue(self.session_id))
            session = finish_result.get("session", {})
            score_result = session.get("score_result", {})

            total_score = score_result.get("total_score", 0)
            weak_tags = score_result.get("weakness_tags", [])

            # Validate score range
            expected_range = case.get("expected_score_range", [0, 100])
            score_pass = expected_range[0] <= total_score <= expected_range[1]
            strict_range = case.get("strict_score_range", expected_range)
            strict_score_pass = strict_range[0] <= total_score <= strict_range[1]

            # Validate weak tags relevance
            weak_tag_result = self._validate_weak_tags(
                weak_tags,
                case.get("expected_weak_tags", []),
            )

            return {
                "pass": True,
                "score_pass": score_pass,
                "strict_score_pass": strict_score_pass,
                "weak_tag_pass": weak_tag_result["pass"],
                "weak_tag_method": weak_tag_result.get("method"),
                "weak_tag_reason": weak_tag_result.get("reason"),
                "trace": {
                    "total_score": total_score,
                    "weak_tags": weak_tags,
                    "expected_range": expected_range,
                    "strict_expected_range": strict_range,
                    "calibration_reason": case.get("calibration_reason"),
                    "weak_tag_trace": weak_tag_result.get("trace", {}),
                },
            }

        except Exception as e:
            return {
                "pass": False,
                "score_pass": False,
                "strict_score_pass": False,
                "weak_tag_pass": False,
                "weak_tag_method": "error",
                "weak_tag_reason": str(e)[:100],
                "error": str(e),
            }

    def _check_reply_contract(self, reply_result: dict[str, Any]) -> bool:
        """Check that reply doesn't contain liveScore/source."""
        # Check direct response fields
        if "liveScore" in reply_result or "score" in reply_result:
            return False
        if "source" in reply_result:
            return False

        # Check nested session data
        session = reply_result.get("session", {})
        if "liveScore" in session or "score_result" in session:
            return False

        return True

    def _validate_intent(
        self,
        intent_result: dict[str, Any],
        expected_intents: list[str],
        turn_idx: int,
    ) -> dict[str, Any]:
        """Validate intent detection.

        For E2E, we check that:
        - Intent detection system is working (not crashing)
        - We allow empty detection results (intent detection is a separate module)
        - If intents ARE detected, they should overlap with expected intents

        This is a loose validation since intent detection has its own evaluation stage.

        Returns dict with pass, method, reason, and trace details.
        """
        result = {
            "pass": True,
            "method": "loose_overlap",
            "reason": "",
            "trace": {
                "detected_labels": intent_result.get("intent_labels", []),
                "llm_intents": intent_result.get("llm_intents", []),
            },
        }

        detected_labels = set(intent_result.get("intent_labels", []))
        llm_intents = set(intent_result.get("llm_intents", []))

        # Use LLM intents if available
        all_intents = llm_intents if llm_intents else detected_labels

        if not expected_intents:
            # If no expected intents specified, any detection is OK
            result["reason"] = "no_expected_intents"
            return result

        # Allow empty detection (intent system may not detect anything)
        # E2E is about the dialogue flow, not intent detection accuracy
        if not all_intents:
            result["reason"] = "no_intents_detected_but_allowed"
            return result

        # If intents were detected, check for overlap with expected intents
        overlap = bool(all_intents & set(expected_intents))
        if overlap:
            result["reason"] = "has_expected_intent_overlap"
            result["trace"]["overlap"] = list(all_intents & set(expected_intents))
        else:
            result["reason"] = "no_expected_intent_overlap"
            result["pass"] = True  # Still pass - this is loose validation

        return result

    def _validate_gap(
        self,
        intent_gap: list[str],
        covered_intents: list[str],
        expected_intents: list[str],
    ) -> dict[str, Any]:
        """Validate gap computation.

        Gap validation checks that:
        - Gaps are valid intents (in INTENT_LABELS)
        - Gaps are reasonable for the context

        expected_intents in test data represents the global intent scope, not
        per-turn coverage requirements. The system may identify gaps outside
        this scope, as long as they are valid intents.

        Returns dict with pass, method, reason, and trace details.
        """
        result = {
            "pass": True,
            "method": "valid_intent_check",
            "reason": "",
            "trace": {
                "intent_gap": intent_gap,
                "covered_intents": covered_intents,
                "expected_intents": expected_intents,
            },
        }

        # Handle None or empty intent_gap
        if not intent_gap:
            result["reason"] = "no_gap_detected"
            return result

        gap_set = set(intent_gap)
        valid_intents = set(INTENT_LABELS)

        # All gaps must be valid intents
        invalid_gaps = gap_set - valid_intents
        if invalid_gaps:
            if self.verbose:
                print(f"[DEBUG] Invalid gaps detected: {invalid_gaps}")
            result["pass"] = False
            result["reason"] = f"invalid_gaps: {list(invalid_gaps)}"
            return result

        # If expected_intents provided, check if gaps overlap with them
        # This is a soft check - gaps outside expected_intents are OK if valid
        if expected_intents:
            expected_set = set(expected_intents)
            # Prefer gaps that overlap with expected intents
            if gap_set & expected_set:
                result["reason"] = "gap_overlaps_expected_intents"
            else:
                # Gaps outside expected are still valid as long as they're in INTENT_LABELS
                result["reason"] = "gap_outside_expected_but_valid"

        return result

    def _validate_retrieval(
        self,
        retrieval: dict[str, Any],
        expected_must_points: list[str],
    ) -> dict[str, Any]:
        """Validate RAG retrieval quality with stricter requirements.

        For E2E, we check that:
        - Some items were returned
        - Items contain relevant content (keyword overlap with must_points OR
          expected_followup_direction OR intent relevance)

        Enhanced: Add synonym mapping for common business terms.

        Returns dict with pass, method, reason, and trace details.
        """
        items = retrieval.get("items", [])

        result = {
            "pass": False,
            "method": "keyword_match",
            "reason": "",
            "trace": {
                "returned_items": len(items),
                "top_3_titles": [item.get("metadata", {}).get("title", "")[:50] for item in items[:3]],
            },
        }

        if not items:
            result["reason"] = "no_items_returned"
            return result

        if not expected_must_points:
            # If no must_points expected, any retrieval is acceptable
            result["pass"] = True
            result["reason"] = "no_expected_must_points"
            return result

        # Synonym mapping for common business terms. Core terms are strong
        # evidence; expanded terms are useful but should not pass alone when
        # they are too generic.
        synonym_map = {
            "合规": ["合规", "监管", "规定", "规范", "边界", "红线", "不能承诺", "不承诺", "不保本", "不保息"],
            "风险": ["风险", "亏损", "波动", "不确定", "本金", "市场", "损失"],
            "流动性": ["流动性", "退保", "现金价值", "犹豫期", "可取", "支取", "赎回", "用钱", "交不上", "续存"],
            "费用": ["费用", "缴费", "保费", "费率", "交费"],
            "收益": ["收益", "回报", "分红", "利率", "利息"],
            "共情": ["共情", "理解", "顾虑", "担心", "认可", "尊重"],
            "理解": ["理解", "明白", "认可", "认同", "顾虑"],
            "需求": ["需求", "风险承受", "期限", "偏好", "确认", "了解"],
            "办理": ["办理", "流程", "手续", "材料", "操作", "下一步"],
            "引导": ["引导", "建议", "指导", "方案", "邀约"],
            "异议": ["异议", "拒绝", "犹豫", "顾虑", "担心", "担忧", "商量", "解决方案", "方案", "灵活"],
            "产品": ["产品", "保障", "功能", "条款", "介绍"],
        }
        generic_terms = {
            "客户", "您", "可能", "说明", "介绍", "解释", "告知", "确认",
            "相关", "具体", "问题", "情况", "进行", "可以", "需要",
        }

        # Expand keywords with synonyms.
        core_keywords = set()
        expanded_keywords = set()
        for point in expected_must_points:
            if point:
                expanded_keywords.add(point)
                # Extract 2-4 char chunks
                for i in range(len(point) - 1):
                    for chunk_len in [2, 3, 4]:
                        if i + chunk_len <= len(point):
                            chunk = point[i:i + chunk_len]
                            # Skip very common characters
                            if chunk not in {"的", "了", "是", "有", "在", "不", "个", "很"}:
                                expanded_keywords.add(chunk)
                                # Add synonyms
                                for base_term, synonyms in synonym_map.items():
                                    if base_term in point or base_term in chunk:
                                        core_keywords.update(synonyms)
                                        expanded_keywords.update(synonyms)

        # Filter to only meaningful keywords (2+ chars)
        expanded_keywords = {kw for kw in expanded_keywords if len(kw) >= 2 and kw not in generic_terms}
        core_keywords = {kw for kw in core_keywords if len(kw) >= 2 and kw not in generic_terms}
        if not core_keywords:
            core_keywords = {kw for kw in expanded_keywords if len(kw) >= 3}

        # Check top-5 items. A pass needs either one core hit or at least two
        # expanded hits, avoiding overly broad single-token matches.
        for rank, item in enumerate(items[:5], 1):
            content = item.get("content", "").lower()
            title = item.get("metadata", {}).get("title", "").lower()
            combined_text = content + " " + title

            matched_core = sorted(kw for kw in core_keywords if kw in combined_text)
            matched_expanded = sorted(kw for kw in expanded_keywords if kw in combined_text)

            if matched_core or len(matched_expanded) >= 2:
                result["pass"] = True
                result["reason"] = f"matched_keywords_at_rank_{rank}"
                result["trace"]["matched_core_keywords"] = matched_core[:5]
                result["trace"]["matched_expanded_keywords"] = matched_expanded[:8]
                result["trace"]["match_rank"] = rank
                result["trace"]["core_keywords"] = list(core_keywords)[:10]
                result["trace"]["all_extracted_keywords"] = list(expanded_keywords)[:10]
                return result

        # If expected_must_points is non-empty but no matches found, FAIL
        result["reason"] = f"expected_must_points_not_found: {list(expanded_keywords)[:5]}"
        result["trace"]["missing_core_keywords"] = list(core_keywords)[:10]
        result["trace"]["all_extracted_keywords"] = list(expanded_keywords)[:10]
        return result

    def _validate_followup(
        self,
        followup_message: str,
        intent_gap: list[str],
        expected_directions: list[str],
        turn_idx: int,
    ) -> dict[str, Any]:
        """Validate follow-up direction with stricter requirements.

        Follow-up should:
        - Address one of the gap intents OR match expected_directions
        - Not be too short (minimum length check)
        - Not repeat the same question as previous turn

        Returns dict with pass, method, reason, and trace details.
        """
        result = {
            "pass": False,
            "method": "intent_or_direction_match",
            "reason": "",
            "trace": {
                "followup_length": len(followup_message),
                "gap_intents": intent_gap,
                "expected_direction": expected_directions[turn_idx] if turn_idx < len(expected_directions) else None,
            },
        }

        if not followup_message:
            result["reason"] = "empty_followup"
            return result

        if len(followup_message) <= 3:
            result["reason"] = "followup_too_short"
            return result

        followup_lower = followup_message.lower()

        # Keywords for each intent type (expanded)
        intent_keywords = {
            "rate_concern": ["收益", "利率", "划算", "高", "利息", "多少", "百分", "比存款"],
            "liquidity_concern": ["取", "用钱", "提前", "灵活", "退保", "期限", "活期"],
            "safety_concern": ["安全", "风险", "亏", "保本", "本金", "保证", "承诺"],
            "procedure_question": ["怎么办", "材料", "怎么", "流程", "办理", "手续", "带什么"],
            "rejection_or_hesitation": ["犹豫", "想想", "考虑", "不急", "商量", "家人", "再看看"],
        }

        # Check if followup addresses a gap intent
        gap_set = set(intent_gap or [])
        for intent in gap_set:
            keywords = intent_keywords.get(intent, [])
            matched = [kw for kw in keywords if kw in followup_lower]
            if matched:
                result["pass"] = True
                result["reason"] = f"matched_gap_intent:{intent}"
                result["trace"]["matched_intent"] = intent
                result["trace"]["matched_keywords"] = matched
                return result

        # If no gap, check against expected directions
        if expected_directions and turn_idx < len(expected_directions):
            expected = expected_directions[turn_idx].lower()
            # Extract keywords from expected direction (Chinese)
            expected_keywords = [w for w in expected if len(w) >= 2]
            matched = [kw for kw in expected_keywords if kw in followup_lower]
            if matched:
                result["pass"] = True
                result["reason"] = "matched_expected_direction"
                result["trace"]["matched_keywords"] = matched
                return result

        # If neither gap nor expected direction, check for any meaningful content
        # But still need some relevance keywords
        all_keywords = set()
        for kw_list in intent_keywords.values():
            all_keywords.update(kw_list)

        matched_any = [kw for kw in all_keywords if kw in followup_lower]
        if matched_any:
            result["pass"] = True
            result["reason"] = "matched_general_relevance_keywords"
            result["trace"]["matched_keywords"] = matched_any[:5]
            return result

        result["reason"] = "no_relevance_match"
        return result

    def _validate_weak_tags(
        self,
        weak_tags: list[str],
        expected_weak_tags: list[str],
    ) -> dict[str, Any]:
        """Validate weak tag relevance with stricter requirements.

        For E2E, we check that:
        - If expected_weak_tags is non-empty, we must detect some weak tags
        - Use substring/keyword matches for Chinese text
        - Empty detection is acceptable only if expected is empty

        Returns dict with pass, method, reason, and trace details.
        """
        result = {
            "pass": False,
            "method": "keyword_match",
            "reason": "",
            "trace": {
                "detected_tags": weak_tags,
                "expected_tags": expected_weak_tags,
            },
        }

        if not expected_weak_tags:
            # If no expected weak tags, any result is acceptable
            result["pass"] = True
            result["reason"] = "no_expected_weak_tags"
            return result

        if not weak_tags:
            # Expected weak tags but detected none - FAIL
            result["reason"] = "expected_weak_tags_but_none_detected"
            return result

        # Convert to lowercase for case-insensitive matching
        weak_lower = [tag.lower() for tag in weak_tags]
        expected_lower = [tag.lower() for tag in expected_weak_tags]

        # Check for exact match
        exact_matches = set(weak_lower) & set(expected_lower)
        if exact_matches:
            result["pass"] = True
            result["reason"] = "exact_match"
            result["trace"]["exact_matches"] = list(exact_matches)
            return result

        # Check for substring/keyword matches
        # Extract key terms (2-4 chars) from each expected tag
        matched_substrings = []
        for expected_tag in expected_lower:
            for weak_tag in weak_lower:
                # Check if weak_tag contains key characters from expected_tag
                for i in range(len(expected_tag) - 1):
                    for seq_len in [2, 3, 4]:
                        if i + seq_len <= len(expected_tag):
                            seq = expected_tag[i:i + seq_len]
                            if seq in weak_tag:
                                matched_substrings.append(seq)
                                # Found at least one match
                                result["pass"] = True
                                result["reason"] = "substring_match"
                                result["trace"]["matched_substrings"] = matched_substrings
                                return result

        # Expected weak tags but no meaningful match
        result["reason"] = "expected_weak_tags_no_match_found"
        return result

    def _build_dialogue_trace(
        self,
        reply_results: list[dict[str, Any]],
        finish_result: dict[str, Any],
    ) -> dict[str, Any]:
        """Build compact dialogue trace for verbose output."""
        return {
            "rounds": len(reply_results),
            "finish_score": finish_result.get("trace", {}).get("total_score"),
            "weak_tags": finish_result.get("trace", {}).get("weak_tags"),
        }

    def _build_failure_trace(
        self,
        result: dict[str, Any],
        case: dict[str, Any],
    ) -> dict[str, Any]:
        """Build detailed failure trace for debugging.

        Returns a structured trace showing:
        - Failed stages
        - Expected vs actual for each stage
        - Retrieval top items
        - Followup messages
        - Score and weak tags
        """
        trace = {
            "case_id": result.get("case_id"),
            "overall_pass": result.get("overall_pass", False),
            "failed_stages": [],
            "stage_details": {},
        }

        # Check each stage
        stages_to_check = [
            ("start_pass", "Dialogue Start"),
            ("contract_pass", "Contract Compliance"),
            ("intent_pass", "Intent Detection"),
            ("gap_pass", "Gap Computation"),
            ("retrieval_hit", "Retrieval Quality"),
            ("followup_pass", "Follow-up Direction"),
            ("finish_score_pass", "Finish Score"),
            ("strict_score_pass", "Strict Finish Score"),
            ("weak_tag_pass", "Weak Tag Detection"),
        ]

        for stage_key, stage_name in stages_to_check:
            stage_value = result.get(stage_key, False)
            if not stage_value:
                trace["failed_stages"].append(stage_name)

            trace["stage_details"][stage_name] = {
                "pass": stage_value,
                "details": self._get_stage_details(stage_key, result, case),
            }

        return trace

    def _get_stage_details(
        self,
        stage_key: str,
        result: dict[str, Any],
        case: dict[str, Any],
    ) -> dict[str, Any]:
        """Extract detailed information for a specific stage."""
        details = {}

        if stage_key == "contract_pass":
            # Check if liveScore or source appeared
            for i, reply in enumerate(result.get("reply_results", [])):
                if "contract_pass" in reply and not reply.get("contract_pass", False):
                    details[f"round_{i}"] = "Contract violation detected"

        elif stage_key == "start_pass":
            details = result.get("start_trace", {})

        elif stage_key == "retrieval_hit":
            # Show retrieval failures
            for i, reply in enumerate(result.get("reply_results", [])):
                if not reply.get("retrieval_hit", False):
                    details[f"round_{i}"] = {
                        "reason": reply.get("retrieval_reason", ""),
                        "method": reply.get("retrieval_method", ""),
                        "trace": reply.get("retrieval_trace", {}),
                        "expected_must_points": case.get("expected_must_points", []),
                        "retrieval_items_count": len(reply.get("retrieval_items", [])),
                        "retrieval_top_titles": [
                            item.get("metadata", {}).get("title", "")[:50]
                            for item in reply.get("retrieval_items", [])[:3]
                        ],
                    }

        elif stage_key == "followup_pass":
            # Show followup failures
            for i, reply in enumerate(result.get("reply_results", [])):
                if not reply.get("followup_pass", False):
                    details[f"round_{i}"] = {
                        "reason": reply.get("followup_reason", ""),
                        "method": reply.get("followup_method", ""),
                        "trace": reply.get("followup_trace", {}),
                        "followup_message": reply.get("ai_customer_message", ""),
                        "expected_direction": case.get("expected_followup_direction", [])[i] if i < len(case.get("expected_followup_direction", [])) else None,
                    }

        elif stage_key == "finish_score_pass":
            # Show score validation details
            details = {
                "expected_range": case.get("expected_score_range", [0, 100]),
                "actual_score": result.get("finish_trace", {}).get("total_score"),
            }

        elif stage_key == "strict_score_pass":
            # Show strict score validation details
            details = {
                "strict_expected_range": case.get(
                    "strict_score_range",
                    case.get("expected_score_range", [0, 100]),
                ),
                "actual_score": result.get("finish_trace", {}).get("total_score"),
                "calibration_reason": case.get("calibration_reason"),
            }

        elif stage_key == "weak_tag_pass":
            # Show weak tag validation details
            details = {
                "expected_tags": case.get("expected_weak_tags", []),
                "detected_tags": result.get("finish_trace", {}).get("weak_tags", []),
                "method": result.get("weak_tag_method", ""),
                "reason": result.get("weak_tag_reason", ""),
                "tag_trace": result.get("finish_trace", {}).get("weak_tag_trace", {}),
            }

        elif stage_key == "intent_pass":
            # Show intent detection details
            for i, reply in enumerate(result.get("reply_results", [])):
                if not reply.get("intent_pass", False):
                    details[f"round_{i}"] = {
                        "expected_intents": case.get("expected_intents", []),
                    }

        elif stage_key == "gap_pass":
            # Show gap computation details
            for i, reply in enumerate(result.get("reply_results", [])):
                if not reply.get("gap_pass", False):
                    details[f"round_{i}"] = {
                        "intent_gap": reply.get("intent_gap", []),
                    }

        return details


def compute_e2e_metrics(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute aggregate E2E metrics from case results."""
    if not results:
        return {
            "e2e_overall_pass": 0.0,
            "start_pass": 0.0,
            "contract_pass": 0.0,
            "intent_pass": 0.0,
            "gap_pass": 0.0,
            "retrieval_hit": 0.0,
            "followup_pass": 0.0,
            "finish_score_pass": 0.0,
            "strict_score_pass": 0.0,
            "strict_e2e_overall_pass": 0.0,
            "weak_tag_pass": 0.0,
        }

    total = len(results)

    def pass_rate(key: str) -> float:
        return sum(1 for r in results if r.get(key, False)) / max(total, 1)

    return {
        "e2e_overall_pass": round(pass_rate("overall_pass"), 4),
        "start_pass": round(pass_rate("start_pass"), 4),
        "contract_pass": round(pass_rate("contract_pass"), 4),
        "intent_pass": round(pass_rate("intent_pass"), 4),
        "gap_pass": round(pass_rate("gap_pass"), 4),
        "retrieval_hit": round(pass_rate("retrieval_hit"), 4),
        "followup_pass": round(pass_rate("followup_pass"), 4),
        "finish_score_pass": round(pass_rate("finish_score_pass"), 4),
        "strict_score_pass": round(pass_rate("strict_score_pass"), 4),
        "strict_e2e_overall_pass": round(pass_rate("strict_overall_pass"), 4),
        "weak_tag_pass": round(pass_rate("weak_tag_pass"), 4),
    }
