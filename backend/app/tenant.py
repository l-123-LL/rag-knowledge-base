from fastapi import Header


def get_tenant_id(
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
) -> str:
    return x_tenant_id or "default"
