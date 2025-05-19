# User registration view
from rest_framework.response import Response
from rest_framework.decorators import api_view
from .models import User
from .serializers import UserSerializer

@api_view(['POST'])
def register_user(request):
    """
    View to register a new user.
    
    This endpoint allows anyone to register as a new user.
    
    Returns:
        Response with status and message
    """
    data = request.data
    serializer = UserSerializer(data=data)
    
    if serializer.is_valid():
        serializer.save()
        return Response({
            "message": "User created successfully",
            "user": {"username": serializer.data.get("username")}
        }, status=201)
    
    return Response({"message": "Validation failed", "errors": serializer.errors}, status=400)
