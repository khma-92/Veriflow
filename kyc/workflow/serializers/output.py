from rest_framework import serializers

class WorkflowOutputSerializer(serializers.Serializer):
    job_id = serializers.CharField()
    status = serializers.ChoiceField(choices=["queued","running","succeeded","failed"])
