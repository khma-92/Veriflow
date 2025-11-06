from django.urls import path

from kyc.face_match.views.match import FaceMatchView

urlpatterns = [ path("match", FaceMatchView.as_view(), name="face-match") ]
