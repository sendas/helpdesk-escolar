from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_secret_key: str = "dev-secret-change-me"
    app_debug: bool = False
    frontend_url: str = "http://localhost:85"
    # Comma-separated list of extra allowed CORS origins (e.g. during migration)
    extra_allowed_origins: str = ""

    @property
    def allowed_origins(self) -> list[str]:
        origins = [self.frontend_url]
        if self.extra_allowed_origins:
            origins += [o.strip() for o in self.extra_allowed_origins.split(",") if o.strip()]
        return origins

    database_url: str = "sqlite+aiosqlite:///./data/tickets.db"

    # LDAP
    ldap_enabled: bool = True
    ldap_server: str = ""
    ldap_port: int = 636
    ldap_use_ssl: bool = True
    ldap_bind_dn: str = ""
    ldap_bind_password: str = ""
    ldap_base_dn: str = ""
    ldap_user_filter: str = "(sAMAccountName={username})"
    ldap_attr_email: str = "mail"
    ldap_attr_display_name: str = "displayName"
    ldap_admin_group: str = ""

    # Azure AD
    azure_ad_enabled: bool = True
    azure_tenant_id: str = ""
    azure_client_id: str = ""
    azure_client_secret: str = ""
    azure_redirect_uri: str = "http://localhost:8089/api/v1/auth/azure-callback"
    azure_admin_group_id: str = ""
    # Comma-separated list of Microsoft account emails that should be admins.
    azure_admin_emails: str = ""
    # Comma-separated AD/Entra OU paths allowed to use the app.
    # Example: queiroz.local/AEEQ/_Docentes,queiroz.local/AEEQ/_Suporte
    azure_allowed_onprem_ous: str = ""
    azure_admin_onprem_ous: str = ""
    azure_technician_onprem_ous: str = ""
    azure_secretary_onprem_ous: str = ""
    azure_non_teaching_onprem_ous: str = ""
    # By default, refresh Entra users once per night.
    # Use a lower value (e.g. 60) to sync periodically, or 0 to disable.
    azure_sync_interval_minutes: int = 1440

    # JWT
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480

    # Mail
    mail_username: str = ""
    mail_password: str = ""
    mail_from: str = "tickets@escola.local"
    mail_server: str = ""
    mail_port: int = 587
    mail_starttls: bool = True
    mail_ssl_tls: bool = False
    mail_suppress_send: bool = False

    # Web Push / browser notifications
    # Must be a valid contact URI. Example: mailto:helpdesk@techpro.pt
    push_vapid_subject: str = "mailto:helpdesk@techpro.pt"

    # Incoming mail replies
    mail_reply_enabled: bool = False
    imap_server: str = ""
    imap_port: int = 993
    imap_ssl: bool = True
    imap_username: str = ""
    imap_password: str = ""
    imap_folder: str = "INBOX"
    imap_poll_seconds: int = 120

    # Backups
    backup_auto_enabled: bool = False
    backup_interval_hours: int = 24
    backup_directory: str = "/app/data/backups"
    backup_retention: int = 14


settings = Settings()
