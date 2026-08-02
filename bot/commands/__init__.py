"""
commands – Raccoglie tutti i router dei comandi in un unico router.
"""

from aiogram import Router

from commands.start import router as start_router
from commands.about import router as about_router
from commands.settings import router as settings_router
from commands.report import router as report_router
from commands.now import router as now_router
from commands.search import router as search_router
from commands.fav import router as fav_router
from commands.biblio import router as biblio_router
from commands.userinfo import router as userinfo_router
from commands.aula import router as aula_router
from commands.help import router as help_router


def get_main_router() -> Router:
    main = Router()
    main.include_router(start_router)
    main.include_router(about_router)
    main.include_router(settings_router)
    main.include_router(report_router)
    main.include_router(now_router)
    main.include_router(search_router)
    main.include_router(fav_router)
    main.include_router(biblio_router)
    main.include_router(userinfo_router)
    # aula_router: catch-all per il testo libero (ricerca per sigla)
    main.include_router(aula_router)
    # help_router per ultimo: contiene il fallback sui comandi non riconosciuti
    main.include_router(help_router)
    return main