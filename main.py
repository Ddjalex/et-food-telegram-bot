from app import app  # noqa: F401

# Register enhanced payment verification blueprint
from enhanced_payment_verification import enhanced_payment
app.register_blueprint(enhanced_payment)

# Import route modules
import routes
import admin_routes
import restaurant_routes
import kitchen_food_routes  # noqa: F401
# import kitchen_routes  # noqa: F401  # Commented out to avoid route conflicts

# Register payment workflow blueprint
from payment_workflow import payment_workflow
app.register_blueprint(payment_workflow)
import routes  # noqa: F401
import restaurant_routes  # noqa: F401
from kitchen_availability_routes import kitchen_bp

# Register kitchen availability blueprint
app.register_blueprint(kitchen_bp)

# Initialize bot_minimal
from bot_minimal import init_bot
init_bot(app)
