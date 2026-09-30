# Sessões em memória: {telegram_user_id: {step, product_id, campo_id, price, payment_id, coupon_data}}
_sessions: dict = {}

def get(user_id: int) -> dict:
    return _sessions.get(user_id, {})

def set(user_id: int, data: dict):
    _sessions[user_id] = data

def update(user_id: int, **kwargs):
    _sessions.setdefault(user_id, {}).update(kwargs)

def clear(user_id: int):
    _sessions.pop(user_id, None)
