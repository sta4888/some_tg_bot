from fastapi import APIRouter
from starlette import status

router = APIRouter(
    prefix="/miniapp",
    tags=["miniapp"]
)


@router.get("",
            summary="Получение списка",
            status_code=status.HTTP_200_OK)
async def get_some():
    """
    Get запрос получения списка.

    """

    return {"DATA": 123}
