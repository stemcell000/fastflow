# authentication/views.py

from django.contrib.auth import authenticate, login
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions, viewsets, filters
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .serializers import (LDAPTokenObtainPairSerializer, CustomUserSerializer, CustomUserCategorySerializer, LDAPGroupSerializer, CustomUserTechnicalSerializer,)
from rest_framework.permissions import IsAdminUser
from django.core.management import call_command
from rest_framework.decorators import action
from authentication.models import CustomUser, LDAPGroup, CustomUserCategory
from django_filters.rest_framework import DjangoFilterBackend
from .permissions import IsNetworkManager


class IsStaffOrSuperUser(BasePermission):
    """
    Custom permission to only allow admin users (staff or superuser).
    """
    def has_permission(self, request, view):
        return request.user and (request.user.is_staff or request.user.is_superuser)


# ========================================
# VIEWSETS POUR USERS ET LDAP
# ========================================

class CustomUserViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour gérer les utilisateurs
    """
    queryset = CustomUser.objects.all().order_by('last_name')
    serializer_class = CustomUserSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'is_staff', 'category', 'is_human']
    search_fields = ['username', 'first_name', 'last_name', 'email']
    ordering_fields = ['username', 'first_name', 'last_name', 'date_joined']
    ordering = ['last_name', 'first_name']
    http_method_names = ['get', 'post', 'put', 'patch', 'delete']

    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsStaffOrSuperUser()]
        return [IsAuthenticated()]
    
    def get_queryset(self):
        """
        Par défaut, filtrer pour ne montrer que les utilisateurs humains
        """
        queryset = super().get_queryset()
        
        # Filtrer par is_human par défaut (sauf si explicitement demandé)
        show_all = self.request.query_params.get('show_all', 'false').lower() == 'true'
        if not show_all:
            queryset = queryset.filter(is_human=True)
        
        return queryset
    
    def get_serializer_class(self):
        """
        Utiliser le serializer technique pour l'action technical_list
        """
        if self.action == 'technical_list':
            return CustomUserTechnicalSerializer
        return super().get_serializer_class()
    
    @action(
        detail=False, 
        methods=['get'], 
        url_path='technical',
        permission_classes=[IsNetworkManager]  # ← Utiliser la permission
    )
    def technical_list(self, request):
        """
        Liste technique des utilisateurs pour Network & Identity Managers
        Requiert: is_staff ou groupe 'Network & Identity Manager'
        """
        # Vérifier les permissions
        if not (request.user.is_staff or 
                request.user.groups.filter(name='Network & Identity Manager').exists()):
            return Response(
                {'detail': 'Permission denied. Network & Identity Manager role required.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Récupérer les paramètres de filtrage
        show_all = request.query_params.get('show_all', 'false').lower() == 'true'
        
        queryset = self.get_queryset()
        if not show_all:
            queryset = queryset.filter(is_human=True)
        
        serializer = CustomUserTechnicalSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Récupérer le profil de l'utilisateur connecté"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, url_path='all-users')
    def active_users(self, request):
        """Liste tous les utilisateurs actifs"""
        users = CustomUser.objects.order_by('last_name').distinct()\
            .exclude(is_superuser=True)\
            .exclude(first_name='')\
            .exclude(last_name='')
        serializer = self.get_serializer(users, many=True)
        return Response(serializer.data)

class LDAPGroupViewSet(viewsets.ModelViewSet):
    """
    ViewSet pour gérer les groupes LDAP
    """
    queryset = LDAPGroup.objects.all()
    serializer_class = LDAPGroupSerializer  
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'distinguished_name', 'description']
    ordering = ['name']
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsStaffOrSuperUser()]
        return [IsAuthenticated()]
    
    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        """Récupérer les membres d'un groupe LDAP"""
        group = self.get_object()
        members = group.members.all()
        serializer = CustomUserSerializer(members, many=True)
        return Response(serializer.data)


# ========================================
# VUES D'AUTHENTIFICATION (EXISTANTES)
# ========================================

class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return Response({"detail": "Login successful"}, status=status.HTTP_200_OK)
        else:
            return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)


class LDAPTokenObtainPairView(TokenObtainPairView):
    serializer_class = LDAPTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        remember_me = request.data.get('rememberMe', False)
        response = super().post(request, *args, **kwargs)
        data = response.data

        access_token = data.get("access")
        refresh_token = data.get("refresh")

        max_age_access = 300
        max_age_refresh = 7 * 24 * 60 * 60

        if remember_me:
            max_age_access = 3600 * 24 * 7
            max_age_refresh = 3600 * 24 * 30

        if access_token:
            response.set_cookie(
                key="access_token",
                value=access_token,
                httponly=True,
                secure=False,
                samesite="Lax",
                max_age=max_age_access,
            )

        if refresh_token:
            response.set_cookie(
                key="refresh_token",
                value=refresh_token,
                httponly=True,
                secure=False,
                samesite="Lax",
                max_age=max_age_refresh,
            )

        response.data["access_debug"] = access_token
        response.data["refresh_debug"] = refresh_token

        return response


class CookieTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        refresh_token = request.COOKIES.get("refresh_token")
        print("TOKEN IN:", refresh_token)

        if not refresh_token:
            return Response({"detail": "No refresh token provided"}, status=status.HTTP_401_UNAUTHORIZED)

        data = {"refresh": refresh_token}
        serializer = self.get_serializer(data=data)
        
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            print("Refresh token rejected:", e)
            return Response({"detail": "Invalid or expired refresh token"}, status=status.HTTP_401_UNAUTHORIZED)

        new_access = serializer.validated_data.get("access")
        response = Response(serializer.validated_data, status=status.HTTP_200_OK)

        if new_access:
            response.set_cookie(
                key="access_token",
                value=new_access,
                httponly=True,
                secure=False,
                samesite="Lax",
                max_age=7 * 24 * 60 * 60,
            )

        return response


class LogoutView(APIView):
    def post(self, request):
        response = Response({"detail": "Logged out successfully."}, status=status.HTTP_200_OK)
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")
        return response


class MeView(APIView):
    """
    Retourne les informations de l'utilisateur connecté
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = CustomUserSerializer(request.user, context={'request': request})
        return Response(serializer.data)


class SyncLDAPUsersView(APIView):
    """
    Vue pour déclencher MANUELLEMENT la synchronisation LDAP
    """
    permission_classes = [IsAdminUser]

    def post(self, request):
        try:
            call_command('sync_ldap_users')
            return Response({'success': True, 'message': 'LDAP sync done.'})
        except Exception as e:
            return Response({'success': False, 'error': str(e)}, status=500)