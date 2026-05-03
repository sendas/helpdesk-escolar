import ssl
import logging
from ldap3 import Server, Connection, ALL, Tls, SUBTREE
from ldap3.core.exceptions import LDAPException
from app.config import settings

logger = logging.getLogger(__name__)


def authenticate_ldap(username: str, password: str) -> dict | None:
    if not settings.ldap_enabled or not settings.ldap_server:
        logger.warning("LDAP login rejected: LDAP is disabled or LDAP_SERVER is empty")
        return None

    tls = Tls(validate=ssl.CERT_NONE) if settings.ldap_use_ssl else None
    server = Server(
        settings.ldap_server,
        port=settings.ldap_port,
        use_ssl=settings.ldap_use_ssl,
        tls=tls,
        get_info=ALL,
    )

    # Step 1: service account bind to search for user DN
    try:
        conn = Connection(
            server,
            user=settings.ldap_bind_dn,
            password=settings.ldap_bind_password,
            auto_bind=True,
        )
    except LDAPException as exc:
        logger.warning("LDAP service bind failed for %s: %s", settings.ldap_bind_dn, exc)
        return None

    search_filter = settings.ldap_user_filter.format(username=username)
    conn.search(
        settings.ldap_base_dn,
        search_filter,
        search_scope=SUBTREE,
        attributes=[
            settings.ldap_attr_email,
            settings.ldap_attr_display_name,
            "memberOf",
            "distinguishedName",
        ],
    )

    if not conn.entries:
        conn.unbind()
        logger.warning("LDAP user search returned no entries for username=%s base=%s filter=%s", username, settings.ldap_base_dn, search_filter)
        return None

    entry = conn.entries[0]
    user_dn = str(entry.distinguishedName)
    conn.unbind()

    # Step 2: verify user credentials by binding with their DN
    try:
        user_conn = Connection(server, user=user_dn, password=password, auto_bind=True)
        user_conn.unbind()
    except LDAPException as exc:
        logger.warning("LDAP user bind failed for username=%s dn=%s: %s", username, user_dn, exc)
        return None

    groups = []
    try:
        groups = [str(g) for g in entry.memberOf]
    except Exception:
        pass

    is_admin = bool(
        settings.ldap_admin_group
        and any(settings.ldap_admin_group.lower() in g.lower() for g in groups)
    )

    email = ""
    try:
        email = str(getattr(entry, settings.ldap_attr_email))
    except Exception:
        email = f"{username}@escola.local"

    display_name = username
    try:
        display_name = str(getattr(entry, settings.ldap_attr_display_name))
    except Exception:
        pass

    return {
        "username": username,
        "email": email,
        "display_name": display_name,
        "is_admin": is_admin,
        "auth_provider": "ldap",
    }
