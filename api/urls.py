from django.conf import settings
from django.urls import re_path

# Project
from api.views import *

app_name = "api"

urlpatterns = [
    re_path(r"^version/?$", AppVersionView, name="app_versions"),
    re_path(r"^ping/?$", PingView, name="ping"),
    # handbooks
    re_path(r"^handbooks/?$", HandbooksListView, name="handbooks_list"),
    re_path(r"^handbooks/(?P<handbook_name>\w+)/?$", HandbookView, name="handbooks_item_list"),
    # auth
    re_path(r"^auth/auth/?$", AuthRegisterView, name="auth"),
    # users
    re_path(r"^users/(?P<user_id>[\w-]+)/?$", UserView, name="user"),
    # services
    re_path(r"^services/store-rates/?$", StoreExchangeRatesView, name="store_exchanges_rates"),
]
