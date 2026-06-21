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
LANGUAGE_OPTIONS = {"English": "en", "日本語": "ja"}
LANGUAGE_NAMES = {"en": "English", "ja": "Japanese"}

TRANSLATIONS = {
    "en": {
        "language_label": "Language",
        "app_caption": "Tier-1 ticket triage and local IT knowledge base assistant",
        "sidebar_header": "Configuration",
        "provider_label": "LLM provider",
        "kb_sidebar": "Local knowledge base files are loaded from `knowledge_base/`.",
        "tab_triage": "Ticket Triage",
        "tab_kb": "Knowledge Base Search",
        "help_title": "? What does this page do?",
        "triage_subheader": "Ticket Triage",
        "triage_help": (
            "This page simulates Tier-1 helpdesk ticket intake. Enter a user issue and the app "
            "classifies category, priority, sentiment, resolver team, and first troubleshooting steps."
        ),
        "issue_label": "Describe the IT support issue",
        "issue_placeholder": "Example: I cannot connect to the VPN from home and I have a deadline today.",
        "example_ticket_label": "Try an example ticket",
        "analyze_ticket": "Analyze Ticket",
        "empty_issue_error": "Enter a support issue before analyzing the ticket.",
        "analyzing_ticket": "Analyzing ticket...",
        "category": "Category",
        "priority": "Priority",
        "sentiment": "Sentiment",
        "suggested_team": "Suggested team",
        "first_steps": "First troubleshooting steps:",
        "professional_response": "Professional first response:",
        "kb_subheader": "Knowledge Base Search",
        "kb_help": (
            "This page simulates an internal IT knowledge base assistant. Ask a troubleshooting question "
            "and the app searches local IT support documents, then generates an answer based on the most "
            "relevant sources."
        ),
        "loaded_chunks": "Loaded knowledge base chunks: {count}",
        "reload_kb": "Reload Knowledge Base",
        "reloading_kb": "Reloading local knowledge base files...",
        "reloaded_kb": "Reloaded {count} chunks.",
        "question_label": "Ask a technician question",
        "question_placeholder": "How do I troubleshoot VPN connection failure?",
        "search_kb": "Search Knowledge Base",
        "empty_question_error": "Enter a question before searching the knowledge base.",
        "retrieving_docs": "Retrieving relevant documents...",
        "no_matches": "No matching knowledge base content was found.",
        "drafting_answer": "Drafting answer...",
        "retrieved_sources": "Retrieved sources",
        "kb_unavailable": "Knowledge base is unavailable: {error}",
    },
    "ja": {
        "language_label": "言語",
        "app_caption": "Tier-1ヘルプデスクのチケット分類と社内ITナレッジベース検索アシスタント",
        "sidebar_header": "設定",
        "provider_label": "LLMプロバイダー",
        "kb_sidebar": "ローカルのナレッジベース文書は `knowledge_base/` から読み込まれます。",
        "tab_triage": "チケット分類",
        "tab_kb": "ナレッジベース検索",
        "help_title": "? このページでできること",
        "triage_subheader": "チケット分類",
        "triage_help": (
            "このページは、Tier-1ヘルプデスクのチケット受付を想定したものです。ユーザーからの問い合わせ内容を入力すると、"
            "カテゴリ、優先度、感情、対応チーム、最初に確認すべきトラブルシューティング手順を分類します。"
        ),
        "issue_label": "ITサポートの問い合わせ内容",
        "issue_placeholder": "例: 自宅からVPNに接続できず、本日中に作業が必要です。",
        "example_ticket_label": "サンプルチケットを選択",
        "analyze_ticket": "チケットを分析",
        "empty_issue_error": "分析する前に問い合わせ内容を入力してください。",
        "analyzing_ticket": "チケットを分析しています...",
        "category": "カテゴリ",
        "priority": "優先度",
        "sentiment": "感情",
        "suggested_team": "推奨対応チーム",
        "first_steps": "最初のトラブルシューティング手順:",
        "professional_response": "ユーザーへの一次返信文:",
        "kb_subheader": "ナレッジベース検索",
        "kb_help": (
            "このページは、社内ITナレッジベースアシスタントを想定したものです。トラブルシューティングに関する質問を入力すると、"
            "ローカルのITサポート文書を検索し、関連度の高い情報に基づいて回答を生成します。"
        ),
        "loaded_chunks": "読み込み済みナレッジベースチャンク: {count}",
        "reload_kb": "ナレッジベースを再読み込み",
        "reloading_kb": "ローカルのナレッジベース文書を再読み込みしています...",
        "reloaded_kb": "{count}件のチャンクを再読み込みしました。",
        "question_label": "技術者向けの質問を入力",
        "question_placeholder": "VPNに接続できない場合はどうすればいいですか？",
        "search_kb": "ナレッジベースを検索",
        "empty_question_error": "検索する前に質問を入力してください。",
        "retrieving_docs": "関連する文書を検索しています...",
        "no_matches": "一致するナレッジベース文書が見つかりませんでした。",
        "drafting_answer": "回答を作成しています...",
        "retrieved_sources": "参照した文書",
        "kb_unavailable": "ナレッジベースを利用できません: {error}",
    },
}

CATEGORY_LABELS = {
    "en": {category: category for category in TRIAGE_CATEGORIES},
    "ja": {
        "Network": "ネットワーク",
        "Hardware": "ハードウェア",
        "Software": "ソフトウェア",
        "Email": "メール",
        "Account": "アカウント",
        "Printer": "プリンター",
        "Security": "セキュリティ",
        "Other": "その他",
    },
}
PRIORITY_LABELS = {
    "en": {priority: priority for priority in PRIORITIES},
    "ja": {"Low": "低", "Medium": "中", "High": "高", "Critical": "緊急"},
}
SENTIMENT_LABELS = {
    "en": {sentiment: sentiment for sentiment in SENTIMENTS},
    "ja": {"Calm": "落ち着いている", "Frustrated": "困っている", "Angry": "怒っている", "Urgent": "緊急"},
}
TEAM_LABELS_JA = {
    "Service Desk": "サービスデスク",
    "Network Support": "ネットワークサポート",
    "Desktop Support": "デスクトップサポート",
    "Messaging / Email Support": "メールサポート",
    "Identity and Access Management": "ID・アクセス管理チーム",
    "Security Operations": "セキュリティ運用チーム",
}

JAPANESE_SEARCH_MAPPINGS = {
    "VPN": " VPN ",
    "メール": " email mail outlook webmail ",
    "パスワード": " password credentials ",
    "アカウント": " account login identity ",
    "プリンター": " printer print queue ",
    "ネットワーク": " network internet connection ",
    "遅い": " slow performance freezing ",
    "ログイン": " login signin access ",
    "接続できない": " cannot connect connection failure ",
    "アクセスできない": " cannot access login account ",
    "会社のメール": " company email mailbox outlook ",
    "動作が遅い": " slow performance cpu memory disk ",
}


@dataclass
class RetrievedChunk:
    source: str
    text: str
    score: float = 0.0


def t(language: str, key: str, **kwargs: object) -> str:
    text = TRANSLATIONS.get(language, TRANSLATIONS["en"]).get(key, TRANSLATIONS["en"][key])
    return text.format(**kwargs) if kwargs else text


def display_value(value_type: str, value: str, language: str) -> str:
    labels = {
        "category": CATEGORY_LABELS,
        "priority": PRIORITY_LABELS,
        "sentiment": SENTIMENT_LABELS,
    }
    return labels.get(value_type, {}).get(language, {}).get(value, value)


def display_team(team: str, language: str) -> str:
    if language == "ja":
        return TEAM_LABELS_JA.get(team, team)
    return team


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
    text = normalize_search_text(text)
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


def normalize_search_text(text: str) -> str:
    normalized = text
    for japanese, english_terms in JAPANESE_SEARCH_MAPPINGS.items():
        if japanese in normalized:
            normalized = normalized.replace(japanese, f"{japanese} {english_terms}")
    return normalized


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
    normalized_query_text = normalize_search_text(query)
    chunk_text_lower = chunk.text.lower()
    source_lower = chunk.source.lower().replace("_", " ")
    chunk_terms = tokenize(chunk.text)
    matching_terms = query_terms.intersection(chunk_terms)

    score = float(len(matching_terms) * 3)
    score += sum(chunk_text_lower.count(term) for term in matching_terms) * 0.5
    score += sum(2 for term in matching_terms if term in source_lower)

    normalized_query = " ".join(re.findall(r"[a-zA-Z0-9]+", normalized_query_text.lower()))
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
    query_lower = normalize_search_text(query).lower()
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

    def triage_ticket(self, issue: str, language: str) -> dict:
        raise NotImplementedError

    def answer_with_context(self, question: str, chunks: list[RetrievedChunk], language: str) -> str:
        raise NotImplementedError


class GeminiProvider(LLMProvider):
    name = "Google Gemini"

    def __init__(self, api_key: str, model_name: str = "gemini-1.5-flash"):
        if genai is None:
            raise RuntimeError("google-generativeai is not installed. Run: pip install -r requirements.txt")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)

    def triage_ticket(self, issue: str, language: str) -> dict:
        response_language = LANGUAGE_NAMES.get(language, "English")
        prompt = f"""
You are a Tier-1 IT helpdesk triage assistant. Analyze the user issue and return valid JSON only.
Answer user-facing fields in {response_language}.

Allowed categories: {", ".join(TRIAGE_CATEGORIES)}
Allowed priorities: {", ".join(PRIORITIES)}
Allowed sentiments: {", ".join(SENTIMENTS)}
Keep category, priority, and sentiment values exactly in English from the allowed lists.
Write suggested_team, troubleshooting_steps, and first_response in {response_language}.

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
        return parse_json_response(response.text, language)

    def answer_with_context(self, question: str, chunks: list[RetrievedChunk], language: str) -> str:
        context = format_chunks_for_prompt(chunks)
        response_language = LANGUAGE_NAMES.get(language, "English")
        if language == "ja":
            answer_format = """
回答:
- トラブルシューティング手順: ...
- 最初に確認すること: ...
- エスカレーションの目安: ...

参照元:
- source filename
"""
        else:
            answer_format = """
Answer:
- Clear troubleshooting steps: ...
- What to verify first: ...
- When to escalate: ...

Sources:
- source filename
"""
        prompt = f"""
You are an IT knowledge base assistant. Answer the technician's question using only the context below.
If the answer is not in the context, say what is missing and suggest escalating or checking internal documentation.
Write the answer in {response_language}. Keep source filenames unchanged.
Return the answer in exactly this format:
{answer_format}

Question:
{question}

Knowledge base context:
{context}
"""
        response = self.model.generate_content(prompt)
        return response.text.strip()


class RuleBasedFallbackProvider(LLMProvider):
    name = "Local Rule-Based Fallback"

    def triage_ticket(self, issue: str, language: str) -> dict:
        text = normalize_search_text(issue).lower()
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
            "suggested_team": display_team(team, language),
            "troubleshooting_steps": troubleshooting_steps_for(category, language),
            "first_response": first_response_for(category=category, priority=priority, language=language),
        }

    def answer_with_context(self, question: str, chunks: list[RetrievedChunk], language: str) -> str:
        return build_fallback_kb_answer(question=question, chunks=chunks, language=language)


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


def answer_with_fallback(provider: LLMProvider, question: str, chunks: list[RetrievedChunk], language: str) -> str:
    if isinstance(provider, GeminiProvider):
        try:
            answer = provider.answer_with_context(question, chunks, language).strip()
            if is_useful_kb_answer(answer, language):
                return ensure_sources_section(answer=answer, chunks=chunks, language=language)
        except Exception:
            pass

    return build_fallback_kb_answer(question=question, chunks=chunks, language=language)


def is_useful_kb_answer(answer: str, language: str) -> bool:
    answer_lower = answer.lower()
    required_heading = "回答:" if language == "ja" else "answer:"
    return bool(answer.strip()) and required_heading in answer_lower and len(re.findall(r"^-", answer, re.MULTILINE)) >= 3


def ensure_sources_section(answer: str, chunks: list[RetrievedChunk], language: str) -> str:
    source_heading = "参照元:" if language == "ja" else "Sources:"
    if "sources:" in answer.lower() or "参照元:" in answer:
        return answer

    source_lines = "\n".join(f"- {source_filename(chunk.source)}" for chunk in chunks)
    return f"{answer.rstrip()}\n\n{source_heading}\n{source_lines}"


def build_fallback_kb_answer(question: str, chunks: list[RetrievedChunk], language: str) -> str:
    if not chunks:
        if language == "ja":
            return (
                "回答:\n"
                "- トラブルシューティング手順: 該当するナレッジベース文書が見つかりませんでした。\n"
                "- 最初に確認すること: ユーザー、端末、対象アプリ、正確なエラーメッセージ、業務影響を確認してください。\n"
                "- エスカレーションの目安: 業務が停止している場合、またはTier-1の権限外の対応が必要な場合はエスカレーションしてください。\n\n"
                "参照元:\n"
                "- 該当なし"
            )
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
    verify_first = pick_verify_first(question=question, chunks=chunks, steps=steps, language=language)
    escalation = extract_escalation(context_text, language)
    source_lines = "\n".join(f"- {source_filename(chunk.source)}" for chunk in chunks)

    if language == "ja":
        return (
            "回答:\n"
            f"- トラブルシューティング手順: {format_inline_steps(steps, language)}\n"
            f"- 最初に確認すること: {verify_first}\n"
            f"- エスカレーションの目安: {escalation}\n\n"
            "参照元:\n"
            f"{source_lines}"
        )

    return (
        "Answer:\n"
        f"- Clear troubleshooting steps: {format_inline_steps(steps, language)}\n"
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


def format_inline_steps(steps: list[str], language: str) -> str:
    if not steps:
        if language == "ja":
            return "問い合わせ内容、アカウントまたはサービス状態、正常に利用できるアクセス方法、正確なエラー内容を確認してください。"
        return "Confirm the issue details, check account or service status, test a known working access path, and document the exact error."
    if language == "ja":
        return "；".join(translate_step_to_japanese(step) for step in steps)
    return "; ".join(steps)


def pick_verify_first(question: str, chunks: list[RetrievedChunk], steps: list[str], language: str) -> str:
    query_terms = tokenize(question)
    source_names = {source_filename(chunk.source) for chunk in chunks}

    if source_names.intersection({"email_login_issues.md", "password_reset_account_lockout.md"}) or query_terms.intersection(
        {"email", "mail", "outlook", "webmail", "login", "access", "password", "account", "mfa"}
    ):
        if language == "ja":
            return (
                "まず、Webメールにサインインできるか、他の社内サービスでパスワードが有効か、MFAを利用できるか、"
                "アカウントがロック・期限切れ・無効化・ライセンス未付与になっていないかを確認してください。"
            )
        return (
            "First verify whether the user can sign in to webmail, whether their password works for other "
            "company services, whether MFA is available, and whether the account is locked, expired, disabled, or unlicensed."
        )

    if "vpn_troubleshooting.md" in source_names:
        if language == "ja":
            return "まず、通常のインターネット接続、承認済みVPNクライアントとプロファイル、認証情報、MFA承認、他ユーザーへの影響有無を確認してください。"
        return "First verify public internet access, the approved VPN client/profile, credentials, MFA approval, and whether other users are affected."

    if "windows_slow_pc_checklist.md" in source_names:
        if language == "ja":
            return "まず、動作が遅くなった時期、直近で再起動済みか、タスクマネージャーでCPU・メモリ・ディスク・スタートアップアプリの使用状況を確認してください。"
        return "First verify when the slowness started, whether the PC was recently restarted, and Task Manager CPU, memory, disk, and startup app usage."

    if steps:
        return translate_step_to_japanese(steps[0]) if language == "ja" else steps[0]

    if language == "ja":
        return "まず、ユーザー本人、端末、正確なエラーメッセージ、影響範囲、業務影響を確認してください。"
    return "First verify the user's identity, device, exact error message, scope, and business impact."


def extract_escalation(text: str, language: str) -> str:
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
        escalation = " ".join(escalation_lines)
        return translate_escalation_to_japanese(escalation) if language == "ja" else escalation

    if language == "ja":
        return "複数ユーザーに影響している場合、Tier-1の確認で復旧しない場合、専門チームの権限が必要な場合、または不審な操作が疑われる場合はエスカレーションしてください。"
    return "Escalate when multiple users are affected, Tier-1 checks do not restore access, policy requires resolver-team action, or suspicious activity is present."


def translate_step_to_japanese(step: str) -> str:
    lower_step = step.lower()
    translations = [
        ("sign in to webmail", "ブラウザーでWebメールにサインインできるか確認してください。"),
        ("username format", "ユーザー名の形式と、同じパスワードで他の社内サービスにサインインできるか確認してください。"),
        ("account lockout", "アカウントロック、パスワード期限切れ、アカウント無効化、直近のパスワード変更有無を確認してください。"),
        ("mfa", "MFAの方法が利用可能か、プッシュ通知がブロックされていないか確認してください。"),
        ("private browser", "キャッシュされた認証情報の影響を切り分けるため、プライベートブラウザーで試してください。"),
        ("internet access", "VPN接続前に、通常のインターネット接続が利用できるか確認してください。"),
        ("vpn client", "承認済みVPNクライアントと正しい会社VPNプロファイルを使用しているか確認してください。"),
        ("restart the computer", "VPNアダプターやネットワークアダプターが固まっている可能性があるため、端末の再起動を案内してください。"),
        ("task manager", "タスクマネージャーでCPU、メモリ、ディスク、スタートアップアプリの使用状況を確認してください。"),
        ("disk space", "空きディスク容量を確認してください。容量不足はフリーズや更新失敗の原因になります。"),
        ("windows updates", "Windows Updateが実行中ではないか確認してください。"),
        ("printer name", "プリンター名、設置場所、ユーザーが社内またはリモート環境かを確認してください。"),
    ]
    for needle, translation in translations:
        if needle in lower_step:
            return translation
    return step


def translate_escalation_to_japanese(escalation: str) -> str:
    lower_escalation = escalation.lower()
    if "messaging support" in lower_escalation or "mailbox" in lower_escalation:
        return "メールボックスが見つからない、ライセンス設定に問題がある、複数ユーザーに影響している、または本人確認後もMFAを受信できない場合は、メールサポートへエスカレーションしてください。"
    if "identity and access management" in lower_escalation or "account is disabled" in lower_escalation:
        return "アカウントが無効化されている、権限が不足している、MFAをTier-1でリセットできない、または保存済み資格情報を更新してもロックアウトが続く場合は、ID・アクセス管理チームへエスカレーションしてください。"
    if "network support" in lower_escalation or "vpn" in lower_escalation:
        return "複数ユーザーに影響している、VPNゲートウェイが利用できない、DNSやルートに問題がある、または基本確認後も接続タイムアウトが続く場合は、ネットワークサポートへエスカレーションしてください。"
    if "desktop support" in lower_escalation or "hardware" in lower_escalation:
        return "ハードウェア障害、ブルースクリーン、ディスクエラー、過熱、またはTier-1確認後も改善しない場合は、デスクトップサポートへエスカレーションしてください。"
    return "複数ユーザーに影響している場合、Tier-1の確認で復旧しない場合、専門チームの権限が必要な場合、または不審な操作が疑われる場合はエスカレーションしてください。"


def parse_json_response(text: str, language: str = "en") -> dict:
    cleaned = text.strip()
    cleaned = re.sub(r"^```json\s*|\s*```$", "", cleaned, flags=re.IGNORECASE | re.MULTILINE)
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if match:
        cleaned = match.group(0)
    data = json.loads(cleaned)
    return normalize_triage(data, language)


def normalize_triage(data: dict, language: str = "en") -> dict:
    category = data.get("category", "Other")
    priority = data.get("priority", "Medium")
    sentiment = data.get("sentiment", "Calm")

    return {
        "category": category if category in TRIAGE_CATEGORIES else "Other",
        "priority": priority if priority in PRIORITIES else "Medium",
        "sentiment": sentiment if sentiment in SENTIMENTS else "Calm",
        "suggested_team": data.get("suggested_team", "Service Desk"),
        "troubleshooting_steps": ensure_list(data.get("troubleshooting_steps"), language),
        "first_response": data.get(
            "first_response",
            first_response_for(category=category if category in TRIAGE_CATEGORIES else "Other", priority=priority if priority in PRIORITIES else "Medium", language=language),
        ),
    }


def ensure_list(value: object, language: str = "en") -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        return [value]
    if language == "ja":
        return ["問い合わせ内容を確認します。", "直近の変更内容を確認します。", "業務に影響がある場合はエスカレーションします。"]
    return ["Confirm the issue details.", "Check recent changes.", "Escalate if the issue blocks work."]


def first_response_for(category: str, priority: str, language: str) -> str:
    if language == "ja":
        return (
            "ITサポートへお問い合わせいただきありがとうございます。お問い合わせ内容を受け付けました。"
            f"{PRIORITY_LABELS['ja'].get(priority, priority)}優先度の"
            f"{CATEGORY_LABELS['ja'].get(category, category)}関連のチケットとして、初期確認を進めます。"
            "追加確認が必要な場合がありますので、端末を利用できる状態にしてお待ちください。"
        )

    return (
        "Thank you for contacting IT Support. We have received your request and will begin "
        f"troubleshooting it as a {priority.lower()} priority {category.lower()} issue. "
        "Please keep your device available in case we need additional details."
    )


def troubleshooting_steps_for(category: str, language: str = "en") -> list[str]:
    steps_en = {
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
    steps_ja = {
        "Network": [
            "ユーザーが自宅Wi-Fi、社内LAN、VPNのどれを利用しているか確認します。",
            "VPNクライアントを再起動し、通常のインターネット接続が利用できるか確認します。",
            "ネットワークまたはVPNサービスの障害情報が出ていないか確認します。",
        ],
        "Printer": [
            "プリンター名、設置場所、他のユーザーにも影響しているかを確認します。",
            "プリンターの電源、用紙、トナー、印刷キュー、既定プリンター設定を確認します。",
            "必要に応じて印刷スプーラーの再起動、またはプリンターの再追加を行います。",
        ],
        "Email": [
            "Webメール、Outlook、モバイルメールのどこで問題が発生しているか確認します。",
            "認証情報、MFA通知、メールボックス状態、サービス正常性を確認します。",
            "Outlook Web Accessで切り分けを行い、クライアント側かアカウント側かを確認します。",
        ],
        "Account": [
            "社内手順に従ってユーザー本人確認を行います。",
            "アカウントロック、無効化、パスワードリセット要否を確認します。",
            "MFAの状態と直近のサインインエラーを確認します。",
        ],
        "Hardware": [
            "端末モデル、資産番号、物理的な症状を確認します。",
            "再起動と不要な周辺機器の取り外しを案内します。",
            "ハードウェア故障が疑われる場合は保証または交換手順を確認します。",
        ],
        "Software": [
            "アプリ名、エラーメッセージ、直近の変更内容を確認します。",
            "アプリと端末を再起動し、更新状況を確認します。",
            "パフォーマンス問題の場合は、スタートアップアプリ、空き容量、イベントログを確認します。",
        ],
        "Security": [
            "不審なリンクをクリックしたり証拠を削除したりしないよう案内します。",
            "送信者、URL、添付ファイル、スクリーンショットなどの情報を収集します。",
            "侵害が疑われる場合は、直ちにセキュリティ運用チームへエスカレーションします。",
        ],
        "Other": [
            "端末、ユーザー、場所、業務影響を確認します。",
            "問題を再現できるか、いつ発生し始めたかを確認します。",
            "初期確認後、適切な対応チームへ振り分けます。",
        ],
    }
    steps = steps_ja if language == "ja" else steps_en
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


def ticket_examples(language: str) -> list[str]:
    if language == "ja":
        return [
            "自宅からVPNに接続できません。",
            "ノートPCの動作がとても遅く、頻繁にフリーズします。",
            "会社のメールにアクセスできません。",
            "プリンターが動かず、至急印刷が必要です。",
        ]
    return [
        "I cannot connect to the VPN from home.",
        "My laptop is very slow and keeps freezing.",
        "I cannot access my company email.",
        "The printer is not working and I need it urgently.",
    ]


def kb_examples(language: str) -> list[str]:
    if language == "ja":
        return [
            "VPNに接続できない場合はどうすればいいですか？",
            "会社のメールにアクセスできない場合、何を確認すべきですか？",
            "Windows PCの動作が遅い場合、何を確認すべきですか？",
        ]
    return [
        "How do I troubleshoot VPN connection failure?",
        "What should I check when a user cannot access company email?",
        "What should I check when a Windows PC is running slowly?",
    ]


def render_triage_tab(provider: LLMProvider, language: str) -> None:
    st.subheader(t(language, "triage_subheader"))
    with st.expander(t(language, "help_title")):
        st.write(t(language, "triage_help"))

    issue = st.text_area(
        t(language, "issue_label"),
        height=140,
        placeholder=t(language, "issue_placeholder"),
    )

    selected_example = st.selectbox(t(language, "example_ticket_label"), [""] + ticket_examples(language))
    if selected_example and not issue:
        issue = selected_example
        st.info(issue)

    if st.button(t(language, "analyze_ticket"), type="primary"):
        if not issue.strip():
            st.error(t(language, "empty_issue_error"))
            return

        with st.spinner(t(language, "analyzing_ticket")):
            try:
                triage = provider.triage_ticket(issue, language)
            except Exception as exc:
                st.error(f"Could not analyze the ticket: {exc}")
                return

        columns = st.columns(3)
        columns[0].metric(t(language, "category"), display_value("category", triage["category"], language))
        columns[1].metric(t(language, "priority"), display_value("priority", triage["priority"], language))
        columns[2].metric(t(language, "sentiment"), display_value("sentiment", triage["sentiment"], language))

        st.markdown(f"**{t(language, 'suggested_team')}:** {triage['suggested_team']}")
        st.markdown(f"**{t(language, 'first_steps')}**")
        for step in triage["troubleshooting_steps"]:
            st.write(f"- {step}")

        st.markdown(f"**{t(language, 'professional_response')}**")
        st.success(triage["first_response"])


def render_kb_tab(provider: LLMProvider, language: str) -> None:
    st.subheader(t(language, "kb_subheader"))
    with st.expander(t(language, "help_title")):
        st.write(t(language, "kb_help"))

    try:
        knowledge_base = get_knowledge_base()
        chunk_count = knowledge_base.ensure_loaded()
    except Exception as exc:
        st.error(t(language, "kb_unavailable", error=exc))
        return

    left, right = st.columns([2, 1])
    left.caption(t(language, "loaded_chunks", count=chunk_count))
    if right.button(t(language, "reload_kb")):
        with st.spinner(t(language, "reloading_kb")):
            chunk_count = knowledge_base.reload()
        st.success(t(language, "reloaded_kb", count=chunk_count))

    example_columns = st.columns(3)
    for index, example_question in enumerate(kb_examples(language)):
        if example_columns[index].button(example_question, key=f"kb_example_{language}_{index}"):
            st.session_state.kb_question = example_question

    question = st.text_input(
        t(language, "question_label"),
        placeholder=t(language, "question_placeholder"),
        key="kb_question",
    )

    if st.button(t(language, "search_kb"), type="primary"):
        if not question.strip():
            st.error(t(language, "empty_question_error"))
            return

        with st.spinner(t(language, "retrieving_docs")):
            chunks = unique_top_sources(knowledge_base.search(question, limit=6))

        if not chunks:
            st.warning(t(language, "no_matches"))
            return

        with st.spinner(t(language, "drafting_answer")):
            answer = answer_with_fallback(provider=provider, question=question, chunks=chunks, language=language)

        st.markdown(answer)

        with st.expander(t(language, "retrieved_sources")):
            for chunk in chunks:
                st.markdown(f"**{chunk.source} | score: {chunk.score:.1f}**")
                st.write(chunk.text)


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, layout="wide")
    st.title(APP_TITLE)

    provider = get_provider()
    with st.sidebar:
        selected_language = st.selectbox("Language / 言語", list(LANGUAGE_OPTIONS.keys()))
        language = LANGUAGE_OPTIONS[selected_language]
        st.header(t(language, "sidebar_header"))
        st.write(f"{t(language, 'provider_label')}: **{provider.name}**")
        st.markdown(t(language, "kb_sidebar"))

    st.caption(t(language, "app_caption"))

    triage_tab, kb_tab = st.tabs([t(language, "tab_triage"), t(language, "tab_kb")])
    with triage_tab:
        render_triage_tab(provider, language)
    with kb_tab:
        render_kb_tab(provider, language)


if __name__ == "__main__":
    main()
