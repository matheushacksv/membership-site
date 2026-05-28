from ninja.errors import HttpError


def staff_required(request):
    user = request.auth
    if not getattr(user, "is_staff", False):
        raise HttpError(403, "Staff only")
    return user


def superuser_required(request):
    user = request.auth
    if not getattr(user, "is_superuser", False):
        raise HttpError(403, "Superuser only")
    return user
