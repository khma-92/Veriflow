from rest_framework import serializers

class ValidateInputSerializer(serializers.Serializer):
    detected = serializers.DictField()  # {"type":"passport","country":"CIV"}
    fields = serializers.DictField()    # {"mrz":"P<CIV...", "dob":"1999-08-16", "expiry_date":"2029-08-15"}
