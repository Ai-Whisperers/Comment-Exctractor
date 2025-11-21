"""Instagram Page Objects."""

from .base_page import BasePage
from .login_page import LoginPage
from .profile_page import ProfilePage
from .post_modal import PostModal
from .comments_section import CommentsSection

__all__ = [
    "BasePage",
    "LoginPage",
    "ProfilePage",
    "PostModal",
    "CommentsSection",
]
