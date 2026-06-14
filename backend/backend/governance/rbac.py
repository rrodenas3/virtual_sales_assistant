from fastapi import HTTPException, status

from backend.auth.mock_jwt import CurrentUser


def assert_store_access(user: CurrentUser, store_rep_id: str, store_territory_code: str) -> None:
    if user.role == "admin":
        return
    if user.role == "manager" and user.territory_code == store_territory_code:
        return
    if user.role == "rep" and user.rep_id == store_rep_id and user.territory_code == store_territory_code:
        return
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")


def assert_territory_access(user: CurrentUser, territory_code: str) -> None:
    if user.role == "admin":
        return
    if user.territory_code == territory_code:
        return
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Territory not found")

