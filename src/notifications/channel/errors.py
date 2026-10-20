"""Errors a channel adapter raises to the dispatcher."""


class ChannelUnavailableError(RuntimeError):
    """The channel provider cannot be reached at all (an outage, not a rejected send).

    The dispatcher lets this propagate instead of recording the notification as
    FAILED, so the notification stays DISPATCHING and the engine retries the message.
    Repeated failures trip the dispatcher subscription's circuit breaker.
    """
