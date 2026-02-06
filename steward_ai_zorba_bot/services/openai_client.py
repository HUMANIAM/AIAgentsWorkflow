#!/usr/bin/env python3
"""OpenAI GPT client for generating suggested answers"""

import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI


# Load .env from bot directory
env_file = Path(__file__).parent.parent / ".env"
load_dotenv(env_file)


def get_client():
    """Get OpenAI client with API key from .env"""
    api_key = os.getenv('AI_API_KEY', '').strip()
    if not api_key:
        raise ValueError("AI_API_KEY not found in .env")
    return OpenAI(api_key=api_key)


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
        return f"Sorry, I couldn't process that: {str(e)}"


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

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
            temperature=0.5
        )
        
        import json
        result = json.loads(response.choices[0].message.content.strip())
        return result.get('headline', 'Untitled Idea'), result.get('description', '')
    except Exception:
        return 'Untitled Idea', ''


def generate_context_from_chat(history: list) -> str:
    """
    Generate a context.md document from idea conversation.
    
    Returns:
        Markdown content for context file
    """
    client = get_client()
    
    # Build conversation summary
    conv_text = "\n".join([f"{m['role'].upper()}: {m['content']}" for m in history])
    
    prompt = f"""Convert this brainstorming conversation into a client context document.
Extract: what they want, their current problem, requirements, and done criteria.

Conversation:
{conv_text}

Output in this markdown format:
---
plugin: idea_name
version: 1
owner: client
last_updated: {__import__('datetime').datetime.now().strftime('%Y-%m-%d')}
---

# What I want (client perspective)
[Summary of what they want]

## The problem I have now:
[Current situation/problem]

## What I need:
[List of requirements]

## What "done" means to me:
[Success criteria]"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.5
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"# Error generating context\n\n{str(e)}"


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
