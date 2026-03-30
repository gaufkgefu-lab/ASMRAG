"""FastAPI application exposing API and public website."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.repository import get_card, list_distinct_values, search_cards


APP_ROOT = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(APP_ROOT / "templates"))

app = FastAPI(
    title="ASMRAG Public Knowledge Base",
    description="Public engineering knowledge base for activated sludge RAG workflows.",
    version="0.1.0",
)
app.mount("/static", StaticFiles(directory=str(APP_ROOT / "static")), name="static")


@app.get("/api/health")
def api_health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/cards")
def api_list_cards(
    q: str = "",
    category: str = "",
    tag: list[str] = Query(default=[]),
    microorganism: str = "",
    condition: str = "",
    source_type: str = "",
    status: str = "active",
    limit: int = 50,
    offset: int = 0,
):
    items = search_cards(
        q=q,
        category=category,
        tags=tag,
        microorganism=microorganism,
        condition=condition,
        source_type=source_type,
        status=status,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "count": len(items)}


@app.get("/api/cards/{knowledge_id}")
def api_get_card(knowledge_id: str):
    card = get_card(knowledge_id)
    if card is None:
        raise HTTPException(status_code=404, detail="Card not found")
    return card


@app.get("/api/facets")
def api_facets():
    return {
        "categories": list_distinct_values("categories"),
        "tags": list_distinct_values("tags"),
        "microorganisms": list_distinct_values("microorganisms"),
        "conditions": list_distinct_values("conditions"),
        "source_types": list_distinct_values("source_types"),
    }


@app.get("/", response_class=HTMLResponse)
def web_index(
    request: Request,
    q: str = "",
    category: str = "",
    tag: list[str] = Query(default=[]),
    microorganism: str = "",
    condition: str = "",
    source_type: str = "",
    status: str = "active",
):
    cards = search_cards(
        q=q,
        category=category,
        tags=tag,
        microorganism=microorganism,
        condition=condition,
        source_type=source_type,
        status=status,
    )
    facets = {
        "categories": list_distinct_values("categories"),
        "tags": list_distinct_values("tags"),
        "microorganisms": list_distinct_values("microorganisms"),
        "conditions": list_distinct_values("conditions"),
        "source_types": list_distinct_values("source_types"),
    }
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "cards": cards,
            "facets": facets,
            "filters": {
                "q": q,
                "category": category,
                "tag": tag,
                "microorganism": microorganism,
                "condition": condition,
                "source_type": source_type,
                "status": status,
            },
        },
    )


@app.get("/cards/{knowledge_id}", response_class=HTMLResponse)
def web_card_detail(request: Request, knowledge_id: str):
    card = get_card(knowledge_id)
    if card is None:
        raise HTTPException(status_code=404, detail="Card not found")
    return templates.TemplateResponse("card_detail.html", {"request": request, "card": card})
