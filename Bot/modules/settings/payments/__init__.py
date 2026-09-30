from .cog import setup as setup_payments


def setup(bot):
    """Setup all payment-related cogs"""
    setup_payments(bot)


__all__ = ["setup"]
