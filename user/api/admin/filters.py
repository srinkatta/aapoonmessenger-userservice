from django_filters import rest_framework as filters
from user import models as user_models


class UserFilter(filters.FilterSet):
    class Meta:
        model = user_models.User
        fields = {
            "date_joined": ["exact", "gt", "lt"],
            "country_code": ["exact"],
            "country_iso_code": ["exact"],
            "phone_number_verified": ["exact"],
            "last_login": ["exact", "gt", "lt"],
            "user_type": ["exact"],
        }
