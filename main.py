from app import app  # noqa: F401

# Initialize driver bot
try:
    from driver_bot import init_driver_bot
    init_driver_bot(app)
except Exception as e:
    print(f"Warning: Driver bot initialization failed: {e}")
    print("Driver bot features will not be available")
