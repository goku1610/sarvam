import os
import asyncio
import json
import threading
import uuid
from typing import Any
from datetime import datetime
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

    def list_summaries(self) -> list[dict[str, Any]]:
        with self.lock:
            sessions = self._read().get("sessions", {})

        summaries = []
        for session in sessions.values():
            state = session.get("state", {})
            title = state.get("chat_title") or state.get("original_query") or "Untitled research"
            if not state.get("original_query") and not state.get("chat_title"):
                continue

            summaries.append({
                "session_id": session.get("session_id"),
                "title": title,
                "original_query": state.get("original_query", ""),
                "updated_at": session.get("updated_at"),
                "created_at": session.get("created_at"),
            })

        return sorted(
            summaries,
            key=lambda item: item.get("updated_at") or item.get("created_at") or "",
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
            session["updated_at"] = now
            if event:
                session.setdefault("history", []).append({"timestamp": now, **event})
            self._write(data)
            return session


session_store = JsonSessionStore()


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


@app.post("/api/plan")
async def generate_plan(request: QueryRequest):
    planner = ResearchPlanner()
    if request.session_id:
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
            valid_pages = await scraper.execute_concurrent_research(queries)

            for page in valid_pages:
                yield json.dumps({
                    "type": "result",
                    "title": page["title"],
                    "url": page["url"],
                    "domain": page["domain"],
                    "content": page["content"][:300],
                    "query": page.get("query", ""),
                    "rank": page.get("rank"),
                }) + "\n"
                await asyncio.sleep(0)

            research_context = build_context_from_pages(
                request.query or " ".join(queries),
                valid_pages,
            )
            yield json.dumps({
                "type": "context_ready",
                "chunks": research_context["chunks"],
                "context": research_context["context"],
                "chunk_count": research_context["chunk_count"],
                "selected_count": research_context["selected_count"],
            }) + "\n"
            yield json.dumps({"type": "done"}) + "\n"
        except Exception as error:
            yield json.dumps({"type": "error", "message": str(error)}) + "\n"

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
