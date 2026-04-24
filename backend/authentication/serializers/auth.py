from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import authenticate
from rest_framework import serializers


class LDAPTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Serializer pour l'authentification LDAP avec JWT"""
    
    def validate(self, attrs):
        request = self.context.get('request')
        username = attrs.get('username')
        password = attrs.get('password')

        print("Authenticating:", username)
        user = authenticate(request=request, username=username, password=password)
        if not user:
            print("LDAP authentication failed")
            raise serializers.ValidationError("Invalid credentials")

        self.user = user
        print("LDAP authentication successful")
        return super().validate(attrs)
    

