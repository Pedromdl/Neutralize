from djoser.serializers import UserCreateSerializer, UserSerializer
from django.contrib.auth import get_user_model

User = get_user_model()

class CustomUserCreateSerializer(UserCreateSerializer):
    class Meta(UserCreateSerializer.Meta):
        model = User
        fields = (
            'id',
            'email',
            'password',
            'first_name',
            'last_name',
            'cpf',
            'address',
            'phone',
            'birth_date',
        )
        extra_kwargs = {'password': {'write_only': True}}

class CustomUserSerializer(UserSerializer):
    class Meta(UserSerializer.Meta):
        model = User
        fields = (
            'id',
            'email',
            'first_name',
            'last_name',
            'cpf',
            'address',
            'phone',
            'birth_date',
        )
