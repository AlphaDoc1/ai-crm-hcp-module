"""
app/agent/tools.py
─────────────────────────────────────────────────────────────────────────────
Defines all 5 LangGraph tools for the HCP Interaction Agent.

Tool registry:
  1. log_interaction      — extract + save new interaction via LLM
  2. edit_interaction     — update an existing interaction record
  3. search_hcp           — fuzzy-search HCPs by name, return history
  4. suggest_followups    — LLM-generated follow-up chips, saved to DB
  5. summarize_interaction — live structured preview, NOT saved to DB

Each tool:
  - Is decorated with @tool (LangChain standard)
  - Handles its own DB session lifecycle (open → use → close)
  - Handles LLM JSON parsing failures gracefully via _safe_parse_json()
  - Returns a dict payload that surfaces in AgentState.tool_result
─────────────────────────────────────────────────────────────────────────────
"""

import json
import re
import logging
from datetime import date, time as time_type
from typing import Optional

from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models import HCP, Interaction, FollowUp, SentimentEnum, InteractionTypeEnum, FollowUpStatusEnum
from app.agent.prompts import (
    LOG_INTERACTION_EXTRACTION_PROMPT,
    SUGGEST_FOLLOWUPS_PROMPT,
    SUMMARIZE_INTERACTION_PROMPT,
)

logger = logging.getLogger(__name__)
settings = get_settings()


# ─────────────────────────────────────────────────────────────────────────────
# LLM factory helpers
# ─────────────────────────────────────────────────────────────────────────────

def _get_primary_llm() -> ChatGroq:
    """
    Return a ChatGroq instance for entity-extraction tasks (openai/gpt-oss-20b).

    reasoning_effort="medium" via model_kwargs: extraction tasks (log_interaction,
    suggest_followups, summarize_interaction) benefit from a bit more reasoning to
    correctly identify pharma entities and produce clean JSON. "medium" balances
    accuracy with reasonable latency.

    NOTE: reasoning_effort is passed via model_kwargs because langchain_groq 0.2.x
    does not expose it as a direct ChatGroq constructor kwarg.
    """
    return ChatGroq(
        model=settings.primary_model,       # "openai/gpt-oss-20b"
        api_key=settings.groq_api_key,
        temperature=1,                      # reasoning models require temperature=1
        max_tokens=4096,
        model_kwargs={"reasoning_effort": "medium"},  # via model_kwargs
    )


def _get_fallback_llm() -> ChatGroq:
    """
    Return a ChatGroq instance using the fallback model (openai/gpt-oss-120b).
    Larger model used when primary fails — also uses reasoning_effort=medium.
    """
    return ChatGroq(
        model=settings.fallback_model,      # "openai/gpt-oss-120b"
        api_key=settings.groq_api_key,
        temperature=1,                      # reasoning models require temperature=1
        max_tokens=4096,
        model_kwargs={"reasoning_effort": "medium"},  # via model_kwargs
    )


def _invoke_llm_with_fallback(messages: list, context: str = "") -> str:
    """
    Try the primary model first; if it fails or returns empty content,
    fall back to openai/gpt-oss-120b. Returns the raw string content.

    FIX 3 — Content verification:
    openai/gpt-oss-20b/120b are reasoning models. Per Groq's API docs, the
    reasoning tokens appear in a separate `reasoning` field on the response,
    NOT embedded in `content`. So response.content should contain only the
    final answer. We log it at DEBUG level so it can be visually verified
    that no <think>...</think> or reasoning text leaks into the JSON parsing.
    The _safe_parse_json() fallback logic is unchanged and handles any edge
    cases where the model unexpectedly wraps output in markdown fences.
    """
    try:
        llm = _get_primary_llm()
        response = llm.invoke(messages)
        content = response.content.strip()

        # FIX 3 — Log raw content so we can verify no reasoning text leaks in
        logger.debug(
            f"[LLM] raw response.content for context='{context}' "
            f"(first 500 chars): {content[:500]!r}"
        )

        if not content:
            raise ValueError("Primary LLM returned empty response")
        logger.info(f"[LLM] Primary model responded for: {context}")
        return content
    except Exception as primary_err:
        logger.warning(f"[LLM] Primary model failed ({primary_err}), using fallback for: {context}")
        try:
            llm = _get_fallback_llm()
            response = llm.invoke(messages)
            content = response.content.strip()
            # Also log fallback content for the same verification purpose
            logger.debug(
                f"[LLM] fallback raw response.content for context='{context}' "
                f"(first 500 chars): {content[:500]!r}"
            )
            return content
        except Exception as fallback_err:
            logger.error(f"[LLM] Both models failed: {fallback_err}")
            raise RuntimeError(f"Both primary and fallback LLMs failed. Last error: {fallback_err}")


# ─────────────────────────────────────────────────────────────────────────────
# JSON parsing helper — gracefully handles dirty LLM output
# ─────────────────────────────────────────────────────────────────────────────

def _safe_parse_json(raw: str, context: str = "unknown") -> Optional[dict | list]:
    """
    Attempt to parse LLM output as JSON. Groq models sometimes wrap JSON
    in markdown code fences or add explanatory text.
    This function tries multiple strategies before giving up.

    Strategy 1: Direct json.loads() on the raw string.
    Strategy 2: Strip ```json ... ``` or ``` ... ``` markdown fences.
    Strategy 3: Regex extraction of the first {...} or [...] block found.
    Strategy 4: Return None if all strategies fail (caller handles gracefully).
    """
    if not raw:
        return None

    # Strategy 1 — direct parse
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Strategy 2 — strip markdown code fences
    cleaned = re.sub(r"```(?:json)?\s*", "", raw).replace("```", "").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Strategy 3 — extract first JSON object {...} or array [...]
    obj_match = re.search(r"\{[\s\S]*\}", cleaned)
    arr_match = re.search(r"\[[\s\S]*\]", cleaned)

    # Prefer whichever appears first
    candidates = []
    if obj_match:
        candidates.append((obj_match.start(), obj_match.group()))
    if arr_match:
        candidates.append((arr_match.start(), arr_match.group()))
    candidates.sort(key=lambda x: x[0])

    for _, candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            continue

    logger.warning(f"[JSON] _safe_parse_json failed for context='{context}'. Raw (first 300 chars): {raw[:300]}")
    return None


# ─────────────────────────────────────────────────────────────────────────────
# DB helper — resolve HCP by name (fuzzy ILIKE search)
# ─────────────────────────────────────────────────────────────────────────────

def _find_hcp_by_name(db: Session, name: str) -> Optional[HCP]:
    """
    Search for an HCP whose name contains `name` (case-insensitive).
    Returns the first match, or None.
    """
    return (
        db.query(HCP)
        .filter(HCP.name.ilike(f"%{name}%"))
        .first()
    )


def _serialize_interaction(interaction: Interaction, hcp: Optional[HCP] = None) -> dict:
    """Convert an Interaction ORM object to a JSON-safe dict."""
    return {
        "id": interaction.id,
        "hcp_id": interaction.hcp_id,
        "hcp_name": hcp.name if hcp else None,
        "interaction_type": interaction.interaction_type.value if interaction.interaction_type else None,
        "date": interaction.date.isoformat() if interaction.date else None,
        "time": interaction.time.strftime("%H:%M") if interaction.time else None,
        "attendees": interaction.attendees,
        "topics_discussed": interaction.topics_discussed,
        "materials_shared": interaction.materials_shared or [],
        "samples_distributed": interaction.samples_distributed or [],
        "sentiment": interaction.sentiment.value if interaction.sentiment else None,
        "outcomes": interaction.outcomes,
        "follow_up_actions": interaction.follow_up_actions,
        "created_at": interaction.created_at.isoformat() if interaction.created_at else None,
        "updated_at": interaction.updated_at.isoformat() if interaction.updated_at else None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# TOOL 1 — log_interaction
# ─────────────────────────────────────────────────────────────────────────────

@tool
def log_interaction(user_message: str) -> dict:
    """
    Log a new HCP interaction from free-text or structured input.

    How it works:
    1. The raw `user_message` (e.g. "Met Dr. Sharma today at Apollo, discussed
       OncoBoost Phase III data, positive sentiment, shared brochure") is sent
       to openai/gpt-oss-20b via Groq with an entity-extraction prompt.
    2. The LLM returns a JSON object with fields: hcp_name, interaction_type,
       date, time, attendees, topics_discussed, materials_shared (array),
       samples_distributed (array), sentiment, outcomes, follow_up_actions.
    3. The extracted hcp_name is used to look up the HCP in the database via
       fuzzy ILIKE search. If not found, a new HCP record is created.
    4. A new Interaction record is inserted and committed to PostgreSQL.
    5. Returns a structured dict with the saved interaction data.

    JSON parsing failures are handled gracefully — if the LLM returns malformed
    JSON, _safe_parse_json() applies multiple recovery strategies. If all fail,
    a partial record with the raw text in topics_discussed is saved.

    Args:
        user_message: Free-text description of the HCP interaction.

    Returns:
        dict with keys: success, interaction_id, extracted_data, message
    """
    db = SessionLocal()
    try:
        # ── Step 1: LLM entity extraction ────────────────────────────────────
        prompt = LOG_INTERACTION_EXTRACTION_PROMPT.format(user_text=user_message)
        messages = [HumanMessage(content=prompt)]
        raw_llm_output = _invoke_llm_with_fallback(messages, context="log_interaction")

        extracted = _safe_parse_json(raw_llm_output, context="log_interaction")

        if not extracted or not isinstance(extracted, dict):
            logger.warning("[log_interaction] JSON parsing failed — using fallback minimal record")
            extracted = {
                "hcp_name": None,
                "interaction_type": "Meeting",
                "date": None,
                "time": None,
                "attendees": "",
                "topics_discussed": user_message,
                "materials_shared": [],
                "samples_distributed": [],
                "sentiment": "neutral",
                "outcomes": "",
                "follow_up_actions": "",
            }

        # ── Step 2: Resolve or create HCP ────────────────────────────────────
        hcp_name = extracted.get("hcp_name") or ""
        hcp = None
        if hcp_name:
            hcp = _find_hcp_by_name(db, hcp_name)
            if not hcp:
                # Auto-create a minimal HCP record so the interaction can be saved
                hcp = HCP(name=hcp_name, specialty="Unknown", hospital="Unknown")
                db.add(hcp)
                db.flush()   # get ID without committing

        if not hcp:
            # Last resort — create a placeholder HCP
            hcp = HCP(name="Unknown HCP", specialty="Unknown", hospital="Unknown")
            db.add(hcp)
            db.flush()

        # ── Step 3: Parse enum values safely ─────────────────────────────────
        raw_type = extracted.get("interaction_type", "Meeting")
        try:
            interaction_type = InteractionTypeEnum(raw_type)
        except ValueError:
            interaction_type = InteractionTypeEnum.meeting

        raw_sentiment = extracted.get("sentiment", "neutral")
        try:
            sentiment = SentimentEnum(raw_sentiment.lower() if raw_sentiment else "neutral")
        except ValueError:
            sentiment = SentimentEnum.neutral

        # ── Step 4: Parse date/time ───────────────────────────────────────────
        parsed_date = None
        raw_date = extracted.get("date")
        if raw_date:
            try:
                parsed_date = date.fromisoformat(raw_date)
            except (ValueError, TypeError):
                parsed_date = None

        parsed_time = None
        raw_time = extracted.get("time")
        if raw_time:
            try:
                parts = raw_time.split(":")
                parsed_time = time_type(int(parts[0]), int(parts[1]))
            except (ValueError, TypeError, IndexError):
                parsed_time = None

        # ── Step 5: Build and save the Interaction record ─────────────────────
        materials = extracted.get("materials_shared") or []
        if not isinstance(materials, list):
            materials = []

        samples = extracted.get("samples_distributed") or []
        if not isinstance(samples, list):
            samples = []

        interaction = Interaction(
            hcp_id=hcp.id,
            interaction_type=interaction_type,
            date=parsed_date,
            time=parsed_time,
            attendees=extracted.get("attendees", ""),
            topics_discussed=extracted.get("topics_discussed", user_message),
            materials_shared=materials,
            samples_distributed=samples,
            sentiment=sentiment,
            outcomes=extracted.get("outcomes", ""),
            follow_up_actions=extracted.get("follow_up_actions", ""),
        )
        db.add(interaction)
        db.commit()
        db.refresh(interaction)

        result = _serialize_interaction(interaction, hcp)
        logger.info(f"[log_interaction] Saved interaction id={interaction.id} for HCP '{hcp.name}'")

        return {
            "success": True,
            "interaction_id": interaction.id,
            "extracted_data": extracted,
            "saved_interaction": result,
            "message": f"Interaction logged successfully (ID: {interaction.id}) for {hcp.name}.",
        }

    except Exception as e:
        db.rollback()
        logger.error(f"[log_interaction] Error: {e}", exc_info=True)
        return {"success": False, "error": str(e), "message": f"Failed to log interaction: {e}"}
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# TOOL 2 — edit_interaction
# ─────────────────────────────────────────────────────────────────────────────

@tool
def edit_interaction(interaction_id: int, updates: str) -> dict:
    """
    Edit an existing HCP interaction record.

    How it works:
    1. Validates that the interaction with `interaction_id` exists in the DB.
       Returns an error dict if not found.
    2. Parses `updates` as a JSON string (or dict-like string) containing
       only the fields to change. Supported fields: interaction_type, date,
       time, attendees, topics_discussed, materials_shared, samples_distributed,
       sentiment, outcomes, follow_up_actions.
    3. Applies only the provided fields — unchanged fields are left as-is.
    4. Commits the update and returns the full updated record.

    Args:
        interaction_id: Integer ID of the interaction to edit.
        updates: JSON string of field-value pairs to update.
                 Example: '{"sentiment": "positive", "outcomes": "Dr agreed to prescribe"}'

    Returns:
        dict with keys: success, interaction_id, updated_fields, saved_interaction, message
    """
    db = SessionLocal()
    try:
        # ── Step 1: Validate existence ────────────────────────────────────────
        interaction = db.query(Interaction).filter(Interaction.id == interaction_id).first()
        if not interaction:
            return {
                "success": False,
                "error": f"Interaction with id={interaction_id} not found.",
                "message": f"No interaction found with ID {interaction_id}. Use search_hcp to find valid IDs.",
            }

        # ── Step 2: Parse update payload ─────────────────────────────────────
        updates_dict = _safe_parse_json(updates, context="edit_interaction")
        if not updates_dict or not isinstance(updates_dict, dict):
            # Try direct eval as last resort (safe for simple dicts)
            return {
                "success": False,
                "error": "Invalid updates format — expected a JSON string.",
                "message": "Please pass updates as a JSON string, e.g. '{\"sentiment\": \"positive\"}'",
            }

        updated_fields = []

        # ── Step 3: Apply each allowed field update ───────────────────────────
        if "interaction_type" in updates_dict:
            try:
                interaction.interaction_type = InteractionTypeEnum(updates_dict["interaction_type"])
                updated_fields.append("interaction_type")
            except ValueError:
                pass

        if "date" in updates_dict and updates_dict["date"]:
            try:
                interaction.date = date.fromisoformat(updates_dict["date"])
                updated_fields.append("date")
            except (ValueError, TypeError):
                pass

        if "time" in updates_dict and updates_dict["time"]:
            try:
                parts = updates_dict["time"].split(":")
                interaction.time = time_type(int(parts[0]), int(parts[1]))
                updated_fields.append("time")
            except (ValueError, TypeError, IndexError):
                pass

        if "attendees" in updates_dict:
            interaction.attendees = updates_dict["attendees"]
            updated_fields.append("attendees")

        if "topics_discussed" in updates_dict:
            interaction.topics_discussed = updates_dict["topics_discussed"]
            updated_fields.append("topics_discussed")

        if "materials_shared" in updates_dict:
            val = updates_dict["materials_shared"]
            interaction.materials_shared = val if isinstance(val, list) else []
            updated_fields.append("materials_shared")

        if "samples_distributed" in updates_dict:
            val = updates_dict["samples_distributed"]
            interaction.samples_distributed = val if isinstance(val, list) else []
            updated_fields.append("samples_distributed")

        if "sentiment" in updates_dict:
            try:
                interaction.sentiment = SentimentEnum(updates_dict["sentiment"].lower())
                updated_fields.append("sentiment")
            except (ValueError, AttributeError):
                pass

        if "outcomes" in updates_dict:
            interaction.outcomes = updates_dict["outcomes"]
            updated_fields.append("outcomes")

        if "follow_up_actions" in updates_dict:
            interaction.follow_up_actions = updates_dict["follow_up_actions"]
            updated_fields.append("follow_up_actions")

        # ── Step 4: Commit ────────────────────────────────────────────────────
        db.commit()
        db.refresh(interaction)
        hcp = db.query(HCP).filter(HCP.id == interaction.hcp_id).first()

        result = _serialize_interaction(interaction, hcp)
        logger.info(f"[edit_interaction] Updated interaction id={interaction_id}, fields={updated_fields}")

        return {
            "success": True,
            "interaction_id": interaction_id,
            "updated_fields": updated_fields,
            "saved_interaction": result,
            "message": f"Interaction {interaction_id} updated successfully. Fields changed: {', '.join(updated_fields)}.",
        }

    except Exception as e:
        db.rollback()
        logger.error(f"[edit_interaction] Error: {e}", exc_info=True)
        return {"success": False, "error": str(e), "message": f"Failed to edit interaction {interaction_id}: {e}"}
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# TOOL 3 — search_hcp
# ─────────────────────────────────────────────────────────────────────────────

@tool
def search_hcp(query: str, limit: int = 10) -> dict:
    """
    Fuzzy-search Healthcare Professionals (HCPs) by name.

    Supports the 'Search or select HCP' dropdown on the Log Interaction form.
    Returns each matched HCP along with a summary of their past interactions.

    How it works:
    - Performs a case-insensitive PostgreSQL ILIKE search on hcps.name
      using the pattern %query% (contains match).
    - For each matched HCP, fetches their most recent 5 interactions.
    - Returns structured data suitable for populating a UI dropdown.

    Args:
        query: Search term (partial or full HCP name, e.g. "Sharma", "Dr. Priya")
        limit: Maximum number of HCPs to return (default 10)

    Returns:
        dict with keys: success, count, hcps (list of HCP + interaction history)
    """
    db = SessionLocal()
    try:
        hcps = (
            db.query(HCP)
            .filter(HCP.name.ilike(f"%{query}%"))
            .order_by(HCP.name)
            .limit(limit)
            .all()
        )

        results = []
        for hcp in hcps:
            # Fetch most recent 5 interactions for this HCP
            recent_interactions = (
                db.query(Interaction)
                .filter(Interaction.hcp_id == hcp.id)
                .order_by(Interaction.created_at.desc())
                .limit(5)
                .all()
            )

            interaction_summaries = []
            for intr in recent_interactions:
                interaction_summaries.append({
                    "id": intr.id,
                    "type": intr.interaction_type.value if intr.interaction_type else None,
                    "date": intr.date.isoformat() if intr.date else None,
                    "sentiment": intr.sentiment.value if intr.sentiment else None,
                    "topics_snippet": (intr.topics_discussed or "")[:120] + "..."
                    if intr.topics_discussed and len(intr.topics_discussed) > 120
                    else (intr.topics_discussed or ""),
                })

            results.append({
                "id": hcp.id,
                "name": hcp.name,
                "specialty": hcp.specialty,
                "hospital": hcp.hospital,
                "contact_info": hcp.contact_info,
                "interaction_count": len(recent_interactions),
                "recent_interactions": interaction_summaries,
            })

        logger.info(f"[search_hcp] Query='{query}' returned {len(results)} HCPs")
        return {
            "success": True,
            "count": len(results),
            "hcps": results,
            "message": f"Found {len(results)} HCP(s) matching '{query}'.",
        }

    except Exception as e:
        logger.error(f"[search_hcp] Error: {e}", exc_info=True)
        return {"success": False, "error": str(e), "hcps": [], "message": f"Search failed: {e}"}
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# TOOL 4 — suggest_followups
# ─────────────────────────────────────────────────────────────────────────────

@tool
def suggest_followups(interaction_id: int) -> dict:
    """
    Generate 2-3 AI-powered follow-up suggestions for a specific interaction.

    How it works:
    1. Fetches the interaction + associated HCP from the database.
    2. Builds a context-rich prompt (HCP specialty, hospital, interaction type,
       topics discussed, materials shared, samples, sentiment, outcomes).
    3. Calls openai/gpt-oss-20b (with openai/gpt-oss-120b as fallback) to generate
       2-3 pharma-specific, actionable follow-up suggestions.
    4. Parses the LLM JSON array response (with _safe_parse_json fallback).
    5. Saves each suggestion as a FollowUp record (status=pending) in the DB.
    6. Returns the suggestions as a list — powers the "AI Suggested Follow-ups"
       chips in the UI.

    Args:
        interaction_id: Integer ID of the interaction to generate follow-ups for.

    Returns:
        dict with keys: success, interaction_id, suggestions (list of strings),
                        saved_followup_ids, message
    """
    db = SessionLocal()
    try:
        # ── Fetch interaction + HCP ───────────────────────────────────────────
        interaction = db.query(Interaction).filter(Interaction.id == interaction_id).first()
        if not interaction:
            return {
                "success": False,
                "error": f"Interaction id={interaction_id} not found.",
                "message": f"No interaction found with ID {interaction_id}.",
                "suggestions": [],
            }

        hcp = db.query(HCP).filter(HCP.id == interaction.hcp_id).first()

        # ── Build prompt ──────────────────────────────────────────────────────
        materials_text = json.dumps(interaction.materials_shared or [])
        samples_text = json.dumps(interaction.samples_distributed or [])

        prompt = SUGGEST_FOLLOWUPS_PROMPT.format(
            hcp_name=hcp.name if hcp else "Unknown HCP",
            specialty=hcp.specialty if hcp else "Unknown",
            hospital=hcp.hospital if hcp else "Unknown",
            interaction_type=interaction.interaction_type.value if interaction.interaction_type else "Meeting",
            interaction_date=interaction.date.isoformat() if interaction.date else "Not specified",
            topics_discussed=interaction.topics_discussed or "Not specified",
            materials_shared=materials_text,
            samples_distributed=samples_text,
            sentiment=interaction.sentiment.value if interaction.sentiment else "neutral",
            outcomes=interaction.outcomes or "None noted",
            follow_up_actions=interaction.follow_up_actions or "None specified",
        )

        messages = [HumanMessage(content=prompt)]
        raw_output = _invoke_llm_with_fallback(messages, context="suggest_followups")

        # ── Parse suggestions ─────────────────────────────────────────────────
        suggestions = _safe_parse_json(raw_output, context="suggest_followups")

        if not suggestions or not isinstance(suggestions, list):
            # Fallback: split by newline or numbered list if JSON fails
            lines = [
                re.sub(r"^[\d\.\-\*\+]+\s*", "", ln).strip()
                for ln in raw_output.split("\n")
                if ln.strip() and len(ln.strip()) > 10
            ]
            suggestions = lines[:3] if lines else [
                f"Schedule follow-up meeting with {hcp.name if hcp else 'HCP'} in 2 weeks",
                "Send relevant clinical data PDF via email",
                "Register HCP for upcoming advisory board or webinar",
            ]

        # Ensure max 3 suggestions
        suggestions = [str(s).strip() for s in suggestions if s][:3]

        # ── Save to follow_ups table ──────────────────────────────────────────
        saved_ids = []
        for suggestion_text in suggestions:
            followup = FollowUp(
                interaction_id=interaction_id,
                suggested_action=suggestion_text,
                status=FollowUpStatusEnum.pending,
            )
            db.add(followup)
            db.flush()
            saved_ids.append(followup.id)

        db.commit()
        logger.info(f"[suggest_followups] Generated {len(suggestions)} follow-ups for interaction={interaction_id}")

        return {
            "success": True,
            "interaction_id": interaction_id,
            "suggestions": suggestions,
            "saved_followup_ids": saved_ids,
            "message": f"Generated {len(suggestions)} follow-up suggestions for interaction {interaction_id}.",
        }

    except Exception as e:
        db.rollback()
        logger.error(f"[suggest_followups] Error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "suggestions": [],
            "message": f"Failed to generate follow-ups: {e}",
        }
    finally:
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# TOOL 5 — summarize_interaction
# ─────────────────────────────────────────────────────────────────────────────

@tool
def summarize_interaction(raw_text: str) -> dict:
    """
    Generate a structured JSON summary of raw interaction notes WITHOUT saving to DB.

    Powers the live AI Assistant chat preview in the right panel — allows the
    field rep to see a structured extraction before committing to save.

    How it works:
    1. Takes any raw text (free-form field notes, voice-note transcript, etc.)
    2. Sends it to openai/gpt-oss-20b with a structured summary prompt.
    3. The LLM returns JSON with: hcp_name, interaction_type, sentiment,
       topics_summary, key_products_mentioned, materials/samples counts,
       outcomes_summary, suggested_follow_ups, and a confidence score.
    4. _safe_parse_json() handles dirty output gracefully.
    5. Returns the parsed summary dict — NOTHING is written to the database.

    Args:
        raw_text: Raw interaction notes or voice-note transcript text.

    Returns:
        dict with keys: success, summary (structured dict), raw_llm_output, message
    """
    try:
        prompt = SUMMARIZE_INTERACTION_PROMPT.format(raw_text=raw_text)
        messages = [HumanMessage(content=prompt)]
        raw_output = _invoke_llm_with_fallback(messages, context="summarize_interaction")

        summary = _safe_parse_json(raw_output, context="summarize_interaction")

        if not summary or not isinstance(summary, dict):
            logger.warning("[summarize_interaction] JSON parsing failed — returning raw text wrapper")
            summary = {
                "hcp_name": "Could not extract",
                "interaction_type": "Unknown",
                "sentiment": "neutral",
                "topics_summary": raw_text[:500],
                "key_products_mentioned": [],
                "materials_shared_count": 0,
                "samples_distributed_count": 0,
                "outcomes_summary": "Could not extract structured outcomes.",
                "suggested_follow_ups": [],
                "confidence": "low",
            }

        logger.info("[summarize_interaction] Summary generated (not saved)")
        return {
            "success": True,
            "summary": summary,
            "raw_llm_output": raw_output,
            "message": "Interaction summarized (preview only — not saved to database).",
        }

    except Exception as e:
        logger.error(f"[summarize_interaction] Error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "summary": None,
            "message": f"Summarization failed: {e}",
        }


# ─────────────────────────────────────────────────────────────────────────────
# Tool registry — imported by graph.py to bind to the LLM
# ─────────────────────────────────────────────────────────────────────────────

ALL_TOOLS = [
    log_interaction,
    edit_interaction,
    search_hcp,
    suggest_followups,
    summarize_interaction,
]
