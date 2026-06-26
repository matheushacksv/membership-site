from datetime import timedelta

from django.utils import timezone


def expiry_from_days(access_days, start=None):
    """expires_at a partir de access_days. None (vitalício) se access_days vazio.

    `start` define a base da contagem (default = agora). Em matrícula nova é now;
    na correção retroativa em massa usa-se o enrolled_at de cada matrícula.
    """
    if not access_days:
        return None
    return (start or timezone.now()) + timedelta(days=access_days)
