from myapi.models import SemanticCache
from pgvector.django import CosineDistance



def save_to_db(query, query_embedding, response ):
    SemanticCache.objects.create(
    query=query,
    response=response,
    embedding=query_embedding
)

def semantic_cache_search(query_embedding):

    # Annotate creates an temp column of distance here 
    cached = (SemanticCache.objects.annotate(distance=CosineDistance("embedding",query_embedding)).order_by("distance").first())

    return cached

# cached here gives response of Semantic cache table columns + distance(creates are temp instance)