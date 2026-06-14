from django.db import models
from pgvector.django import VectorField, HnswIndex
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex


class Document(models.Model):
    doc_name= models.CharField(max_length=100)
    document= models.FileField(upload_to= "documents/")
    uploaded_at= models.DateTimeField(auto_now_add= True)
    file_type= models.CharField(max_length=10)
    status= models.CharField(max_length=10)
    is_deleted= models.BooleanField(default= False)
    raw_content= models.TextField(null= True, blank= True)

    def __str__(self):
        return self.doc_name
    
class DeletedDocument(models.Model):
    original_doc_name = models.CharField(max_length=100)
    raw_content = models.TextField()
    deleted_at = models.DateTimeField(auto_now_add=True)

    purge_after = models.DateTimeField()

class DocumentChunk(models.Model):
    document= models.ForeignKey(Document, on_delete= models.CASCADE, related_name= "chunks")
    chunk= models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    chunk_index= models.IntegerField()
    embedding= VectorField(dimensions= 768, null= True, blank= True)
    page_number= models.IntegerField(null= True, blank= True)

    search_vector= SearchVectorField(null= True)

    class Meta:
        indexes= [
            HnswIndex(
                name= 'document_hnsw_idx',
                fields= ['embedding'],
                m= 16,
                ef_construction= 64,
                opclasses= ['vector_cosine_ops']   
            ),

            GinIndex(fields=['search_vector'])
        ]


class Patient(models.Model):
    phone = models.CharField(max_length=20, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Appointment(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="appointments")

    booking_uid = models.CharField(max_length=255)
    booking_id = models.BigIntegerField()

    service = models.CharField(max_length=255)

    date = models.DateField()
    time = models.TimeField()

    status = models.CharField(max_length=20, default="scheduled")

    created_at = models.DateTimeField(auto_now_add=True)