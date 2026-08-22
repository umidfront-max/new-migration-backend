"""Foydalanuvchilar, rollar, audit jurnali va tizim sozlamalari."""
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models

from core.models import OrderedModel, TimeStampedModel


class Role(TimeStampedModel):
    """Kirish huquqlari darajasi."""

    TONE_CHOICES = [
        ("turk", "Firuza"),
        ("lapis", "Ko‘k"),
        ("saffron", "Sariq"),
        ("coral", "Marjon"),
        ("violet", "Binafsha"),
        ("mist", "Kulrang"),
    ]

    name = models.CharField("nomi", max_length=120, unique=True)
    scope = models.CharField("ko‘lami", max_length=180, blank=True)
    capacity = models.PositiveIntegerField("foydalanuvchilar soni", default=0)
    tone = models.CharField("rangi", max_length=16, choices=TONE_CHOICES, default="lapis")

    class Meta:
        verbose_name = "rol"
        verbose_name_plural = "rollar"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class UserManager(BaseUserManager):
    """`login` maydonini identifikator sifatida ishlatadi."""

    use_in_migrations = True

    def create_user(self, login: str, password: str | None = None, **extra_fields):
        if not login:
            raise ValueError("Login bo‘sh bo‘lishi mumkin emas")
        user = self.model(login=self.normalize_login(login), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, login: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("status", User.Status.ACTIVE)
        if not extra_fields.get("is_staff") or not extra_fields.get("is_superuser"):
            raise ValueError("Superuser uchun is_staff va is_superuser True bo‘lishi kerak")
        return self.create_user(login, password, **extra_fields)

    @staticmethod
    def normalize_login(login: str) -> str:
        return login.strip().lower()


class User(AbstractBaseUser, PermissionsMixin):
    """
    Tizim foydalanuvchisi.

    Parol Django'ning standart PBKDF2 hashi bilan saqlanadi — frontenddagi
    vaqtinchalik SHA-256 yechimi shu bilan almashtiriladi.
    """

    class Status(models.TextChoices):
        ACTIVE = "Faol", "Faol"
        BLOCKED = "Bloklangan", "Bloklangan"

    login = models.CharField("login", max_length=64, unique=True, db_index=True)
    full_name = models.CharField("F.I.Sh", max_length=180)
    role = models.ForeignKey(
        Role, verbose_name="roli", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="users",
    )
    unit = models.CharField("tashkilot / bo‘lim", max_length=180, blank=True)
    phone = models.CharField("telefon", max_length=32, blank=True)
    status = models.CharField(
        "holati", max_length=16, choices=Status.choices, default=Status.ACTIVE,
    )
    is_staff = models.BooleanField("xodim", default=False)
    is_active = models.BooleanField("faol", default=True)
    date_joined = models.DateTimeField("qo‘shilgan", auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "login"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        verbose_name = "foydalanuvchi"
        verbose_name_plural = "foydalanuvchilar"
        ordering = ["full_name"]

    def __str__(self) -> str:
        return f"{self.full_name} ({self.login})"

    @property
    def is_blocked(self) -> bool:
        """Bloklangan hisob tizimga kira olmaydi."""
        return self.status == self.Status.BLOCKED

    def can_sign_in(self) -> bool:
        return self.is_active and not self.is_blocked


class SystemSetting(TimeStampedModel):
    """Administrator panelidagi sozlamalar."""

    class Kind(models.TextChoices):
        SWITCH = "switch", "Yoqish/o‘chirish"
        NUMBER = "number", "Raqamli qiymat"

    key = models.SlugField("kalit", max_length=64, unique=True)
    label = models.CharField("nomi", max_length=180)
    hint = models.CharField("izoh", max_length=250, blank=True)
    kind = models.CharField("turi", max_length=16, choices=Kind.choices, default=Kind.SWITCH)
    number_value = models.IntegerField("qiymati", null=True, blank=True)
    is_enabled = models.BooleanField("yoqilgan", default=False)

    class Meta:
        verbose_name = "sozlama"
        verbose_name_plural = "sozlamalar"
        ordering = ["id"]

    def __str__(self) -> str:
        return self.label


class AuditLogEntry(models.Model):
    """
    O'zgarmas jurnal: kim, qachon, nima qildi.

    Yozuvlar faqat qo'shiladi — API orqali tahrirlash yoki o'chirish yo'q.
    """

    user = models.ForeignKey(
        User, verbose_name="foydalanuvchi", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="audit_entries",
    )
    actor_login = models.CharField("login", max_length=64)
    role_name = models.CharField("roli", max_length=120, blank=True)
    action = models.CharField("amal", max_length=250)
    ip_address = models.GenericIPAddressField("IP manzil", null=True, blank=True)
    is_success = models.BooleanField("bajarildi", default=True)
    created_at = models.DateTimeField("vaqti", auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = "audit yozuvi"
        verbose_name_plural = "audit jurnali"
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"{self.actor_login}: {self.action}"
