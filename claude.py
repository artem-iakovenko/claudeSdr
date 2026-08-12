from anthropic import Anthropic
from config import CLAUDE_CONFIG
import re
import json
from secret_manager import access_secret

CLAUDE_KEY = access_secret("kitrum-cloud", "claude_admin")

client = Anthropic(
    api_key=CLAUDE_KEY,
)


def ask_claude_beta(model, max_tokens, message, custom_skills, betas, tools):
    container_payload, skills_payload, betas_payload, tools_payload = {}, [], [], []
    for custom_skill in custom_skills:
        skills_payload.append({"type": "custom", "skill_id": custom_skill, "version": "latest"})
    if skills_payload:
        container_payload['skills'] = skills_payload
    for beta in betas:
        betas_payload.append(CLAUDE_CONFIG['betas'][beta])
    for tool in tools:
        tools_payload.append(CLAUDE_CONFIG['tools'][tool])
    message_payload = [{"role": "user", "content": message}]

    response = client.beta.messages.create(
        model=model,
        max_tokens=max_tokens,
        betas=betas_payload,
        container=container_payload,
        messages=message_payload,
        tools=tools_payload,
    )
    return response


def extract_json(response):
    text = "".join(b.text for b in response.content if b.type == "text").strip()
    if not text:
        raise ValueError(f"No text in response (stop_reason={response.stop_reason})")

    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"[\{\[].*[\}\]]", text, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


