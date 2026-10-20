"""Errors a channel adapter raises to the dispatcher."""


class ChannelUnavailableError(RuntimeError):
    """The channel provider cannot be reached at all, so nothing was sent.

    A send the provider received and rejected returns ``status: failed`` instead.
    The dispatcher lets this error propagate instead of recording the
    notification as FAILED. The notification stays DISPATCHING, the engine
    retries the message, and repeated failures open the dispatcher
    subscription's circuit breaker.
    """
