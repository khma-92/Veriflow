from rest_framework import serializers

class WorkflowInputSerializer(serializers.Serializer):
    steps = serializers.ListField(child=serializers.ChoiceField(choices=["liveness","ocr","validate","face_match","score"]), allow_empty=False)
    inputs = serializers.DictField()   # voir structure annoncée dans ton cahier
    rules = serializers.DictField(required=False)  # {"min_score_accept":80,"min_similarity":0.75,"require_back_image":false}
    webhook_url = serializers.URLField(required=False, allow_blank=True)
