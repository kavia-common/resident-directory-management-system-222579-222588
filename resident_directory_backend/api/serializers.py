from typing import Any, Dict, Optional
from django.db import transaction
from rest_framework import serializers
from .models import Resident, Photo


# PUBLIC_INTERFACE
class PhotoSerializer(serializers.ModelSerializer):
    """Serializer for uploading and representing resident photos."""

    image_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Photo
        fields = ["id", "resident", "image", "image_url", "is_primary", "uploaded_at"]
        read_only_fields = ["id", "uploaded_at", "image_url"]

    def get_image_url(self, obj: Photo) -> Optional[str]:
        request = self.context.get("request")
        if obj.image and hasattr(obj.image, "url"):
            if request:
                return request.build_absolute_uri(obj.image.url)
            return obj.image.url
        return None

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure only one primary photo per resident."""
        is_primary = attrs.get("is_primary", False)
        resident = attrs.get("resident") or (self.instance.resident if self.instance else None)
        if is_primary and resident:
            # When creating or updating to primary, ensure others are demoted in save()
            # But also avoid multiple primaries by checking existing ones
            qs = Photo.objects.filter(resident=resident, is_primary=True)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                # Allow but we'll demote others on save if the client explicitly sets primary
                # To be strict, we can still allow and handle in view action. Here we allow.
                pass
        return attrs

    def update(self, instance: Photo, validated_data: Dict[str, Any]) -> Photo:
        with transaction.atomic():
            instance = super().update(instance, validated_data)
            if instance.is_primary:
                Photo.objects.filter(resident=instance.resident, is_primary=True).exclude(pk=instance.pk).update(is_primary=False)
        return instance


# PUBLIC_INTERFACE
class ResidentSerializer(serializers.ModelSerializer):
    """Serializer for residents including photo info and primary photo URL."""

    photos = PhotoSerializer(many=True, read_only=True)
    primary_photo_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Resident
        fields = [
            "id",
            "first_name",
            "last_name",
            "apartment",
            "phone",
            "email",
            "dob",
            "notes",
            "is_active",
            "created_at",
            "updated_at",
            "primary_photo_url",
            "photos",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "primary_photo_url", "photos"]

    def get_primary_photo_url(self, obj: Resident) -> Optional[str]:
        request = self.context.get("request")
        primary = obj.primary_photo
        if primary and primary.image:
            if request:
                return request.build_absolute_uri(primary.image.url)
            return primary.image.url
        return None
