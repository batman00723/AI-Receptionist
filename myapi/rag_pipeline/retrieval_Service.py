from myapi.models import DocumentChunk
from pgvector.django import CosineDistance
from myapi.rag_pipeline.rrf import reciprocal_rank_fusion
#from myapi.rag_pipeline.reranker import RerankService
from django.contrib.postgres.search import SearchQuery, SearchRank

class HybridRetrievalRerankService:
    @staticmethod
    def get_hybrid_reranked_content(query, query_vector, top_k=3):
        
        print("Hybrid Search Started")
        vector_results= DocumentChunk.objects.annotate(
            similarity= 1 - CosineDistance("embedding", query_vector)
        ).order_by("-similarity")[:10]

        keyword_result = DocumentChunk.objects.annotate(
            rank=SearchRank('search_vector', query)
        ).order_by("-rank")[:10]


        fused_score = reciprocal_rank_fusion(vector_results=vector_results, keyword_results=keyword_result)

        canditate_ids = [item[0] for item in fused_score[:3]]
        candidate_context_chunks = list(DocumentChunk.objects.filter(id__in=canditate_ids))

        # final_context_objects= RerankService.get_top_reranked_results(
        #    query= query,
        #    chunks= candidate_context_chunks,
        #    top_k= 5
        # )
        # print(f"Chunks Retrieved {final_context_objects}")

        return candidate_context_chunks
    

