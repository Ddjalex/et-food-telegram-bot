from app import app  # noqa: F401
import routes  # noqa: F401
import restaurant_routes  # noqa: F401
import kitchen_routes  # noqa: F401
from kitchen_availability_routes import kitchen_bp

# Register kitchen availability blueprint
app.register_blueprint(kitchen_bp)
