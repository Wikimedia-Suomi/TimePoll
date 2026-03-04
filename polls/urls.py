from django.urls import path

from . import views

app_name = "polls"

urlpatterns = [
    path("", views.index, name="index"),
    path("api/auth/session/", views.auth_session, name="auth_session"),
    path("api/auth/register/", views.register_identity, name="register_identity"),
    path("api/auth/login/", views.login_identity, name="login_identity"),
    path("api/auth/logout/", views.logout_identity, name="logout_identity"),
    path("api/auth/me/", views.auth_me_data, name="auth_me_data"),
    path("api/i18n/language/", views.set_language_view, name="set_language"),
    path("api/polls/", views.polls_collection, name="polls_collection"),
    path("api/polls/<uuid:poll_id>/", views.poll_detail, name="poll_detail"),
    path("api/polls/<uuid:poll_id>/close/", views.poll_close, name="poll_close"),
    path("api/polls/<uuid:poll_id>/reopen/", views.poll_reopen, name="poll_reopen"),
    path("api/polls/<uuid:poll_id>/votes/", views.poll_votes_upsert, name="poll_votes_upsert"),
    path(
        "api/polls/<uuid:poll_id>/votes/<int:option_id>/",
        views.poll_vote_delete,
        name="poll_vote_delete",
    ),
]
