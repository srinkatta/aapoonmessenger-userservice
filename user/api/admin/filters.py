from django_filters import rest_framework as filters
from user import models as user_models


class UserFilter(filters.FilterSet):
    """
    Filter class for querying User model based on specified fields.

    Available filters:
    - date_joined: Date of user registration (exact, greater than, less than).
    - country_code: User's country code.
    - country_iso_code: Country's ISO code.
    - phone_number_verified: Phone number verification status.
    - last_login: Last login timestamp (exact, greater than, less than).
    - user_type: Type of user.
    """

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
