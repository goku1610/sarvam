import os
import asyncio
import json
import re
import threading
import uuid
from typing import Any
from datetime import datetime
from urllib.parse import urlsplit, urlunsplit
from fastapi import FastAPI
from fastapi.responses import StreamingResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from google import genai
from google.genai import types
from filtering import build_context_from_pages
from search import WebSearchScraper


def load_local_env(env_path: str = ".env") -> None:
    if not os.path.exists(env_path):
        return

    with open(env_path, "r", encoding="utf-8") as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")

            # Preserve explicitly exported environment variables.
            if key and key not in os.environ:
                os.environ[key] = value


load_local_env()

app = FastAPI(title="Deep Research Agent")
frontend_dist_dir = os.path.join("frontend", "dist")
frontend_assets_dir = os.path.join(frontend_dist_dir, "assets")

if os.path.isdir(frontend_assets_dir):
    app.mount("/assets", StaticFiles(directory=frontend_assets_dir), name="assets")


class JsonSessionStore:
    def __init__(self, path: str = os.path.join("data", "sessions.json")):
        self.path = path
        self.lock = threading.Lock()
        os.makedirs(os.path.dirname(self.path), exist_ok=True)

    def _read(self) -> dict:
        if not os.path.exists(self.path):
            return {"sessions": {}}

        try:
            with open(self.path, "r", encoding="utf-8") as session_file:
                return json.load(session_file)
        except (json.JSONDecodeError, OSError):
            return {"sessions": {}}

    def _write(self, data: dict) -> None:
        with open(self.path, "w", encoding="utf-8") as session_file:
            json.dump(data, session_file, indent=2)

    def get_or_create(self, session_id: str | None = None) -> dict:
        now = datetime.now().isoformat()
        with self.lock:
            data = self._read()
            sessions = data.setdefault("sessions", {})
            if not session_id or session_id not in sessions:
                session_id = str(uuid.uuid4())
                sessions[session_id] = {
                    "session_id": session_id,
                    "created_at": now,
                    "updated_at": now,
                    "history": [],
                    "state": {},
                }
            self._write(data)
            return sessions[session_id]

    def get(self, session_id: str) -> dict | None:
        with self.lock:
            return self._read().get("sessions", {}).get(session_id)

    def delete(self, session_id: str) -> bool:
        with self.lock:
            data = self._read()
            sessions = data.setdefault("sessions", {})
            if session_id not in sessions:
                return False
            del sessions[session_id]
            self._write(data)
            return True

    def list_summaries(self) -> list[dict[str, Any]]:
        with self.lock:
            sessions = self._read().get("sessions", {})

        summaries = []
        for session in sessions.values():
            state = session.get("state", {})
            title = state.get("chat_title") or state.get("original_query") or "Untitled research"
            if not state.get("original_query") and not state.get("chat_title"):
                continue
            sort_at = state.get("history_sort_at") or session.get("updated_at") or session.get("created_at")

            summaries.append({
                "session_id": session.get("session_id"),
                "title": title,
                "original_query": state.get("original_query", ""),
                "updated_at": session.get("updated_at"),
                "created_at": session.get("created_at"),
                "sort_at": sort_at,
            })

        return sorted(
            summaries,
            key=lambda item: item.get("sort_at") or "",
            reverse=True,
        )

    def update_state(
        self,
        session_id: str,
        state: dict[str, Any],
        event: dict[str, Any] | None = None,
    ) -> dict:
        now = datetime.now().isoformat()
        with self.lock:
            data = self._read()
            sessions = data.setdefault("sessions", {})
            session = sessions.setdefault(
                session_id,
                {
                    "session_id": session_id,
                    "created_at": now,
                    "updated_at": now,
                    "history": [],
                    "state": {},
                },
            )
            session["state"] = {**session.get("state", {}), **state}
            if event and event.get("type") != "chat_renamed":
                session["state"]["history_sort_at"] = now
            session["updated_at"] = now
            if event:
                session.setdefault("history", []).append({"timestamp": now, **event})
            self._write(data)
            return session

    def append_message(self, session_id: str, role: str, content: str) -> dict:
        now = datetime.now().isoformat()
        with self.lock:
            data = self._read()
            sessions = data.setdefault("sessions", {})
            session = sessions.setdefault(
                session_id,
                {
                    "session_id": session_id,
                    "created_at": now,
                    "updated_at": now,
                    "history": [],
                    "state": {},
                },
            )
            session.setdefault("messages", []).append({
                "role": role,
                "content": content,
                "timestamp": now,
            })
            session["updated_at"] = now
            self._write(data)
            return session

    def record_turn(self, session_id: str, turn: dict[str, Any]) -> dict:
        now = datetime.now().isoformat()
        with self.lock:
            data = self._read()
            sessions = data.setdefault("sessions", {})
            session = sessions.setdefault(
                session_id,
                {
                    "session_id": session_id,
                    "created_at": now,
                    "updated_at": now,
                    "history": [],
                    "state": {},
                },
            )
            session.setdefault("turns", []).append({"timestamp": now, **turn})
            session["updated_at"] = now
            self._write(data)
            return session


session_store = JsonSessionStore()
ROLLING_SUMMARY_BATCH_SIZE = 1
ZERO_RESULT_SEARCH_RETRY_LIMIT = 2


# Define the data model for the incoming request
class QueryRequest(BaseModel):
    session_id: str | None = None
    query: str
    deep_research: bool = False


class ClarifyingQuestionRequest(BaseModel):
    session_id: str | None = None
    query: str
    plan: list[str] = []
    search_queries: list[str] = []


class ClarifyingAnswer(BaseModel):
    question: str
    answer: str


class QueryRefinementRequest(BaseModel):
    session_id: str | None = None
    query: str
    plan: list[str] = []
    search_queries: list[str] = []
    answers: list[ClarifyingAnswer] = []


class PlanRevisionRequest(BaseModel):
    session_id: str | None = None
    query: str
    plan: list[str] = []
    search_queries: list[str] = []
    revision_request: str
    deep_research: bool = False


class SearchRequest(BaseModel):
    session_id: str | None = None
    query: str = ""
    queries: list[str]


class SearchResultSummary(BaseModel):
    title: str = ""
    url: str = ""
    domain: str = ""
    content: str = ""


class FollowUpQueryRequest(BaseModel):
    session_id: str | None = None
    query: str
    plan: list[str] = []
    searched_queries: list[str] = []
    sources: list[SearchResultSummary] = []
    iteration: int = 1


class AnswerRequest(BaseModel):
    session_id: str | None = None
    query: str
    plan: list[str] = []
    search_queries: list[str] = []
    context: str = ""
    chunks: list[dict[str, Any]] = []


class ContinueChatRequest(BaseModel):
    session_id: str
    message: str


class SessionRequest(BaseModel):
    session_id: str | None = None


class SessionStateUpdate(BaseModel):
    state: dict[str, Any] = {}
    event: dict[str, Any] | None = None


def parse_json_object(raw_output: str) -> dict:
    cleaned_output = raw_output.strip()
    if cleaned_output.startswith("```"):
        cleaned_output = cleaned_output.strip("`")
        cleaned_output = cleaned_output.removeprefix("json").strip()
    return json.loads(cleaned_output)


def trim_text(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0] + "\n[Trimmed for context budget.]"


def normalize_citation_url(url: str) -> str:
    """Normalize URLs enough to compare LLM citations against retrieved sources."""
    cleaned_url = url.strip().rstrip(".,;:")
    try:
        parsed = urlsplit(cleaned_url)
    except ValueError:
        return cleaned_url.rstrip("/").lower()

    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower().removeprefix("www.")
    path = parsed.path.rstrip("/")
    return urlunsplit((scheme, netloc, path, parsed.query, ""))


def validate_answer_citations(answer: str, chunks: list[dict[str, Any]]) -> tuple[str, dict[str, Any]]:
    """Keep only citations whose URLs came from selected source chunks."""
    allowed_sources: dict[str, dict[str, str]] = {}
    for chunk in chunks:
        url = str(chunk.get("url", "")).strip()
        if not url:
            continue
        normalized_url = normalize_citation_url(url)
        allowed_sources[normalized_url] = {
            "url": url,
            "title": str(chunk.get("title", "Unknown Title")).strip() or "Unknown Title",
            "domain": str(chunk.get("domain", "")).strip(),
        }

    citation_pattern = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")
    removed_count = 0
    corrected_count = 0

    def replace_citation(match: re.Match) -> str:
        nonlocal removed_count, corrected_count
        label = match.group(1).strip()
        cited_url = match.group(2).strip()
        source = allowed_sources.get(normalize_citation_url(cited_url))

        if not source:
            removed_count += 1
            return f"{label} [unverified citation removed]"

        canonical_label = f"{source['title']} — {source['domain']}" if source["domain"] else source["title"]
        canonical_citation = f"[{canonical_label}]({source['url']})"
        if canonical_citation != match.group(0):
            corrected_count += 1
        return canonical_citation

    validated_answer = citation_pattern.sub(replace_citation, answer)
    if removed_count:
        validated_answer += (
            f"\n\nCitation validation note: removed {removed_count} citation"
            f"{'' if removed_count == 1 else 's'} that did not match retrieved sources."
        )

    return validated_answer, {
        "allowed_url_count": len(allowed_sources),
        "corrected_citation_count": corrected_count,
        "removed_citation_count": removed_count,
    }


def score_turn_relevance(turn: dict[str, Any], query: str) -> int:
    query_terms = {
        term
        for term in re.findall(r"[a-z0-9]+", query.lower())
        if len(term) > 2
    }
    if not query_terms:
        return 0

    turn_text = f"{turn.get('query', '')} {turn.get('final_answer', '')}".lower()
    turn_terms = set(re.findall(r"[a-z0-9]+", turn_text))
    return len(query_terms & turn_terms)


def build_history_context(session: dict | None, max_chars: int = 5000, current_query: str = "") -> str:
    if not session:
        return ""

    state = session.get("state", {})
    messages = session.get("messages", [])
    turns = session.get("turns", [])
    parts = []
    rolling_summary = str(state.get("rolling_summary", "")).strip()

    if rolling_summary:
        parts.append(f"Conversation summary so far:\n{rolling_summary}")

    newest_messages = []
    for message in messages[-4:]:
        role = message.get("role", "unknown")
        content = trim_text(str(message.get("content", "")), 900)
        if content:
            newest_messages.append(f"{role}: {content}")
    if newest_messages:
        parts.append("Newest messages:\n" + "\n".join(newest_messages))

    relevant_turns = []
    if current_query.strip():
        scored_turns = [
            (score_turn_relevance(turn, current_query), index, turn)
            for index, turn in enumerate(turns)
        ]
        relevant_turns = [
            turn
            for score, _index, turn in sorted(scored_turns, key=lambda item: (item[0], item[1]), reverse=True)
            if score > 0
        ][:2]

    newest_turns = []
    selected_turns = relevant_turns or turns[-2:]
    for turn in selected_turns:
        query = turn.get("query", "")
        final_answer = trim_text(str(turn.get("final_answer", "")), 900)
        if query and final_answer:
            newest_turns.append(f"Prior turn query: {query}\nPrior answer excerpt: {final_answer}")
    if newest_turns:
        section_title = "Relevant prior turns" if relevant_turns else "Newest completed turns"
        parts.append(f"{section_title}:\n" + "\n\n".join(newest_turns))

    return trim_text("\n\n".join(parts), max_chars)


def format_turns_for_summary(turns: list[dict[str, Any]]) -> str:
    formatted_turns = []
    for index, turn in enumerate(turns, start=1):
        query = trim_text(str(turn.get("query", "")), 700)
        answer = trim_text(str(turn.get("final_answer", "")), 1200)
        search_queries = turn.get("search_queries_issued", [])
        formatted_turns.append(
            f"Turn {index}\n"
            f"User query: {query}\n"
            f"Search queries: {json.dumps(search_queries)}\n"
            f"Assistant answer: {answer}"
        )
    return "\n\n".join(formatted_turns)


class ResearchPlanner:
    def __init__(self):
        if not os.environ.get("GEMINI_API_KEY"):
            raise ValueError(
                "GEMINI_API_KEY is missing. Add it to .env or export it before starting the server."
            )

        self.client = genai.Client()
        self.model_name = "gemini-3.1-flash-lite"

    def generate_plan_stream(self, user_query: str, deep_research: bool = False):
        current_date = datetime.now().strftime("%B %d, %Y")
        research_mode_instructions = (
            "Deep research mode is ON. Produce a more comprehensive plan that expects broader coverage, "
            "more source discovery, and iterative follow-up after the first batch of documents is reviewed. "
            "Generate 5 to 7 search queries that support multiple passes of research."
            if deep_research
            else "Deep research mode is OFF. Produce a lighter-weight research plan that retrieves a smaller set "
            "of high-value documents, performs only one retrieval pass, and does not plan any further iteration "
            "after the initial documents are collected. Generate 2 to 3 search queries focused on the fastest "
            "path to a good answer."
        )
        system_prompt = (
            "You are an expert research planner. Create a concise chat title, break down the question into "
            "a brief 2-sentence strategy, and generate a list of highly effective search queries.\n"
            f"Today's date is {current_date}. Use this date when the topic depends on timeliness, recency, or current events.\n\n"
            f"{research_mode_instructions}\n\n"
            "You must use the following structural token boundaries precisely in your output format:\n"
            "<TITLE_START>\n[A 3 to 6 word title for this research chat]\n<TITLE_END>\n"
            "<PLAN_START>\n[Your 2-sentence plan goes here]\n<PLAN_END>\n"
            "<QUERIES_START>\n[\"query 1\", \"query 2\"]\n<QUERIES_END>\n\n"
            "Do not include any conversational intro or wrap-up prose outside these tokens."
        )

        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=f"{system_prompt}\n\nUser Query: {user_query}"),
                ],
            ),
        ]

        # Use the configuration provided to minimize thinking overhead for maximum speed
        generate_content_config = types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(
                thinking_level="MINIMAL",
            ),
            temperature=0.2,
        )

        try:
            # Call the stream API via the official genai client
            response_stream = self.client.models.generate_content_stream(
                model=self.model_name,
                contents=contents,
                config=generate_content_config,
            )
            
            for chunk in response_stream:
                if chunk.text:
                    yield chunk.text
                    
        except Exception as e:
            # Secure token-enclosed fallback if API limits are hit or network drops
            fallback_title = user_query[:48].strip() or "Research chat"
            yield f"<TITLE_START>\n{fallback_title}\n<TITLE_END>\n<PLAN_START>\nFallback strategy triggered due to system error: {str(e)}\n<PLAN_END>\n<QUERIES_START>\n[\"{user_query}\"]\n<QUERIES_END>"

    def generate_clarifying_questions(
        self,
        user_query: str,
        plan: list[str],
        search_queries: list[str],
    ) -> list[dict]:
        current_date = datetime.now().strftime("%B %d, %Y")
        prompt = (
            "You are helping refine a deep research route before document retrieval begins.\n"
            f"Today's date is {current_date}.\n\n"
            "Given the user's topic, draft up to 3 optional clarifying questions that would materially improve "
            "the search query set. Ask only questions that change what should be searched. Each question should "
            "include 2 to 4 concise prefilled options. Do not ask generic preference questions.\n\n"
            "Respond only with valid JSON in this exact shape:\n"
            "{\"questions\":[{\"question\":\"...\",\"options\":[\"option 1\",\"option 2\"]}]}\n\n"
            f"User topic: {user_query}\n"
            f"Current plan: {json.dumps(plan)}\n"
            f"Current search queries: {json.dumps(search_queries)}"
        )

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(thinking_level="MINIMAL"),
                    temperature=0.2,
                ),
            )
            parsed_response = parse_json_object(response.text or "{}")
            questions = parsed_response.get("questions", [])
            return [
                {
                    "question": str(question.get("question", "")).strip(),
                    "options": [
                        str(option).strip()
                        for option in question.get("options", [])
                        if str(option).strip()
                    ][:4],
                }
                for question in questions
                if str(question.get("question", "")).strip()
            ][:3]
        except Exception:
            return []

    def refine_search_queries(
        self,
        user_query: str,
        plan: list[str],
        search_queries: list[str],
        answers: list[ClarifyingAnswer],
    ) -> list[str]:
        if not answers:
            return search_queries

        prompt = (
            "You are refining a deep research search query set before retrieval starts.\n"
            "Use the user's clarifying answers to modify, remove, or add search queries. Keep only high-value "
            "queries and return 5 to 7 final queries. Do not include explanations.\n\n"
            "Respond only with valid JSON in this exact shape:\n"
            "{\"search_queries\":[\"query 1\",\"query 2\"]}\n\n"
            f"Original topic: {user_query}\n"
            f"Plan: {json.dumps(plan)}\n"
            f"Current search queries: {json.dumps(search_queries)}\n"
            f"Clarifying answers: {json.dumps([answer.model_dump() for answer in answers])}"
        )

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(thinking_level="MINIMAL"),
                    temperature=0.2,
                ),
            )
            parsed_response = parse_json_object(response.text or "{}")
            refined_queries = parsed_response.get("search_queries", [])
            return [
                str(search_query).strip()
                for search_query in refined_queries
                if str(search_query).strip()
            ][:7] or search_queries
        except Exception:
            return search_queries

    def revise_plan(
        self,
        user_query: str,
        plan: list[str],
        search_queries: list[str],
        revision_request: str,
        deep_research: bool = False,
    ) -> dict[str, Any]:
        current_date = datetime.now().strftime("%B %d, %Y")
        query_count_instruction = (
            "Return 5 to 7 search queries because deep research mode is active."
            if deep_research
            else "Return 2 to 4 search queries."
        )
        prompt = (
            "You are revising a web research plan before retrieval starts.\n"
            f"Today's date is {current_date}.\n"
            "Keep the original user question as the research goal, but adapt the plan and search queries to the "
            "user's revision request. The plan should be concise and operational, not a final answer. "
            f"{query_count_instruction}\n\n"
            "Respond only with valid JSON in this exact shape:\n"
            "{\"plan_steps\":[\"step 1\",\"step 2\"],\"search_queries\":[\"query 1\",\"query 2\"]}\n\n"
            f"Original user question: {user_query}\n"
            f"Current plan: {json.dumps(plan)}\n"
            f"Current search queries: {json.dumps(search_queries)}\n"
            f"Revision request: {revision_request}"
        )

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(thinking_level="MINIMAL"),
                    temperature=0.2,
                ),
            )
            parsed_response = parse_json_object(response.text or "{}")
            revised_plan = [
                str(step).strip()
                for step in parsed_response.get("plan_steps", [])
                if str(step).strip()
            ][:5]
            revised_queries = [
                str(search_query).strip()
                for search_query in parsed_response.get("search_queries", [])
                if str(search_query).strip()
            ][:7]
            return {
                "plan_steps": revised_plan or plan,
                "search_queries": revised_queries or search_queries,
            }
        except Exception:
            return {
                "plan_steps": plan,
                "search_queries": search_queries,
            }

    def generate_follow_up_queries(
        self,
        user_query: str,
        plan: list[str],
        searched_queries: list[str],
        sources: list[SearchResultSummary],
        iteration: int,
    ) -> list[str]:
        if not sources:
            return []

        source_summaries = [
            {
                "title": source.title,
                "url": source.url,
                "domain": source.domain,
                "snippet": source.content[:1200],
            }
            for source in sources[-12:]
        ]

        prompt = (
            "You are the iteration controller for a deep research agent.\n"
            "Review the user's research goal, plan, queries already searched, and source snippets already read. "
            "Decide whether another web-search pass is needed to fill important gaps, verify uncertain claims, "
            "or capture newer/primary sources. If the existing sources are enough, return an empty array. "
            "If another pass is useful, return 1 to 4 non-duplicative search queries. Do not repeat any already "
            "searched query. Do not include explanations.\n\n"
            "Respond only with valid JSON in this exact shape:\n"
            "{\"search_queries\":[\"query 1\"]}\n\n"
            f"Deep research iteration: {iteration}\n"
            f"Original topic: {user_query}\n"
            f"Plan: {json.dumps(plan)}\n"
            f"Already searched queries: {json.dumps(searched_queries)}\n"
            f"Sources read: {json.dumps(source_summaries)}"
        )

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(thinking_level="MINIMAL"),
                    temperature=0.2,
                ),
            )
            parsed_response = parse_json_object(response.text or "{}")
            already_searched = {
                searched_query.strip().lower()
                for searched_query in searched_queries
                if searched_query.strip()
            }
            follow_up_queries = []
            for search_query in parsed_response.get("search_queries", []):
                cleaned_query = str(search_query).strip()
                if cleaned_query and cleaned_query.lower() not in already_searched:
                    follow_up_queries.append(cleaned_query)
            return follow_up_queries[:4]
        except Exception:
            return []

    def generate_zero_result_queries(
        self,
        user_query: str,
        attempted_queries: list[str],
        max_queries: int = 4,
    ) -> list[str]:
        current_date = datetime.now().strftime("%B %d, %Y")
        prompt = (
            "A web research search batch returned zero usable links. Generate alternative search queries that "
            "are broader, use different wording, include likely official/primary-source terms when useful, and "
            "avoid repeating attempted queries. Do not answer the user.\n\n"
            f"Today's date is {current_date}.\n"
            f"User research goal: {user_query}\n"
            f"Attempted queries: {json.dumps(attempted_queries)}\n\n"
            "Respond only with valid JSON in this exact shape:\n"
            "{\"search_queries\":[\"query 1\",\"query 2\"]}"
        )

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(thinking_level="MINIMAL"),
                    temperature=0.25,
                ),
            )
            parsed_response = parse_json_object(response.text or "{}")
            attempted = {
                attempted_query.strip().lower()
                for attempted_query in attempted_queries
                if attempted_query.strip()
            }
            recovery_queries = []
            for query in parsed_response.get("search_queries", []):
                cleaned_query = str(query).strip()
                if cleaned_query and cleaned_query.lower() not in attempted:
                    recovery_queries.append(cleaned_query)
            return recovery_queries[:max_queries]
        except Exception:
            return []

    def plan_chat_research(
        self,
        user_message: str,
        history_context: str,
        prior_context: str,
    ) -> dict[str, Any]:
        current_date = datetime.now().strftime("%B %d, %Y")
        prompt = (
            "You are deciding whether a follow-up in a deep research chat needs fresh web research.\n"
            f"Today's date is {current_date}.\n\n"
            "Use fresh search when the user asks for a comparison/entity/metric/source that is missing from the "
            "saved evidence, when they ask for current/latest data, or when answering would require facts not "
            "already present. Do not search for simple summarization, rephrasing, explanation, or formatting of "
            "already available evidence.\n\n"
            "Respond only with valid JSON in this exact shape:\n"
            "{\"needs_search\":true,\"search_queries\":[\"query 1\"],\"reason\":\"short reason\"}\n\n"
            f"User follow-up: {user_message}\n\n"
            f"Prior conversation summary/recent turns:\n{history_context or 'None'}\n\n"
            f"Saved selected web context excerpt:\n{trim_text(prior_context, 6000) or 'None'}"
        )

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(thinking_level="MINIMAL"),
                    temperature=0.1,
                ),
            )
            parsed_response = parse_json_object(response.text or "{}")
            queries = [
                str(query).strip()
                for query in parsed_response.get("search_queries", [])
                if str(query).strip()
            ][:3]
            needs_search = bool(parsed_response.get("needs_search")) and bool(queries)
            return {
                "needs_search": needs_search,
                "search_queries": queries if needs_search else [],
                "reason": str(parsed_response.get("reason", "")).strip(),
            }
        except Exception:
            return {
                "needs_search": False,
                "search_queries": [],
                "reason": "search decision failed",
            }

    def generate_answer_stream(
        self,
        user_query: str,
        plan: list[str],
        search_queries: list[str],
        web_context: str,
        chunks: list[dict[str, Any]],
        history_context: str = "",
    ):
        source_catalog = [
            {
                "source_id": chunk.get("source_id", index + 1),
                "title": chunk.get("title", "Unknown Title"),
                "domain": chunk.get("domain", ""),
                "url": chunk.get("url", ""),
            }
            for index, chunk in enumerate(chunks)
        ]
        current_date = datetime.now().strftime("%B %d, %Y")
        prompt = (
            "You are a deep research answer writer. Answer only from the supplied web context and relevant "
            "conversation context. Do not invent sources. For every claim-heavy sentence or paragraph, cite the "
            "supporting source using this exact shape: [Title — domain](URL). If sources disagree, explicitly "
            "state the disagreement and cite both sides. If evidence is weak or missing, say so and propose the "
            "next research step. Keep the response clear, useful, and grounded.\n\n"
            f"Today's date: {current_date}\n"
            f"User query: {user_query}\n"
            f"Research plan: {json.dumps(plan)}\n"
            f"Search queries issued: {json.dumps(search_queries)}\n"
            f"Relevant prior conversation/turns:\n{history_context or 'None'}\n\n"
            f"Source catalog:\n{json.dumps(source_catalog, indent=2)}\n\n"
            f"Selected web context:\n{web_context}\n\n"
            "Now produce the final answer with citations."
        )

        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=prompt)],
            ),
        ]
        config = types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_level="MINIMAL"),
            temperature=0.2,
        )

        try:
            response_stream = self.client.models.generate_content_stream(
                model=self.model_name,
                contents=contents,
                config=config,
            )
            for chunk in response_stream:
                if chunk.text:
                    yield chunk.text
        except Exception as error:
            yield (
                "I could not generate the final synthesis because the LLM call failed. "
                f"Available evidence was collected from {len(source_catalog)} selected source snippets. "
                f"Error: {error}"
            )

    def generate_context_chat_stream(
        self,
        user_message: str,
        history_context: str,
        prior_web_context: str,
        chunks: list[dict[str, Any]],
    ):
        source_catalog = [
            {
                "source_id": chunk.get("source_id", index + 1),
                "title": chunk.get("title", "Unknown Title"),
                "domain": chunk.get("domain", ""),
                "url": chunk.get("url", ""),
            }
            for index, chunk in enumerate(chunks)
        ]
        current_date = datetime.now().strftime("%B %d, %Y")
        prompt = (
            "You are continuing the same deep research chat after an initial research answer. "
            "Use the prior conversation context and previously selected web evidence to answer the user's "
            "follow-up. Keep continuity with the session. For claim-heavy statements that rely on the saved "
            "web evidence, cite the source using this exact shape: [Title — domain](URL). If the follow-up asks "
            "for facts that are not supported by the saved evidence, say that the existing research context is "
            "insufficient and propose the next search needed. Do not invent sources.\n\n"
            f"Today's date: {current_date}\n"
            f"User follow-up: {user_message}\n\n"
            f"Relevant prior conversation/turns:\n{history_context or 'None'}\n\n"
            f"Saved source catalog:\n{json.dumps(source_catalog, indent=2)}\n\n"
            f"Saved selected web context:\n{prior_web_context or 'None'}\n\n"
            "Now answer the follow-up."
        )

        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=prompt)],
            ),
        ]
        config = types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_level="MINIMAL"),
            temperature=0.2,
        )

        try:
            response_stream = self.client.models.generate_content_stream(
                model=self.model_name,
                contents=contents,
                config=config,
            )
            for chunk in response_stream:
                if chunk.text:
                    yield chunk.text
        except Exception as error:
            yield f"I could not continue the chat because the LLM call failed. Error: {error}"

    def update_rolling_summary(
        self,
        existing_summary: str,
        new_turns_text: str,
        max_words: int = 200,
    ) -> str:
        prompt = (
            "Update a cached rolling conversation summary for a deep research agent.\n"
            "Preserve durable user goals, constraints, decisions, named entities, and useful findings. "
            "Do not include transient UI details or implementation chatter unless it affects future answers. "
            f"Keep the summary under {max_words} words.\n\n"
            f"Existing summary:\n{existing_summary or 'None yet.'}\n\n"
            f"Newest completed turns to merge:\n{new_turns_text}\n\n"
            "Return only the updated summary paragraph."
        )

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    thinking_config=types.ThinkingConfig(thinking_level="MINIMAL"),
                    temperature=0.1,
                ),
            )
            return trim_text((response.text or "").strip(), 1600)
        except Exception:
            fallback_summary = f"{existing_summary}\n\nRecent turns:\n{new_turns_text}".strip()
            return trim_text(fallback_summary, 1600)


async def refresh_rolling_summary_if_needed(session_id: str) -> None:
    session = session_store.get(session_id)
    if not session:
        return

    state = session.get("state", {})
    turns = session.get("turns", [])
    summarized_turn_count = int(state.get("rolling_summary_turn_count", 0) or 0)
    unsummarized_count = len(turns) - summarized_turn_count
    if unsummarized_count < ROLLING_SUMMARY_BATCH_SIZE:
        return

    new_turns = turns[summarized_turn_count:]
    new_turns_text = format_turns_for_summary(new_turns)
    if not new_turns_text.strip():
        return

    try:
        planner = ResearchPlanner()
        updated_summary = await asyncio.to_thread(
            planner.update_rolling_summary,
            str(state.get("rolling_summary", "")).strip(),
            new_turns_text,
        )
        session_store.update_state(
            session_id,
            {
                "rolling_summary": updated_summary,
                "rolling_summary_turn_count": len(turns),
                "rolling_summary_updated_at": datetime.now().isoformat(),
            },
            None,
        )
    except Exception as error:
        print(f"Rolling summary update failed for session {session_id}: {error}")


@app.post("/api/sessions")
async def get_or_create_session(request: SessionRequest):
    return session_store.get_or_create(request.session_id)


@app.get("/api/sessions")
async def list_sessions():
    return {"sessions": session_store.list_summaries()}


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    session = session_store.get(session_id)
    if session is None:
        session = session_store.get_or_create(session_id)
    return session


@app.patch("/api/sessions/{session_id}")
async def update_session_state(session_id: str, request: SessionStateUpdate):
    return session_store.update_state(session_id, request.state, request.event)


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    deleted = session_store.delete(session_id)
    return {"deleted": deleted}


@app.post("/api/plan")
async def generate_plan(request: QueryRequest):
    planner = ResearchPlanner()
    if request.session_id:
        session_store.append_message(request.session_id, "user", request.query)
        session_store.update_state(
            request.session_id,
            {
                "original_query": request.query,
                "deep_research_active": request.deep_research,
            },
            {"type": "plan_requested", "query": request.query, "deep_research": request.deep_research},
        )
    
    async def event_generator():
        # Stream chunks directly to the custom client
        for token in planner.generate_plan_stream(request.query, request.deep_research):
            yield token
            await asyncio.sleep(0.005) # Yield execution control
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/api/clarifying-questions")
async def generate_clarifying_questions(request: ClarifyingQuestionRequest):
    planner = ResearchPlanner()
    questions = planner.generate_clarifying_questions(
        request.query,
        request.plan,
        request.search_queries,
    )
    if request.session_id:
        session_store.update_state(
            request.session_id,
            {"clarifying_questions": questions},
            {"type": "clarifying_questions_generated", "count": len(questions)},
        )
    return {"questions": questions}


@app.post("/api/refine-queries")
async def refine_queries(request: QueryRefinementRequest):
    planner = ResearchPlanner()
    search_queries = planner.refine_search_queries(
        request.query,
        request.plan,
        request.search_queries,
        request.answers,
    )
    if request.session_id:
        session_store.update_state(
            request.session_id,
            {"queries": search_queries, "selected_queries": search_queries},
            {"type": "queries_refined", "count": len(search_queries)},
        )
    return {"search_queries": search_queries}


@app.post("/api/revise-plan")
async def revise_plan(request: PlanRevisionRequest):
    planner = ResearchPlanner()
    revision = planner.revise_plan(
        request.query,
        request.plan,
        request.search_queries,
        request.revision_request,
        request.deep_research,
    )
    if request.session_id:
        session_store.update_state(
            request.session_id,
            {
                "plan_steps": revision["plan_steps"],
                "queries": revision["search_queries"],
                "selected_queries": revision["search_queries"],
                "clarifying_questions": [],
                "clarifying_answers": [],
                "clarifying_complete": not request.deep_research,
            },
            {
                "type": "plan_revised",
                "revision_request": request.revision_request,
                "query_count": len(revision["search_queries"]),
            },
        )
    return revision


@app.post("/api/search")
async def execute_search(request: SearchRequest):
    scraper = WebSearchScraper()
    queries = [query.strip() for query in request.queries if query.strip()]
    if request.session_id:
        session_store.update_state(
            request.session_id,
            {"selected_queries": queries},
            {"type": "search_started", "queries": queries},
        )

    async def event_generator():
        if not queries:
            yield json.dumps({"type": "error", "message": "No search queries selected."}) + "\n"
            return

        try:
            attempted_queries = queries[:]
            active_queries = queries[:]
            valid_pages = []
            for retry_index in range(ZERO_RESULT_SEARCH_RETRY_LIMIT + 1):
                yield json.dumps({
                    "type": "progress",
                    "message": "Searching the web" if retry_index == 0 else "Retrying with broader search queries",
                    "queries": active_queries,
                }) + "\n"
                valid_pages = await scraper.execute_concurrent_research(active_queries)
                if valid_pages:
                    break

                try:
                    recovery_queries = await asyncio.to_thread(
                        ResearchPlanner().generate_zero_result_queries,
                        request.query or " ".join(queries),
                        attempted_queries,
                    )
                except Exception:
                    recovery_queries = []
                recovery_queries = [
                    query
                    for query in recovery_queries
                    if query.strip().lower() not in {attempted_query.lower() for attempted_query in attempted_queries}
                ]
                if not recovery_queries:
                    break

                attempted_queries.extend(recovery_queries)
                active_queries = recovery_queries

            yield json.dumps({"type": "progress", "message": "Fetching and cleaning sources"}) + "\n"

            for page in valid_pages:
                yield json.dumps({
                    "type": "result",
                    "title": page["title"],
                    "url": page["url"],
                    "domain": page["domain"],
                    "content": page["content"][:300],
                    "snippet": page.get("snippet", ""),
                    "score": page.get("score"),
                    "retrieved_at": page.get("retrieved_at", ""),
                    "query": page.get("query", ""),
                    "rank": page.get("rank"),
                }) + "\n"
                await asyncio.sleep(0)

            yield json.dumps({"type": "progress", "message": "Selecting relevant context"}) + "\n"
            research_context = build_context_from_pages(
                request.query or " ".join(queries),
                valid_pages,
            )
            if request.session_id:
                session_store.update_state(
                    request.session_id,
                    {
                        "opened_urls": [page["url"] for page in valid_pages],
                        "fetched_pages": valid_pages,
                        "research_context": research_context,
                        "selected_queries": attempted_queries,
                    },
                    {
                        "type": "context_selected",
                        "opened_url_count": len(valid_pages),
                        "attempted_query_count": len(attempted_queries),
                        "selected_count": research_context["selected_count"],
                        "unreachable_count": research_context.get("unreachable_count", 0),
                    },
                )
            yield json.dumps({
                "type": "context_ready",
                "chunks": research_context["chunks"],
                "context": research_context["context"],
                "chunk_count": research_context["chunk_count"],
                "selected_count": research_context["selected_count"],
                "unreachable_count": research_context.get("unreachable_count", 0),
                "attempted_queries": attempted_queries,
            }) + "\n"
            yield json.dumps({"type": "done"}) + "\n"
        except Exception as error:
            yield json.dumps({"type": "error", "message": str(error)}) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")


@app.post("/api/answer")
async def generate_answer(request: AnswerRequest):
    planner = ResearchPlanner()
    session = session_store.get(request.session_id) if request.session_id else None
    history_context = build_history_context(session, current_query=request.query)
    context = trim_text(request.context, 28000)

    async def event_generator():
        if not context.strip():
            yield json.dumps({
                "type": "error",
                "message": "No selected web context is available for answer generation.",
            }) + "\n"
            return

        yield json.dumps({"type": "progress", "message": "Generating answer with citations"}) + "\n"
        final_answer_parts = []
        for token in planner.generate_answer_stream(
            user_query=request.query,
            plan=request.plan,
            search_queries=request.search_queries,
            web_context=context,
            chunks=request.chunks,
            history_context=history_context,
        ):
            final_answer_parts.append(token)
            yield json.dumps({"type": "token", "text": token}) + "\n"
            await asyncio.sleep(0)

        raw_answer = "".join(final_answer_parts).strip()
        final_answer, citation_validation = validate_answer_citations(raw_answer, request.chunks)
        if request.session_id:
            session_store.append_message(request.session_id, "assistant", final_answer)
            session_store.record_turn(
                request.session_id,
                {
                    "query": request.query,
                    "search_queries_issued": request.search_queries,
                    "urls_opened": sorted({
                        chunk.get("url", "")
                        for chunk in request.chunks
                        if chunk.get("url")
                    }),
                    "context_snippets_selected": request.chunks,
                    "final_answer": final_answer,
                    "citation_validation": citation_validation,
                },
            )
            session_store.update_state(
                request.session_id,
                {
                    "final_answer": final_answer,
                    "citation_validation": citation_validation,
                },
                {
                    "type": "answer_generated",
                    "citation_source_count": len(request.chunks),
                    **citation_validation,
                },
            )
            asyncio.create_task(refresh_rolling_summary_if_needed(request.session_id))

        yield json.dumps({"type": "done", "answer": final_answer}) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")


@app.post("/api/chat")
async def continue_chat(request: ContinueChatRequest):
    planner = ResearchPlanner()
    scraper = WebSearchScraper()
    user_message = request.message.strip()
    if not user_message:
        async def empty_message_event():
            yield json.dumps({"type": "error", "message": "Message is required."}) + "\n"

        return StreamingResponse(empty_message_event(), media_type="application/x-ndjson")

    session_store.append_message(request.session_id, "user", user_message)
    session = session_store.get(request.session_id)
    state = session.get("state", {}) if session else {}
    research_context = state.get("research_context") if isinstance(state.get("research_context"), dict) else {}
    fetched_pages = state.get("fetched_pages") if isinstance(state.get("fetched_pages"), list) else []
    recontextualized_context = (
        build_context_from_pages(user_message, fetched_pages)
        if fetched_pages
        else research_context
    )
    prior_context = trim_text(str(recontextualized_context.get("context", "")), 18000)
    prior_chunks = recontextualized_context.get("chunks", [])
    if not isinstance(prior_chunks, list):
        prior_chunks = []
    history_context = build_history_context(session, current_query=user_message)

    async def event_generator():
        if not session:
            yield json.dumps({"type": "error", "message": "Session was not found."}) + "\n"
            return

        if fetched_pages:
            yield json.dumps({"type": "progress", "message": "Re-selecting saved source context"}) + "\n"
            session_store.update_state(
                request.session_id,
                {"research_context": recontextualized_context},
                {
                    "type": "chat_context_reselected",
                    "selected_count": recontextualized_context.get("selected_count", 0),
                    "unreachable_count": recontextualized_context.get("unreachable_count", 0),
                },
            )
            yield json.dumps({
                "type": "context_ready",
                "chunks": recontextualized_context.get("chunks", []),
                "context": recontextualized_context.get("context", ""),
                "chunk_count": recontextualized_context.get("chunk_count", 0),
                "selected_count": recontextualized_context.get("selected_count", 0),
                "unreachable_count": recontextualized_context.get("unreachable_count", 0),
                "reused_saved_sources": True,
            }) + "\n"

        yield json.dumps({"type": "progress", "message": "Checking whether fresh research is needed"}) + "\n"
        chat_research_plan = await asyncio.to_thread(
            planner.plan_chat_research,
            user_message,
            history_context,
            prior_context,
        )
        search_queries = chat_research_plan.get("search_queries", [])
        fresh_context = {"chunks": [], "context": "", "unreachable_count": 0}
        opened_urls: list[str] = []

        if chat_research_plan.get("needs_search") and search_queries:
            attempted_queries = search_queries[:]
            active_queries = search_queries[:]
            valid_pages = []
            for retry_index in range(ZERO_RESULT_SEARCH_RETRY_LIMIT + 1):
                yield json.dumps({
                    "type": "progress",
                    "message": (
                        "Searching the web for follow-up context"
                        if retry_index == 0
                        else "Retrying follow-up search with broader queries"
                    ),
                    "queries": active_queries,
                }) + "\n"
                valid_pages = await scraper.execute_concurrent_research(active_queries)
                if valid_pages:
                    break

                try:
                    recovery_queries = await asyncio.to_thread(
                        planner.generate_zero_result_queries,
                        user_message,
                        attempted_queries,
                    )
                except Exception:
                    recovery_queries = []
                recovery_queries = [
                    query
                    for query in recovery_queries
                    if query.strip().lower() not in {attempted_query.lower() for attempted_query in attempted_queries}
                ]
                if not recovery_queries:
                    break

                attempted_queries.extend(recovery_queries)
                active_queries = recovery_queries

            search_queries = attempted_queries

            yield json.dumps({"type": "progress", "message": "Fetching and cleaning follow-up sources"}) + "\n"
            for page in valid_pages:
                opened_urls.append(page.get("url", ""))
                yield json.dumps({
                    "type": "result",
                    "title": page.get("title", ""),
                    "url": page.get("url", ""),
                    "domain": page.get("domain", ""),
                    "content": page.get("content", "")[:300],
                    "snippet": page.get("snippet", ""),
                    "score": page.get("score"),
                    "retrieved_at": page.get("retrieved_at", ""),
                    "query": page.get("query", ""),
                    "rank": page.get("rank"),
                    "content_unreachable": page.get("content_unreachable", False),
                }) + "\n"
                await asyncio.sleep(0)

            yield json.dumps({"type": "progress", "message": "Selecting follow-up context"}) + "\n"
            fresh_context = build_context_from_pages(user_message, valid_pages)
            combined_context_text = trim_text(
                f"Previously selected context:\n{prior_context or 'None'}\n\n"
                f"Fresh follow-up context:\n{fresh_context['context'] or 'None'}",
                28000,
            )
            combined_research_context = {
                "chunks": prior_chunks + fresh_context["chunks"],
                "context": combined_context_text,
                "chunk_count": len(prior_chunks) + fresh_context["chunk_count"],
                "selected_count": len(prior_chunks) + fresh_context["selected_count"],
                "unreachable_count": fresh_context.get("unreachable_count", 0),
                "max_context_chars": fresh_context.get("max_context_chars", 24000),
            }
            session_store.update_state(
                request.session_id,
                {
                    "research_context": combined_research_context,
                    "fetched_pages": fetched_pages + valid_pages,
                    "last_chat_search_queries": search_queries,
                },
                {
                    "type": "chat_follow_up_researched",
                    "query_count": len(search_queries),
                    "opened_url_count": len(opened_urls),
                    "selected_count": fresh_context["selected_count"],
                    "unreachable_count": fresh_context.get("unreachable_count", 0),
                },
            )
            yield json.dumps({
                "type": "context_ready",
                "chunks": fresh_context["chunks"],
                "context": fresh_context["context"],
                "chunk_count": fresh_context["chunk_count"],
                "selected_count": fresh_context["selected_count"],
                "unreachable_count": fresh_context.get("unreachable_count", 0),
                "attempted_queries": search_queries,
            }) + "\n"

        yield json.dumps({"type": "progress", "message": "Generating answer with citations"}) + "\n"
        answer_context = prior_context
        answer_chunks = prior_chunks
        if fresh_context.get("context"):
            answer_context = trim_text(
                f"Previously selected context:\n{prior_context or 'None'}\n\n"
                f"Fresh follow-up context:\n{fresh_context['context']}",
                28000,
            )
            answer_chunks = prior_chunks + fresh_context.get("chunks", [])

        answer_parts = []
        for token in planner.generate_answer_stream(
            user_query=user_message,
            plan=[
                "Answer the follow-up using the prior conversation context.",
                (
                    "Fresh web research was run because saved evidence was insufficient."
                    if search_queries
                    else "No fresh search was needed; use saved research context."
                ),
            ],
            search_queries=search_queries,
            web_context=answer_context,
            chunks=answer_chunks,
            history_context=history_context,
        ):
            answer_parts.append(token)
            yield json.dumps({"type": "token", "text": token}) + "\n"
            await asyncio.sleep(0)

        raw_answer = "".join(answer_parts).strip()
        final_answer, citation_validation = validate_answer_citations(raw_answer, answer_chunks)
        session_store.append_message(request.session_id, "assistant", final_answer)
        session_store.record_turn(
            request.session_id,
            {
                "query": user_message,
                "search_queries_issued": search_queries,
                "urls_opened": sorted({url for url in opened_urls if url}),
                "context_snippets_selected": answer_chunks,
                "final_answer": final_answer,
                "citation_validation": citation_validation,
                "answered_from_existing_context": not bool(search_queries),
                "follow_up_search_reason": chat_research_plan.get("reason", ""),
            },
        )
        session_store.update_state(
            request.session_id,
            {
                "last_chat_answer": final_answer,
                "citation_validation": citation_validation,
            },
            {
                "type": "chat_message_answered",
                "citation_source_count": len(answer_chunks),
                "searched_follow_up": bool(search_queries),
                **citation_validation,
            },
        )
        asyncio.create_task(refresh_rolling_summary_if_needed(request.session_id))

        yield json.dumps({"type": "done", "answer": final_answer}) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")


@app.post("/api/follow-up-queries")
async def generate_follow_up_queries(request: FollowUpQueryRequest):
    planner = ResearchPlanner()
    search_queries = planner.generate_follow_up_queries(
        request.query,
        request.plan,
        request.searched_queries,
        request.sources,
        request.iteration,
    )
    if request.session_id:
        session_store.update_state(
            request.session_id,
            {"last_follow_up_queries": search_queries},
            {
                "type": "follow_up_queries_checked",
                "iteration": request.iteration,
                "count": len(search_queries),
            },
        )
    return {"search_queries": search_queries}

# Serve the custom HTML frontend on the root URL
@app.get("/")
async def get_ui():
    frontend_index_path = os.path.join(frontend_dist_dir, "index.html")
    if os.path.exists(frontend_index_path):
        return FileResponse(frontend_index_path)
    return HTMLResponse(
        content=(
            "<h1>Frontend build not found.</h1>"
            "<p>Run <code>npm install</code> and <code>npm run build</code> in the <code>frontend</code> directory.</p>"
        )
    )
