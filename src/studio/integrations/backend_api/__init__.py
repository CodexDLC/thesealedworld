"""HTTP clients for the backend API, called by studio cabinet modules.

Each client targets the active source's `api_base` (see `request.state.source`,
populated by `SourceSelectorMiddleware`). On the local source this is the
in-network backend container; on the prod source this is the SSH-forwarded
prod backend endpoint.
"""
