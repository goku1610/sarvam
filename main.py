import os
import asyncio
import json
from datetime import datetime
from fastapi import FastAPI
from fastapi.responses import StreamingResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from google import genai
from google.genai import types
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

# Define the data model for the incoming request
class QueryRequest(BaseModel):
    query: str
    deep_research: bool = False


class ClarifyingQuestionRequest(BaseModel):
    query: str
    plan: list[str] = []
    search_queries: list[str] = []


class ClarifyingAnswer(BaseModel):
    question: str
    answer: str


class QueryRefinementRequest(BaseModel):
    query: str
    plan: list[str] = []
    search_queries: list[str] = []
    answers: list[ClarifyingAnswer] = []


class SearchRequest(BaseModel):
    queries: list[str]


class SearchResultSummary(BaseModel):
    title: str = ""
    url: str = ""
    domain: str = ""
    content: str = ""


class FollowUpQueryRequest(BaseModel):
    query: str
    plan: list[str] = []
    searched_queries: list[str] = []
    sources: list[SearchResultSummary] = []
    iteration: int = 1


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
            "You are an expert research planner. Break down the question into a brief 2-sentence strategy "
            "and generate a list of highly effective search queries.\n"
            f"Today's date is {current_date}. Use this date when the topic depends on timeliness, recency, or current events.\n\n"
            f"{research_mode_instructions}\n\n"
            "You must use the following structural token boundaries precisely in your output format:\n"
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
            yield f"<PLAN_START>\nFallback strategy triggered due to system error: {str(e)}\n<PLAN_END>\n<QUERIES_START>\n[\"{user_query}\"]\n<QUERIES_END>"

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

@app.post("/api/plan")
async def generate_plan(request: QueryRequest):
    planner = ResearchPlanner()
    
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
    return {"search_queries": search_queries}


@app.post("/api/search")
async def execute_search(request: SearchRequest):
    scraper = WebSearchScraper()
    queries = [query.strip() for query in request.queries if query.strip()]

    async def event_generator():
        if not queries:
            yield json.dumps({"type": "error", "message": "No search queries selected."}) + "\n"
            return

        try:
            async for page in scraper.stream_concurrent_research(queries):
                yield json.dumps({
                    "type": "result",
                    "title": page["title"],
                    "url": page["url"],
                    "domain": page["domain"],
                    "content": page["content"],
                    "query": page.get("query", ""),
                    "rank": page.get("rank"),
                }) + "\n"
                await asyncio.sleep(0)
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
