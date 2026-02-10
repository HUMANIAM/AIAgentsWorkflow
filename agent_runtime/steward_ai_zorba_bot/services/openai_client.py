#!/usr/bin/env python3
"""OpenAI GPT client for idea brainstorming and context generation."""

import os
import json
import re
import logging
from pathlib import Path
from typing import Dict, List, Tuple
from dotenv import load_dotenv
from openai import OpenAI

from services.runtime_paths import (
    resolve_agent_runtime_dir,
    resolve_project_root,
    slugify,
    utc_today,
)

logger = logging.getLogger(__name__)

# Load .env from bot directory
env_file = Path(__file__).parent.parent / ".env"
load_dotenv(env_file)


PROJECT_ROOT = resolve_project_root()


def get_client():
    """Get OpenAI client with API key from .env"""
    api_key = os.getenv('AI_API_KEY', '').strip()
    if not api_key:
        raise ValueError("AI_API_KEY not found in .env")
    return OpenAI(api_key=api_key)


def _strip_code_fence(text: str) -> str:
    """Remove optional markdown code fences around JSON."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _resolve_agent_runtime_dir() -> Path:
    return resolve_agent_runtime_dir(PROJECT_ROOT)


def _context_template_path() -> Path:
    return _resolve_agent_runtime_dir() / "plugin" / "context_template.md"


def _split_front_matter(text: str) -> Tuple[Dict[str, str], str]:
    cleaned = _strip_code_fence(text)
    if not cleaned.startswith("---"):
        return {}, cleaned
    parts = cleaned.split("\n---", 1)
    if len(parts) != 2:
        return {}, cleaned

    front_raw = parts[0]
    body = parts[1].lstrip("\n")
    front: Dict[str, str] = {}
    for line in front_raw.splitlines()[1:]:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        front[key.strip()] = value.strip()
    return front, body


def _serialize_front_matter(front: Dict[str, str], body: str) -> str:
    preferred = ["plugin", "version", "owner", "last_updated", "idea_id"]
    lines = ["---"]
    used = set()
    for key in preferred:
        if key in front:
            lines.append(f"{key}: {front[key]}")
            used.add(key)
    for key, value in front.items():
        if key in used:
            continue
        lines.append(f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines) + "\n\n" + body.lstrip()


def _normalize_context_markdown(text: str, plugin_name: str = "idea", idea_id: str = "") -> str:
    """
    Normalize model-generated context markdown:
    - strip code fences
    - ensure YAML front matter exists
    - force last_updated to today's UTC date
    """
    cleaned = _strip_code_fence(text)
    today = utc_today()

    # Ensure reasonable default plugin slug
    slug = slugify(plugin_name or "idea") or "idea"

    if cleaned.startswith("---"):
        parts = cleaned.split("\n---", 1)
        if len(parts) == 2:
            front_raw = parts[0]
            body = parts[1].lstrip("\n")
            lines = [ln for ln in front_raw.splitlines()[1:] if ln.strip()]

            # Remove existing last_updated lines and add canonical date.
            kept = [ln for ln in lines if not ln.strip().lower().startswith("last_updated:")]

            has_plugin = any(ln.strip().lower().startswith("plugin:") for ln in kept)
            has_version = any(ln.strip().lower().startswith("version:") for ln in kept)
            has_owner = any(ln.strip().lower().startswith("owner:") for ln in kept)
            has_idea_id = any(ln.strip().lower().startswith("idea_id:") for ln in kept)
            if not has_plugin:
                kept.insert(0, f"plugin: {slug}")
            if not has_version:
                kept.append("version: 1")
            if not has_owner:
                kept.append("owner: client")
            if idea_id and not has_idea_id:
                kept.append(f"idea_id: {idea_id}")
            kept.append(f"last_updated: {today}")

            front = "---\n" + "\n".join(kept) + "\n---\n"
            return front + body.lstrip()

    # No usable front matter: create one.
    idea_line = f"idea_id: {idea_id}\n" if idea_id else ""
    front = (
        "---\n"
        f"plugin: {slug}\n"
        "version: 1\n"
        "owner: client\n"
        f"{idea_line}"
        f"last_updated: {today}\n"
        "---\n\n"
    )
    return front + cleaned.lstrip()


def _load_context_template() -> str:
    path = _context_template_path()
    if not path.exists():
        raise FileNotFoundError(f"Missing context template: {path}")
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        raise ValueError(f"Context template is empty: {path}")
    return text


def _parse_template_contract(template: str) -> Tuple[Dict[str, str], List[str]]:
    front, body = _split_front_matter(template)
    if not front:
        raise ValueError("Context template must include YAML front matter.")

    required_headings = [
        line.strip()
        for line in body.splitlines()
        if line.strip().startswith("#")
    ]
    if not required_headings:
        raise ValueError("Context template must include markdown headings.")
    return front, required_headings


def _validate_heading_order(body: str, required_headings: List[str]) -> None:
    body_headings = [line.strip() for line in body.splitlines() if line.strip().startswith("#")]
    cursor = 0
    for heading in required_headings:
        found = False
        while cursor < len(body_headings):
            if body_headings[cursor] == heading:
                found = True
                cursor += 1
                break
            cursor += 1
        if not found:
            raise ValueError(f"Generated context missing required heading: {heading}")


def _apply_template_contract(generated: str, template: str, idea_id: str) -> str:
    template_front, required_headings = _parse_template_contract(template)
    front, body = _split_front_matter(generated)

    if not body.strip():
        raise ValueError("Generated context body is empty.")

    today = utc_today()
    normalized_front = dict(template_front)
    normalized_front.update(front)
    normalized_front["last_updated"] = today
    normalized_front["idea_id"] = idea_id

    plugin = normalized_front.get("plugin", "").strip()
    if not plugin or "<" in plugin or ">" in plugin:
        normalized_front["plugin"] = "idea"
    if not normalized_front.get("version", "").strip():
        normalized_front["version"] = "1"
    if not normalized_front.get("owner", "").strip():
        normalized_front["owner"] = "client"

    _validate_heading_order(body, required_headings)
    return _serialize_front_matter(normalized_front, body)


def _extract_json_object(text: str) -> dict:
    """Best-effort JSON extraction from model output."""
    cleaned = _strip_code_fence(text)
    try:
        return json.loads(cleaned)
    except Exception:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            return {}
        try:
            return json.loads(match.group(0))
        except Exception:
            return {}


def _normalize_headline(headline: str) -> str:
    """Normalize a generated headline into a readable short title."""
    headline = re.sub(r"\s+", " ", (headline or "").strip()).strip(" .:-")
    if not headline:
        return ""
    words = headline.split(" ")
    if len(words) > 8:
        headline = " ".join(words[:8])
    return headline


def _normalize_idea_id(value: str) -> str:
    """Normalize a candidate idea ID into a safe slug."""
    return slugify(value, max_len=60)


def _fallback_headline_from_history(history: list) -> str:
    """Heuristic readable headline from user conversation."""
    user_texts = [m.get("content", "") for m in history if m.get("role") == "user" and m.get("content")]
    corpus = " ".join(user_texts).lower()

    if ("bookmark" in corpus or "bookmarker" in corpus) and "google sheet" in corpus:
        return "SmartBookmarker for Google Sheets"
    if "bookmark" in corpus or "bookmarker" in corpus:
        return "Smart Bookmark Manager Extension"
    if "browser extension" in corpus:
        return "Browser Extension Idea"

    for text in user_texts:
        cleaned = re.sub(r"[^A-Za-z0-9 ]+", " ", text)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if len(cleaned) < 4:
            continue
        words = cleaned.split(" ")
        if len(words) > 8:
            words = words[:8]
        guess = " ".join(words).strip().title()
        if guess:
            return guess

    return "Untitled Idea"


def _fallback_description(history: list) -> str:
    """Build a one-line summary when model headline JSON is unavailable."""
    for msg in reversed(history):
        if msg.get("role") == "user" and msg.get("content"):
            summary = re.sub(r"\s+", " ", msg["content"]).strip()
            if len(summary) > 140:
                summary = summary[:137].rstrip() + "..."
            return summary
    return ""


def chat_about_idea(history: list, new_message: str) -> str:
    """
    Continue a brainstorming conversation about an idea.
    
    Args:
        history: List of {'role': 'user'|'gpt', 'content': str}
        new_message: The new user message
    
    Returns:
        GPT response string
    """
    client = get_client()
    
    # Build messages from history
    messages = [
        {"role": "system", "content": """You are helping a client brainstorm a software idea.
Be concise, ask clarifying questions, suggest features.
Keep responses under 100 words.
Be encouraging and help them refine their idea."""}
    ]
    
    for msg in history:
        role = "user" if msg['role'] == 'user' else "assistant"
        messages.append({"role": role, "content": msg['content']})
    
    # Add new message
    messages.append({"role": "user", "content": new_message})
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=200,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.exception("chat_about_idea failed: %s", e)
        return "Sorry, I couldn't process that right now. Please try again."


def generate_idea_headline(history: list) -> tuple:
    """
    Generate a headline and description from idea conversation.
    
    Returns:
        (headline, description) tuple
    """
    client = get_client()
    
    # Build conversation summary
    conv_text = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in history])
    
    prompt = f"""Based on this brainstorming conversation, generate:
1. A short headline (5-7 words) that captures the main idea
2. A brief description (1 sentence)

Conversation:
{conv_text}

Respond ONLY with JSON: {{"headline": "...", "description": "..."}}"""

    fallback_headline = _fallback_headline_from_history(history)
    fallback_description = _fallback_description(history)

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
            temperature=0.5
        )

        raw = response.choices[0].message.content or ""
        result = _extract_json_object(raw)
        headline = _normalize_headline(str(result.get("headline", "")))
        description = re.sub(r"\s+", " ", str(result.get("description", "")).strip())

        if not headline or headline.lower() in {"untitled idea", "untitled"}:
            headline = fallback_headline
        if not description:
            description = fallback_description

        return headline, description
    except Exception:
        return fallback_headline, fallback_description


def propose_idea_bootstrap(seed_headline: str, conflict_note: str = "") -> dict:
    """
    Generate initial idea bootstrap payload for `/idea <headline>`.

    Returns:
        {
            "headline": str,
            "idea_id": str,
            "assistant_message": str
        }
    """
    client = get_client()

    prompt = (
        "A client is starting a brainstorming session for a software idea. "
        "This idea will be handed to Product Manager and Business Analyst later. "
        "Return strict JSON with keys: "
        "`headline`, `idea_id`, `assistant_message`.\n\n"
        "Rules:\n"
        "- `headline`: concise PM/BA-ready title.\n"
        "- `idea_id`: lowercase snake_case file-safe id.\n"
        "- `assistant_message`: your first concise brainstorming reply to client.\n"
        "- No markdown, no extra keys.\n\n"
        f"Client seed headline: {seed_headline}\n"
    )
    if conflict_note:
        prompt += f"\nRuntime note: {conflict_note}\n"

    fallback_headline = _normalize_headline(seed_headline) or "Untitled Idea"
    fallback_id = _normalize_idea_id(seed_headline) or "untitled_idea"
    fallback_message = (
        "Great start. To prepare this for PM and Business Analyst, "
        "what is the main problem this idea solves and who is the primary user?"
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=220,
            temperature=0.4,
        )
        raw = response.choices[0].message.content or ""
        payload = _extract_json_object(raw)

        headline = _normalize_headline(str(payload.get("headline", ""))) or fallback_headline
        idea_id = _normalize_idea_id(str(payload.get("idea_id", ""))) or _normalize_idea_id(headline) or fallback_id
        assistant_message = re.sub(r"\s+", " ", str(payload.get("assistant_message", "")).strip()) or fallback_message

        return {
            "headline": headline,
            "idea_id": idea_id,
            "assistant_message": assistant_message,
        }
    except Exception:
        return {
            "headline": fallback_headline,
            "idea_id": fallback_id,
            "assistant_message": fallback_message,
        }


def generate_context_from_chat(history: list, idea_id: str = "idea") -> str:
    """
    Generate a context.md document from idea conversation.
    
    Returns:
        Markdown content for context file
    """
    client = get_client()
    
    if not idea_id:
        raise ValueError("idea_id is required for context generation.")

    template = _load_context_template()
    _template_front, _template_headings = _parse_template_contract(template)

    # Build conversation summary
    conv_text = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in history])
    
    prompt = f"""Convert this brainstorming conversation into a client context document.
Extract: what client wants, current problem, requirements, and done criteria.

Conversation:
{conv_text}

Use the following template structure exactly (same front matter keys and heading order):
{template}

Hard requirements:
- Output plain markdown only (no code fences)
- Include front matter key `idea_id` with value `{idea_id}`
- Keep all template headings and order
- Keep content concise and specific"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.5
        )
        content = response.choices[0].message.content or ""
        return _apply_template_contract(content, template, idea_id=idea_id)
    except Exception as e:
        raise RuntimeError(f"Failed to generate context from template: {e}") from e


def get_suggestions(question: str, context: str = "", num_suggestions: int = 3) -> list:
    """
    Generate suggested answers for a client question using GPT.
    
    Args:
        question: The question to generate suggestions for
        context: Additional context about the question
        num_suggestions: Number of suggestions to generate (default 3)
    
    Returns:
        List of suggested answer strings
    """
    client = get_client()
    
    prompt = f"""You are helping a non-technical client answer a question from their development team.
Generate {num_suggestions} simple, clear answer options for the following question.
Keep answers short (1-2 sentences max).
Make the first option the recommended/safest choice.
Include one option that lets the team decide.

Context: {context if context else 'Software development project'}

Question: {question}

Respond with ONLY the numbered options, one per line, like:
1. [first option]
2. [second option]
3. [third option]"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # Using gpt-4o as GPT-5.2 equivalent
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.7
        )
        
        # Parse response into list
        text = response.choices[0].message.content.strip()
        suggestions = []
        for line in text.split('\n'):
            line = line.strip()
            if line and line[0].isdigit():
                # Remove number prefix like "1. " or "1) "
                if '. ' in line:
                    line = line.split('. ', 1)[1]
                elif ') ' in line:
                    line = line.split(') ', 1)[1]
                suggestions.append(line)
        
        return suggestions[:num_suggestions]
    
    except Exception as e:
        # Fallback suggestions if API fails
        return [
            "Yes, that sounds good",
            "No, let's try something else", 
            "I'm not sure, you decide what's best"
        ]
