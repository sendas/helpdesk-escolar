from fastapi import APIRouter
from app.api.v1 import auth, tickets, categories, users, admin, schools, settings, knowledge

router = APIRouter(prefix="/api/v1")
router.include_router(auth.router)
router.include_router(tickets.router)
router.include_router(categories.router)
router.include_router(users.router)
router.include_router(admin.router)
router.include_router(schools.router)
router.include_router(settings.router)
router.include_router(knowledge.router)
