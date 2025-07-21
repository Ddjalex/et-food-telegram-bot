from app import app  # noqa: F401
import kitchen_food_routes  # noqa: F401

# Register payment workflow blueprint
from payment_workflow import payment_workflow
app.register_blueprint(payment_workflow)
import routes  # noqa: F401
import restaurant_routes  # noqa: F401
from kitchen_availability_routes import kitchen_bp

# Register kitchen availability blueprint
app.register_blueprint(kitchen_bp)
