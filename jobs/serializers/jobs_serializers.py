from rest_framework import serializers

from jobs.models import Job


class JobOutSerializer(serializers.ModelSerializer):
    class Meta:
        model = Job
        fields = ("id","status","result_json","error_json","steps","created_at","started_at","finished_at")
        read_only_fields = fields
