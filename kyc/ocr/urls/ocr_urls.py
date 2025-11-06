from django.urls import path

from kyc.ocr.views.ocr import DocumentOcrView

urlpatterns = [
    path("ocr", DocumentOcrView.as_view(), name="document-ocr"),
]
