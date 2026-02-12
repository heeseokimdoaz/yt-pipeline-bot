from fastapi import APIRouter

from app.models.schemas import SearchRequest, SearchResult
from app.services.vector_store import search_similar

router = APIRouter()


@router.post("/similar", response_model=list[SearchResult])
async def vector_search(request: SearchRequest):
    results = search_similar(
        query=request.query,
        collection_name=request.collection,
        n_results=request.n_results,
    )
    return results
