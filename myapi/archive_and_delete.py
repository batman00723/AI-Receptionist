from django.utils import timezone
from datetime import timedelta
from myapi.models import Document, DeletedDocument


def archive_and_delete_document(document):
    DeletedDocument.objects.create(
        original_doc_name=document.doc_name,
        raw_content=document.raw_content,
        purge_after=timezone.now() + timedelta(days=30)
    )

    document.delete()