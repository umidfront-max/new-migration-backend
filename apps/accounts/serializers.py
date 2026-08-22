"""
Serializerlar.

Maydon nomlari frontend kutayotgan shaklda beriladi (`login`, `name`, `role`),
shuning uchun `src/stores/db.js` ni API ga o'tkazishda qayta nomlash kerak emas.
"""
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import AuditLogEntry, Role, SystemSetting, User


class RoleSerializer(serializers.ModelSerializer):
    count = serializers.IntegerField(source="capacity", required=False, default=0)
    userCount = serializers.IntegerField(source="users.count", read_only=True)

    class Meta:
        model = Role
        fields = ["id", "name", "scope", "count", "userCount", "tone"]


class UserSerializer(serializers.ModelSerializer):
    """Rol nomi bilan ishlaydi — frontend rol nomini yuboradi."""

    name = serializers.CharField(source="full_name")
    role = serializers.SlugRelatedField(
        slug_field="name", queryset=Role.objects.all(), allow_null=True, required=False,
    )
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    hasPassword = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "login", "name", "role", "unit", "phone",
            "status", "password", "hasPassword", "date_joined",
        ]
        read_only_fields = ["date_joined"]

    def get_hasPassword(self, user: User) -> bool:
        """Parol o'rnatilganmi — ro'yxatda belgi ko'rsatish uchun."""
        return user.has_usable_password()

    def validate_login(self, value: str) -> str:
        return value.strip().lower()

    def validate_password(self, value: str) -> str:
        if value:
            validate_password(value)
        return value

    def create(self, validated_data: dict) -> User:
        password = validated_data.pop("password", "") or None
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def update(self, instance: User, validated_data: dict) -> User:
        """Parol bo'sh kelsa — eskisi saqlanadi."""
        password = validated_data.pop("password", "")
        for field, value in validated_data.items():
            setattr(instance, field, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class CurrentUserSerializer(serializers.ModelSerializer):
    """Kirgan foydalanuvchi haqidagi qisqa ma'lumot."""

    name = serializers.CharField(source="full_name")
    role = serializers.CharField(source="role.name", default="", read_only=True)

    class Meta:
        model = User
        fields = ["id", "login", "name", "role", "unit", "phone", "status"]


class LoginSerializer(serializers.Serializer):
    """Kirish so'rovi."""

    login = serializers.CharField()
    password = serializers.CharField(style={"input_type": "password"}, trim_whitespace=False)


class SystemSettingSerializer(serializers.ModelSerializer):
    value = serializers.IntegerField(source="number_value", required=False, allow_null=True)
    on = serializers.BooleanField(source="is_enabled", required=False)

    class Meta:
        model = SystemSetting
        fields = ["id", "key", "label", "hint", "kind", "value", "on"]


class AuditLogEntrySerializer(serializers.ModelSerializer):
    user = serializers.CharField(source="actor_login", read_only=True)
    role = serializers.CharField(source="role_name", read_only=True)
    ip = serializers.CharField(source="ip_address", read_only=True)
    ok = serializers.BooleanField(source="is_success", read_only=True)
    at = serializers.DateTimeField(source="created_at", format="%H:%M", read_only=True)

    class Meta:
        model = AuditLogEntry
        fields = ["id", "user", "role", "action", "ip", "ok", "at", "created_at"]
