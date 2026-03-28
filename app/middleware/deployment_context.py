"""
DeploymentContext middleware — attaches FeatureGate to every request.
Enterprise routes check request.state.feature_gate.org_entity_active
and return 404 (not 403) when inactive — the enterprise surface does
not exist in LInDE mode, it is not forbidden.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from services.feature_gate import get_feature_gate

CINDE_ONLY_PREFIXES = (
    "/api/v1/org",
    "/api/v1/idtfs",
    "/api/v1/portfolio",
    "/api/v1/audit",
    "/api/v1/convergence",
    # Legacy prefixes (v3.x routes)
    "/api/organizations",
    "/api/teams",
    "/api/orgs",
    "/api/sessions",  # convergence sessions
    "/api/portfolio-dashboard",
    "/api/discovery",
    "/api/formation",
)


class DeploymentContextMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self._gate = get_feature_gate()

    async def dispatch(self, request: Request, call_next):
        request.state.feature_gate = self._gate
        request.state.deployment_mode = self._gate.mode.value

        # Return 404 for enterprise routes in LINDE mode
        if not self._gate.org_entity_active:
            path = request.url.path
            if any(path.startswith(p) for p in CINDE_ONLY_PREFIXES):
                from starlette.responses import JSONResponse
                return JSONResponse(
                    {"detail": "Not found"},
                    status_code=404
                )
        return await call_next(request)
