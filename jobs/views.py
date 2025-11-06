from rest_framework import viewsets, mixins
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from .models import Job
from .serializers.jobs_serializers import JobOutSerializer


class JobViewSet(viewsets.GenericViewSet, mixins.RetrieveModelMixin):
    queryset = Job.objects.all().order_by("-created_at")
    serializer_class = JobOutSerializer
    permission_classes = [AllowAny]  # lecture ouverte si tu veux (sinon HMAC + tenant check)
