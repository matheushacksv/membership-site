from ninja import NinjaAPI
from ninja_jwt.authentication import JWTAuth

from accounts.api import router as user_router
from courses.api import admin_router as courses_admin
from courses.api import catalog_router
from enrollments.api import router as enrollments_router
from integrations.api import router as integrations_router
from tickets.api import router as tickets_router

api = NinjaAPI(auth=JWTAuth())

api.add_router('/auth', user_router)
api.add_router('/catalog', catalog_router)
api.add_router('/admin', courses_admin)
api.add_router('/enrollments', enrollments_router)
api.add_router('/integrations', integrations_router)
api.add_router('/tickets', tickets_router)
