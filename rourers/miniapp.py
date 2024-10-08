from fastapi import APIRouter, Request
from starlette import status

from main import templates

router = APIRouter(
    prefix="/miniapp",
    tags=["miniapp"]
)


@router.get("",
            summary="Получение главной страницы Мини Ап",
            status_code=status.HTTP_200_OK)
async def get_mini_app(request: Request):
    """
    Get запрос получения главной страницы.

    """

    return templates.TemplateResponse(
        request=request, name="miniapp/index.html", context={}
    )
