"""Shared initial-password policy for login and self-service password changes."""

from sqlbot_xpack.config.arg_manage import get_group_args


async def initial_pwd_disabled(session) -> bool:
    login_args = await get_group_args(session=session, flag="login")
    disabled_arg = next(
        (a for a in login_args if a.pkey == "login.initial_pwd_disabled"), None
    )
    return bool(disabled_arg and str(disabled_arg.pval).strip().lower() == "true")
