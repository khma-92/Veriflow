from django.db import models

class Job(models.Model):
    STATUS_Q = "queued"
    STATUS_R = "running"
    STATUS_S = "succeeded"
    STATUS_F = "failed"

    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE, related_name="jobs")
    status = models.CharField(max_length=16, default=STATUS_Q)
    steps = models.JSONField(default=list, blank=True)       # ["liveness","ocr","validate","face_match","score"]
    inputs = models.JSONField(default=dict, blank=True)
    result_json = models.JSONField(null=True, blank=True)
    error_json = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "jobs"

    def __str__(self):
        return f"Job#{self.id}({self.status})"
