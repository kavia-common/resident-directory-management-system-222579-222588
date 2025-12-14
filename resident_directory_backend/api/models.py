from django.db import models


class TimeStampedModel(models.Model):
    """Abstract base model with created and updated timestamps."""
    created_at = models.DateTimeField(auto_now_add=True, help_text="Creation timestamp")
    updated_at = models.DateTimeField(auto_now=True, help_text="Last update timestamp")

    class Meta:
        abstract = True


class Resident(TimeStampedModel):
    """Resident model storing personal and contact information."""
    first_name = models.CharField(max_length=120)
    last_name = models.CharField(max_length=120)
    apartment = models.CharField(max_length=50)
    phone = models.CharField(max_length=50)
    email = models.EmailField(max_length=254, unique=False)
    dob = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["last_name", "first_name"]
        indexes = [
            models.Index(fields=["last_name", "first_name"]),
            models.Index(fields=["apartment"]),
            models.Index(fields=["email"]),
        ]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name} (Apt {self.apartment})"

    @property
    def primary_photo(self):
        """Return the primary photo instance if available."""
        return self.photos.filter(is_primary=True).first()


def resident_photo_upload_path(instance: "Photo", filename: str) -> str:
    """Dynamic upload path for resident photos: residents/YYYY/MM/<filename>"""
    return f"residents/{instance.uploaded_at.year}/{instance.uploaded_at.month:02d}/{filename}"


class Photo(models.Model):
    """Photo for a resident with primary flag."""
    resident = models.ForeignKey(Resident, related_name="photos", on_delete=models.CASCADE)
    image = models.ImageField(upload_to="residents/%Y/%m/")
    is_primary = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def save(self, *args, **kwargs):
        """Ensure only one primary photo per resident upon save."""
        super().save(*args, **kwargs)
        if self.is_primary:
            # Demote other photos for the same resident
            Photo.objects.filter(resident=self.resident, is_primary=True).exclude(pk=self.pk).update(is_primary=False)

    def __str__(self) -> str:
        return f"Photo for {self.resident} ({'primary' if self.is_primary else 'secondary'})"
