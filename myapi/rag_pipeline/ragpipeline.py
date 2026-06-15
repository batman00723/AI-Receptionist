from myapi.rag_pipeline.embedding import EmbeddingService
from langchain_text_splitters import RecursiveCharacterTextSplitter
from myapi.models import DocumentChunk

class RagPipeline:
    def __init__(self):
        self.splitter= RecursiveCharacterTextSplitter(
            chunk_size= 300,
            chunk_overlap= 100,
            separators= ["\n\n", "\n", " ", ""]
        )

    def process_document(self, document, text):
        chunks= self.splitter.split_text(text)
        
        prepared_chunks= []

        for index, chunk_text in enumerate(chunks):
            vector= EmbeddingService.get_embedding(chunk_text)

            prepared_chunks.append(DocumentChunk(
                document= document,
                chunk= chunk_text,
                embedding= vector,
                chunk_index= index
            ))

        if prepared_chunks:
            DocumentChunk.objects.bulk_create(prepared_chunks)

        return len(prepared_chunks)