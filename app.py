from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

try:
    import google.generativeai as genai
except ImportError:  # pragma: no cover - surfaced in the UI at runtime
    genai = None

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover - PDF loading is optional at runtime
    PdfReader = None


APP_TITLE = "AI Helpdesk Support Assistant"
KB_DIR = Path("knowledge_base")
MAX_KB_SOURCES = 3
TRIAGE_CATEGORIES = [
    "Network",
    "Hardware",
    "Software",
    "Email",
    "Account",
    "Printer",
    "Security",
    "Other",
]
PRIORITIES = ["Low", "Medium", "High", "Critical"]
SENTIMENTS = ["Calm", "Frustrated", "Angry", "Urgent"]


@dataclass
class RetrievedChunk:
    source: str
    text: str
    score: float = 0.0


class KnowledgeBase:
    def __init__(self, kb_dir: Path = KB_DIR):
        self.kb_dir = kb_dir
        self.chunks: list[RetrievedChunk] = []
        self.reload()

    def reload(self) -> int:
        self.chunks = []
        for path in sorted(self.kb_dir.glob("*")):
            if path.suffix.lower() not in {".txt", ".md", ".pdf"}:
                continue

            document_text = load_knowledge_base_file(path)
            chunks = chunk_text(document_text)
            for index, chunk in enumerate(chunks):
                source = path.name if len(chunks) == 1 else f"{path.name} - chunk {index + 1}"
                self.chunks.append(RetrievedChunk(source=source, text=chunk))

        return len(self.chunks)

    def ensure_loaded(self) -> int:
        if not self.chunks:
            return self.reload()
        return len(self.chunks)

    def search(self, query: str, limit: int = 4) -> list[RetrievedChunk]:
        self.ensure_loaded()
        query_terms = tokenize(query)
        if not query_terms:
            return []

        ranked_chunks = []
        for chunk in self.chunks:
            score = score_chunk(query=query, query_terms=query_terms, chunk=chunk)
            if score > 0:
                ranked_chunks.append(RetrievedChunk(source=chunk.source, text=chunk.text, score=score))

        ranked_chunks.sort(key=lambda chunk: chunk.score, reverse=True)
        return ranked_chunks[:limit]


def load_knowledge_base_file(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        if PdfReader is None:
            raise RuntimeError("PDF support requires pypdf. Run: pip install -r requirements.txt")
        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    return path.read_text(encoding="utf-8")


def tokenize(text: str) -> set[str]:
    stop_words = {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "do",
        "for",
        "from",
        "how",
        "i",
        "in",
        "is",
        "it",
        "my",
        "of",
        "on",
        "or",
        "the",
        "to",
        "what",
        "when",
        "with",
    }
    terms = {
        token
        for token in re.findall(r"[a-zA-Z0-9]+", text.lower())
        if len(token) > 2 and token not in stop_words
    }
    return expand_terms(terms)


def expand_terms(terms: set[str]) -> set[str]:
    synonyms = {
        "email": {"email", "mail", "mailbox", "outlook", "webmail", "messaging"},
        "mail": {"email", "mail", "mailbox", "outlook", "webmail", "messaging"},
        "outlook": {"email", "mail", "mailbox", "outlook", "webmail", "messaging"},
        "webmail": {"email", "mail", "mailbox", "outlook", "webmail", "messaging"},
        "login": {"login", "signin", "sign", "access", "account", "password", "credentials"},
        "signin": {"login", "signin", "sign", "access", "account", "password", "credentials"},
        "access": {"access", "login", "signin", "account", "permission"},
        "password": {"password", "credentials", "login", "account", "expired"},
        "account": {"account", "login", "password", "lockout", "locked", "identity"},
        "mfa": {"mfa", "authenticator", "authentication", "push", "verification"},
        "vpn": {"vpn", "network", "remote", "connection", "connect"},
        "slow": {"slow", "slowness", "freezing", "performance", "cpu", "memory", "disk"},
        "slowly": {"slow", "slowly", "slowness", "freezing", "performance", "cpu", "memory", "disk"},
        "freezing": {"slow", "slowness", "freezing", "performance", "cpu", "memory", "disk"},
        "windows": {"windows", "pc", "computer", "laptop", "performance"},
        "pc": {"windows", "pc", "computer", "laptop", "performance"},
        "printer": {"printer", "print", "queue", "spooler", "toner"},
    }

    expanded = set(terms)
    for term in terms:
        expanded.update(synonyms.get(term, set()))
    return expanded


def score_chunk(query: str, query_terms: set[str], chunk: RetrievedChunk) -> float:
    chunk_text_lower = chunk.text.lower()
    source_lower = chunk.source.lower().replace("_", " ")
    chunk_terms = tokenize(chunk.text)
    matching_terms = query_terms.intersection(chunk_terms)

    score = float(len(matching_terms) * 3)
    score += sum(chunk_text_lower.count(term) for term in matching_terms) * 0.5
    score += sum(2 for term in matching_terms if term in source_lower)

    normalized_query = " ".join(re.findall(r"[a-zA-Z0-9]+", query.lower()))
    if normalized_query and normalized_query in " ".join(re.findall(r"[a-zA-Z0-9]+", chunk_text_lower)):
        score += 5

    score += source_priority_boost(query=query, source=chunk.source)
    score += phrase_boost(query=query, chunk_text=chunk_text_lower)

    return score


def source_priority_boost(query: str, source: str) -> float:
    query_terms = tokenize(query)
    source_name = source_filename(source)
    boost = 0.0

    email_terms = {"email", "mail", "mailbox", "outlook", "webmail", "login", "access", "password", "account", "mfa"}
    if query_terms.intersection(email_terms):
        if source_name == "email_login_issues.md":
            boost += 20
        if source_name == "password_reset_account_lockout.md":
            boost += 14
        if source_name in {"vpn_troubleshooting.md", "printer_troubleshooting.md"}:
            boost -= 6

    if query_terms.intersection({"vpn", "remote", "connection", "connect"}):
        if source_name == "vpn_troubleshooting.md":
            boost += 18

    if query_terms.intersection({"slow", "slowly", "windows", "pc", "computer", "freezing", "performance", "cpu", "memory", "disk"}):
        if source_name == "windows_slow_pc_checklist.md":
            boost += 18
        if source_name in {"printer_troubleshooting.md", "vpn_troubleshooting.md", "email_login_issues.md"}:
            boost -= 8

    return boost


def phrase_boost(query: str, chunk_text: str) -> float:
    query_lower = query.lower()
    score = 0.0
    phrases = {
        "cannot access": 8,
        "company email": 10,
        "access company email": 12,
        "email login": 10,
        "password prompt": 8,
        "mfa prompt": 8,
        "account locked": 8,
        "vpn connection": 10,
        "windows pc": 8,
        "running slowly": 8,
    }

    for phrase, weight in phrases.items():
        if phrase in query_lower and any(part in chunk_text for part in phrase.split()):
            score += weight
        if phrase in chunk_text and any(part in query_lower for part in phrase.split()):
            score += weight / 2

    return score


class LLMProvider:
    name = "Base Provider"

    def triage_ticket(self, issue: str) -> dict:
        raise NotImplementedError

    def answer_with_context(self, question: str, chunks: list[RetrievedChunk]) -> str:
        raise NotImplementedError


class GeminiProvider(LLMProvider):
    name = "Google Gemini"

    def __init__(self, api_key: str, model_name: str = "gemini-1.5-flash"):
        if genai is None:
            raise RuntimeError("google-generativeai is not installed. Run: pip install -r requirements.txt")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)

    def triage_ticket(self, issue: str) -> dict:
        prompt = f"""
You are a Tier-1 IT helpdesk triage assistant. Analyze the user issue and return valid JSON only.

Allowed categories: {", ".join(TRIAGE_CATEGORIES)}
Allowed priorities: {", ".join(PRIORITIES)}
Allowed sentiments: {", ".join(SENTIMENTS)}

User issue:
{issue}

JSON schema:
{{
  "category": "...",
  "priority": "...",
  "sentiment": "...",
  "suggested_team": "...",
  "troubleshooting_steps": ["...", "...", "..."],
  "first_response": "..."
}}
"""
        response = self.model.generate_content(prompt)
        return parse_json_response(response.text)

    def answer_with_context(self, question: str, chunks: list[RetrievedChunk]) -> str:
        context = format_chunks_for_prompt(chunks)
        prompt = f"""
You are an IT knowledge base assistant. Answer the technician's question using only the context below.
If the answer is not in the context, say what is missing and suggest escalating or checking internal documentation.
Return the answer in exactly this format:

Answer:
- Clear troubleshooting steps: ...
- What to verify first: ...
- When to escalate: ...

Sources:
- source filename

Question:
{question}

Knowledge base context:
{context}
"""
        response = self.model.generate_content(prompt)
        return response.text.strip()


class RuleBasedFallbackProvider(LLMProvider):
    name = "Local Rule-Based Fallback"

    def triage_ticket(self, issue: str) -> dict:
        text = issue.lower()
        category = "Other"
        team = "Service Desk"

        rules = [
            (("vpn", "wi-fi", "wifi", "internet", "network", "connect"), "Network", "Network Support"),
            (("printer", "print", "toner", "paper jam"), "Printer", "Desktop Support"),
            (("email", "outlook", "mailbox", "company email"), "Email", "Messaging / Email Support"),
            (("password", "locked", "lockout", "account", "login", "sign in"), "Account", "Identity and Access Management"),
            (("slow", "freezing", "crash", "windows", "application"), "Software", "Desktop Support"),
            (("laptop", "keyboard", "screen", "battery", "hardware"), "Hardware", "Desktop Support"),
            (("phishing", "malware", "virus", "suspicious", "security"), "Security", "Security Operations"),
        ]
        for keywords, matched_category, matched_team in rules:
            if any(keyword in text for keyword in keywords):
                category = matched_category
                team = matched_team
                break

        priority = "Medium"
        if any(word in text for word in ["urgent", "asap", "immediately", "critical", "cannot work"]):
            priority = "High"
        if any(word in text for word in ["company-wide", "all users", "breach", "ransomware", "data loss"]):
            priority = "Critical"
        if any(word in text for word in ["question", "when possible", "minor"]):
            priority = "Low"

        sentiment = "Calm"
        if any(word in text for word in ["frustrated", "annoyed", "keeps happening"]):
            sentiment = "Frustrated"
        if any(word in text for word in ["angry", "unacceptable", "mad"]):
            sentiment = "Angry"
        if any(word in text for word in ["urgent", "asap", "immediately", "deadline"]):
            sentiment = "Urgent"

        return {
            "category": category,
            "priority": priority,
            "sentiment": sentiment,
            "suggested_team": team,
            "troubleshooting_steps": troubleshooting_steps_for(category),
            "first_response": (
                "Thank you for contacting IT Support. We have received your request and will begin "
                f"troubleshooting it as a {priority.lower()} priority {category.lower()} issue. "
                "Please keep your device available in case we need additional details."
            ),
        }

    def answer_with_context(self, question: str, chunks: list[RetrievedChunk]) -> str:
        return build_fallback_kb_answer(question=question, chunks=chunks)


def chunk_text(text: str, max_words: int = 260, overlap: int = 40) -> list[str]:
    words = text.split()
    if not words:
        return []

    if len(words) <= max_words:
        return [text.strip()]

    chunks = []
    step = max_words - overlap
    for start in range(0, len(words), step):
        chunk = " ".join(words[start : start + max_words])
        chunks.append(chunk)
        if start + max_words >= len(words):
            break
    return chunks


def format_chunks_for_prompt(chunks: list[RetrievedChunk]) -> str:
    return "\n\n".join(f"Source: {chunk.source}\n{chunk.text}" for chunk in chunks)


def source_filename(source: str) -> str:
    return source.split(" - chunk ", maxsplit=1)[0]


def unique_top_sources(
    chunks: list[RetrievedChunk],
    limit: int = MAX_KB_SOURCES,
    min_score_ratio: float = 0.5,
) -> list[RetrievedChunk]:
    if not chunks:
        return []

    best_score = chunks[0].score
    selected = []
    seen_sources = set()
    for chunk in chunks:
        if best_score > 0 and chunk.score < best_score * min_score_ratio:
            continue

        filename = source_filename(chunk.source)
        if filename in seen_sources:
            continue
        selected.append(RetrievedChunk(source=filename, text=chunk.text, score=chunk.score))
        seen_sources.add(filename)
        if len(selected) == limit:
            break
    return selected


def answer_with_fallback(provider: LLMProvider, question: str, chunks: list[RetrievedChunk]) -> str:
    if isinstance(provider, GeminiProvider):
        try:
            answer = provider.answer_with_context(question, chunks).strip()
            if is_useful_kb_answer(answer):
                return ensure_sources_section(answer=answer, chunks=chunks)
        except Exception:
            pass

    return build_fallback_kb_answer(question=question, chunks=chunks)


def is_useful_kb_answer(answer: str) -> bool:
    answer_lower = answer.lower()
    return bool(answer.strip()) and "answer:" in answer_lower and len(re.findall(r"^-", answer, re.MULTILINE)) >= 3


def ensure_sources_section(answer: str, chunks: list[RetrievedChunk]) -> str:
    if "sources:" in answer.lower():
        return answer

    source_lines = "\n".join(f"- {source_filename(chunk.source)}" for chunk in chunks)
    return f"{answer.rstrip()}\n\nSources:\n{source_lines}"


def build_fallback_kb_answer(question: str, chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return (
            "Answer:\n"
            "- Clear troubleshooting steps: No matching knowledge base content was found for this question.\n"
            "- What to verify first: Confirm the user, device, application, exact error message, and business impact.\n"
            "- When to escalate: Escalate if the issue blocks work or requires access outside Tier-1 permissions.\n\n"
            "Sources:\n"
            "- No matching source found"
        )

    context_text = "\n".join(chunk.text for chunk in chunks)
    steps = extract_relevant_steps(context_text)
    verify_first = pick_verify_first(question=question, chunks=chunks, steps=steps)
    escalation = extract_escalation(context_text)
    source_lines = "\n".join(f"- {source_filename(chunk.source)}" for chunk in chunks)

    return (
        "Answer:\n"
        f"- Clear troubleshooting steps: {format_inline_steps(steps)}\n"
        f"- What to verify first: {verify_first}\n"
        f"- When to escalate: {escalation}\n\n"
        "Sources:\n"
        f"{source_lines}"
    )


def extract_relevant_steps(text: str, limit: int = 5) -> list[str]:
    candidates = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        cleaned = re.sub(r"^[-*]\s*", "", stripped)
        cleaned = re.sub(r"^\d+\.\s*", "", cleaned)
        if len(cleaned) < 20:
            continue
        if cleaned.lower().startswith(("common symptoms", "tier-1 checklist", "escalation notes")):
            continue
        candidates.append(cleaned)

    preferred_terms = ("confirm", "verify", "check", "ask", "try", "restart", "guide")
    preferred = [line for line in candidates if line.lower().startswith(preferred_terms)]
    combined = preferred + [line for line in candidates if line not in preferred]
    return list(dict.fromkeys(combined))[:limit]


def format_inline_steps(steps: list[str]) -> str:
    if not steps:
        return "Confirm the issue details, check account or service status, test a known working access path, and document the exact error."
    return "; ".join(steps)


def pick_verify_first(question: str, chunks: list[RetrievedChunk], steps: list[str]) -> str:
    query_terms = tokenize(question)
    source_names = {source_filename(chunk.source) for chunk in chunks}

    if source_names.intersection({"email_login_issues.md", "password_reset_account_lockout.md"}) or query_terms.intersection(
        {"email", "mail", "outlook", "webmail", "login", "access", "password", "account", "mfa"}
    ):
        return (
            "First verify whether the user can sign in to webmail, whether their password works for other "
            "company services, whether MFA is available, and whether the account is locked, expired, disabled, or unlicensed."
        )

    if "vpn_troubleshooting.md" in source_names:
        return "First verify public internet access, the approved VPN client/profile, credentials, MFA approval, and whether other users are affected."

    if "windows_slow_pc_checklist.md" in source_names:
        return "First verify when the slowness started, whether the PC was recently restarted, and Task Manager CPU, memory, disk, and startup app usage."

    if steps:
        return steps[0]

    return "First verify the user's identity, device, exact error message, scope, and business impact."


def extract_escalation(text: str) -> str:
    escalation_lines = []
    capture = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.lower().startswith("## escalation"):
            capture = True
            continue
        if capture and stripped.startswith("## "):
            break
        if capture and stripped and not stripped.startswith("#"):
            escalation_lines.append(re.sub(r"^[-*]\s*", "", stripped))

    if escalation_lines:
        return " ".join(escalation_lines)

    return "Escalate when multiple users are affected, Tier-1 checks do not restore access, policy requires resolver-team action, or suspicious activity is present."


def parse_json_response(text: str) -> dict:
    cleaned = text.strip()
    cleaned = re.sub(r"^```json\s*|\s*```$", "", cleaned, flags=re.IGNORECASE | re.MULTILINE)
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if match:
        cleaned = match.group(0)
    data = json.loads(cleaned)
    return normalize_triage(data)


def normalize_triage(data: dict) -> dict:
    category = data.get("category", "Other")
    priority = data.get("priority", "Medium")
    sentiment = data.get("sentiment", "Calm")

    return {
        "category": category if category in TRIAGE_CATEGORIES else "Other",
        "priority": priority if priority in PRIORITIES else "Medium",
        "sentiment": sentiment if sentiment in SENTIMENTS else "Calm",
        "suggested_team": data.get("suggested_team", "Service Desk"),
        "troubleshooting_steps": ensure_list(data.get("troubleshooting_steps")),
        "first_response": data.get(
            "first_response",
            "Thank you for contacting IT Support. We have received your request and will follow up shortly.",
        ),
    }


def ensure_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        return [value]
    return ["Confirm the issue details.", "Check recent changes.", "Escalate if the issue blocks work."]


def troubleshooting_steps_for(category: str) -> list[str]:
    steps = {
        "Network": [
            "Confirm whether the user is on home Wi-Fi, office LAN, or VPN.",
            "Ask the user to restart the VPN client and verify internet access.",
            "Check for known network or VPN service alerts.",
        ],
        "Printer": [
            "Confirm the printer name, location, and whether other users are affected.",
            "Check printer power, paper, toner, queue status, and default printer setting.",
            "Restart the print spooler or re-add the printer if needed.",
        ],
        "Email": [
            "Confirm whether the issue affects webmail, Outlook, or mobile email.",
            "Check credentials, MFA prompts, mailbox status, and service health.",
            "Try Outlook web access to isolate client versus account issues.",
        ],
        "Account": [
            "Verify the user's identity using the approved helpdesk process.",
            "Check whether the account is locked, disabled, or requiring password reset.",
            "Confirm MFA status and recent sign-in errors.",
        ],
        "Hardware": [
            "Confirm the device model, asset tag, and physical symptoms.",
            "Ask the user to reboot and disconnect unnecessary peripherals.",
            "Check warranty or replacement path if hardware failure is suspected.",
        ],
        "Software": [
            "Capture the application name, error message, and recent changes.",
            "Restart the application and device, then check updates.",
            "Review startup apps, disk space, and event logs if performance is affected.",
        ],
        "Security": [
            "Advise the user not to click links, delete evidence, or continue using a suspicious file.",
            "Collect sender, URL, attachment, and screenshot details.",
            "Escalate to Security Operations immediately if compromise is suspected.",
        ],
        "Other": [
            "Collect device, user, location, and business impact details.",
            "Try to reproduce the issue or identify when it started.",
            "Route to the appropriate resolver group after initial checks.",
        ],
    }
    return steps.get(category, steps["Other"])


def get_provider() -> LLMProvider:
    load_dotenv()
    api_key = get_config_value("GEMINI_API_KEY")
    model_name = get_config_value("GEMINI_MODEL", "gemini-1.5-flash")

    if api_key:
        try:
            return GeminiProvider(api_key=api_key, model_name=model_name)
        except Exception:
            return RuleBasedFallbackProvider()

    return RuleBasedFallbackProvider()


def get_config_value(name: str, default: str | None = None) -> str | None:
    try:
        value = st.secrets.get(name)
        if value:
            return str(value)
    except Exception:
        pass

    return os.getenv(name, default)


@st.cache_resource
def get_knowledge_base() -> KnowledgeBase:
    return KnowledgeBase()


def render_triage_tab(provider: LLMProvider) -> None:
    st.subheader("Ticket Triage")
    with st.expander("❔ What does this page do?"):
        st.write(
            "This page simulates Tier-1 helpdesk ticket intake. Enter a user issue and the app "
            "classifies category, priority, sentiment, resolver team, and first troubleshooting steps."
        )

    issue = st.text_area(
        "Describe the IT support issue",
        height=140,
        placeholder="Example: I cannot connect to the VPN from home and I have a deadline today.",
    )

    examples = [
        "I cannot connect to the VPN from home.",
        "My laptop is very slow and keeps freezing.",
        "I cannot access my company email.",
        "The printer is not working and I need it urgently.",
    ]
    selected_example = st.selectbox("Try an example ticket", [""] + examples)
    if selected_example and not issue:
        issue = selected_example
        st.info(issue)

    if st.button("Analyze Ticket", type="primary"):
        if not issue.strip():
            st.error("Enter a support issue before analyzing the ticket.")
            return

        with st.spinner("Analyzing ticket..."):
            try:
                triage = provider.triage_ticket(issue)
            except Exception as exc:
                st.error(f"Could not analyze the ticket: {exc}")
                return

        columns = st.columns(3)
        columns[0].metric("Category", triage["category"])
        columns[1].metric("Priority", triage["priority"])
        columns[2].metric("Sentiment", triage["sentiment"])

        st.markdown(f"**Suggested team:** {triage['suggested_team']}")
        st.markdown("**First troubleshooting steps:**")
        for step in triage["troubleshooting_steps"]:
            st.write(f"- {step}")

        st.markdown("**Professional first response:**")
        st.success(triage["first_response"])


def render_kb_tab(provider: LLMProvider) -> None:
    st.subheader("Knowledge Base Search")
    with st.expander("❔ What does this page do?"):
        st.write(
            "This page simulates an internal IT knowledge base assistant. Ask a troubleshooting question "
            "and the app searches local IT support documents, then generates an answer based on the most "
            "relevant sources."
        )

    try:
        knowledge_base = get_knowledge_base()
        chunk_count = knowledge_base.ensure_loaded()
    except Exception as exc:
        st.error(f"Knowledge base is unavailable: {exc}")
        return

    left, right = st.columns([2, 1])
    left.caption(f"Loaded knowledge base chunks: {chunk_count}")
    if right.button("Reload Knowledge Base"):
        with st.spinner("Reloading local knowledge base files..."):
            chunk_count = knowledge_base.reload()
        st.success(f"Reloaded {chunk_count} chunks.")

    example_questions = [
        "How do I troubleshoot VPN connection failure?",
        "What should I check when a user cannot access company email?",
        "What should I check when a Windows PC is running slowly?",
    ]
    example_columns = st.columns(3)
    for index, example_question in enumerate(example_questions):
        if example_columns[index].button(example_question, key=f"kb_example_{index}"):
            st.session_state.kb_question = example_question
            question = example_question

    question = st.text_input(
        "Ask a technician question",
        placeholder="How do I troubleshoot VPN connection failure?",
        key="kb_question",
    )

    if st.button("Search Knowledge Base", type="primary"):
        if not question.strip():
            st.error("Enter a question before searching the knowledge base.")
            return

        with st.spinner("Retrieving relevant documents..."):
            chunks = unique_top_sources(knowledge_base.search(question, limit=6))

        if not chunks:
            st.warning("No matching knowledge base content was found.")
            return

        with st.spinner("Drafting answer..."):
            answer = answer_with_fallback(provider=provider, question=question, chunks=chunks)

        st.markdown(answer)

        with st.expander("Retrieved sources"):
            for chunk in chunks:
                st.markdown(f"**{chunk.source} | score: {chunk.score:.1f}**")
                st.write(chunk.text)


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, layout="wide")
    st.title(APP_TITLE)
    st.caption("Tier-1 ticket triage and local IT knowledge base assistant")

    provider = get_provider()
    with st.sidebar:
        st.header("Configuration")
        st.write(f"LLM provider: **{provider.name}**")
        st.markdown("Local knowledge base files are loaded from `knowledge_base/`.")

    triage_tab, kb_tab = st.tabs(["Ticket Triage", "Knowledge Base Search"])
    with triage_tab:
        render_triage_tab(provider)
    with kb_tab:
        render_kb_tab(provider)


if __name__ == "__main__":
    main()
