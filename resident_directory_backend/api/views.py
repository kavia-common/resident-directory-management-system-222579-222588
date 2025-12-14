from django.contrib.auth.models import User
from django.db.models import Q
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import api_view, action, permission_classes
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Resident, Photo
from .serializers import ResidentSerializer, PhotoSerializer


# PUBLIC_INTERFACE
@api_view(['GET'])
def health(request):
    """Simple health check endpoint.
    Returns: 200 OK with a message indicating the server is running.
    """
    return Response({"message": "Server is up!"})


class StandardResultsSetPagination(PageNumberPagination):
    """Default pagination for list endpoints."""
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class ResidentPermissions(permissions.BasePermission):
    """Custom permissions for resident operations."""
    def has_permission(self, request, view):
        if view.action == 'destroy':
            return request.user and request.user.is_staff
        if view.action in ['list', 'retrieve']:
            # Require authentication for list/retrieve per requirements
            return request.user and request.user.is_authenticated
        # create/update/partial_update require authentication
        if view.action in ['create', 'update', 'partial_update']:
            return request.user and request.user.is_authenticated
        return request.user and request.user.is_authenticated


# PUBLIC_INTERFACE
class ResidentViewSet(viewsets.ModelViewSet):
    """Resident CRUD with search and filters.

    Query params:
    - q: case-insensitive contains across first_name, last_name, apartment, phone, email
    - apartment: exact match filter
    - is_active: true/false filter
    """
    serializer_class = ResidentSerializer
    queryset = Resident.objects.all().prefetch_related('photos')
    pagination_class = StandardResultsSetPagination
    permission_classes = [ResidentPermissions]

    def get_queryset(self):
        qs = super().get_queryset()
        request = self.request
        q = request.query_params.get('q')
        apartment = request.query_params.get('apartment')
        is_active = request.query_params.get('is_active')
        if q:
            qs = qs.filter(
                Q(first_name__icontains=q) |
                Q(last_name__icontains=q) |
                Q(apartment__icontains=q) |
                Q(phone__icontains=q) |
                Q(email__icontains=q)
            )
        if apartment:
            qs = qs.filter(apartment=apartment)
        if is_active is not None:
            val = is_active.lower() in ('1', 'true', 'yes')
            qs = qs.filter(is_active=val)
        return qs.order_by('last_name', 'first_name')

    # Nested route: /api/residents/{id}/photos/
    @action(detail=True, methods=['get', 'post'], url_path='photos', permission_classes=[permissions.IsAuthenticated])
    def photos(self, request, pk=None):
        resident = self.get_object()
        if request.method.lower() == 'get':
            serializer = PhotoSerializer(resident.photos.all(), many=True, context={'request': request})
            return Response(serializer.data)
        # POST - upload
        data = request.data.copy()
        data['resident'] = resident.id
        serializer = PhotoSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            photo = serializer.save()
            if photo.is_primary:
                Photo.objects.filter(resident=resident, is_primary=True).exclude(pk=photo.pk).update(is_primary=False)
            return Response(PhotoSerializer(photo, context={'request': request}).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# PUBLIC_INTERFACE
class PhotoViewSet(viewsets.GenericViewSet):
    """Retrieve and delete photo, with action to set primary."""
    queryset = Photo.objects.select_related('resident').all()
    serializer_class = PhotoSerializer
    permission_classes = [permissions.IsAuthenticated]

    def retrieve(self, request, pk=None):
        """Get a single photo by id."""
        photo = self.get_object()
        return Response(self.get_serializer(photo, context={'request': request}).data)

    def destroy(self, request, pk=None):
        """Delete a photo by id."""
        photo = self.get_object()
        photo.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # PUBLIC_INTERFACE
    @action(detail=True, methods=['post'], url_path='set_primary', permission_classes=[permissions.IsAuthenticated])
    def set_primary(self, request, pk=None):
        """Set the specified photo as primary for its resident and demote others."""
        photo = self.get_object()
        Photo.objects.filter(resident=photo.resident, is_primary=True).exclude(pk=photo.pk).update(is_primary=False)
        if not photo.is_primary:
            photo.is_primary = True
            photo.save(update_fields=['is_primary'])
        return Response(self.get_serializer(photo, context={'request': request}).data)


# PUBLIC_INTERFACE
@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def register(request):
    """Register a new user.

    Body:
    - username (required)
    - password (required)
    - email (optional)

    Returns:
    - 201 Created with success message, or 400 with validation errors.
    """
    username = request.data.get('username')
    password = request.data.get('password')
    email = request.data.get('email', '')
    if not username or not password:
        return Response({'detail': 'username and password are required'}, status=status.HTTP_400_BAD_REQUEST)
    if User.objects.filter(username=username).exists():
        return Response({'detail': 'Username already exists'}, status=status.HTTP_400_BAD_REQUEST)
    user = User.objects.create_user(username=username, email=email, password=password)
    return Response({'success': True, 'username': user.username}, status=status.HTTP_201_CREATED)


# PUBLIC_INTERFACE
class AdminSummaryView(APIView):
    """Staff-only summary with counts of residents and photos."""
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        total_residents = Resident.objects.count()
        active_residents = Resident.objects.filter(is_active=True).count()
        inactive_residents = Resident.objects.filter(is_active=False).count()
        total_photos = Photo.objects.count()
        return Response({
            'residents': {
                'total': total_residents,
                'active': active_residents,
                'inactive': inactive_residents,
            },
            'photos': {
                'total': total_photos
            }
        })
