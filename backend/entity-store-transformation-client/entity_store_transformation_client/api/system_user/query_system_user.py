from http import HTTPStatus
from typing import Any, cast

import httpx

from ... import errors
from ...client import AuthenticatedClient, Client
from ...models.query_request import QueryRequest
from ...models.system_user_query_response import SystemUserQueryResponse
from ...types import UNSET, Response, Unset


def _get_kwargs(
    *,
    body: QueryRequest,
    expansion_level: int | Unset = 2,
) -> dict[str, Any]:
    headers: dict[str, Any] = {}

    params: dict[str, Any] = {}

    params["expansionLevel"] = expansion_level

    params = {k: v for k, v in params.items() if v is not UNSET and v is not None}

    _kwargs: dict[str, Any] = {
        "method": "post",
        "url": "/EntityService/SystemUser/query",
        "params": params,
    }

    _kwargs["json"] = body.to_dict()

    headers["Content-Type"] = "application/json"

    _kwargs["headers"] = headers
    return _kwargs


def _parse_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Any | SystemUserQueryResponse | None:
    if response.status_code == 200:
        response_200 = SystemUserQueryResponse.from_dict(response.json())

        return response_200

    if response.status_code == 401:
        response_401 = cast(Any, None)
        return response_401

    if response.status_code == 403:
        response_403 = cast(Any, None)
        return response_403

    if client.raise_on_unexpected_status:
        raise errors.UnexpectedStatus(response.status_code, response.content)
    else:
        return None


def _build_response(
    *, client: AuthenticatedClient | Client, response: httpx.Response
) -> Response[Any | SystemUserQueryResponse]:
    return Response(
        status_code=HTTPStatus(response.status_code),
        content=response.content,
        headers=response.headers,
        parsed=_parse_response(client=client, response=response),
    )


def sync_detailed(
    *,
    client: AuthenticatedClient,
    body: QueryRequest,
    expansion_level: int | Unset = 2,
) -> Response[Any | SystemUserQueryResponse]:
    """Query SystemUser records.

    Args:
        expansion_level (int | Unset):  Default: 2.
        body (QueryRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | SystemUserQueryResponse]
    """

    kwargs = _get_kwargs(
        body=body,
        expansion_level=expansion_level,
    )

    response = client.get_httpx_client().request(
        **kwargs,
    )

    return _build_response(client=client, response=response)


def sync(
    *,
    client: AuthenticatedClient,
    body: QueryRequest,
    expansion_level: int | Unset = 2,
) -> Any | SystemUserQueryResponse | None:
    """Query SystemUser records.

    Args:
        expansion_level (int | Unset):  Default: 2.
        body (QueryRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | SystemUserQueryResponse
    """

    return sync_detailed(
        client=client,
        body=body,
        expansion_level=expansion_level,
    ).parsed


async def asyncio_detailed(
    *,
    client: AuthenticatedClient,
    body: QueryRequest,
    expansion_level: int | Unset = 2,
) -> Response[Any | SystemUserQueryResponse]:
    """Query SystemUser records.

    Args:
        expansion_level (int | Unset):  Default: 2.
        body (QueryRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Response[Any | SystemUserQueryResponse]
    """

    kwargs = _get_kwargs(
        body=body,
        expansion_level=expansion_level,
    )

    response = await client.get_async_httpx_client().request(**kwargs)

    return _build_response(client=client, response=response)


async def asyncio(
    *,
    client: AuthenticatedClient,
    body: QueryRequest,
    expansion_level: int | Unset = 2,
) -> Any | SystemUserQueryResponse | None:
    """Query SystemUser records.

    Args:
        expansion_level (int | Unset):  Default: 2.
        body (QueryRequest):

    Raises:
        errors.UnexpectedStatus: If the server returns an undocumented status code and Client.raise_on_unexpected_status is True.
        httpx.TimeoutException: If the request takes longer than Client.timeout.

    Returns:
        Any | SystemUserQueryResponse
    """

    return (
        await asyncio_detailed(
            client=client,
            body=body,
            expansion_level=expansion_level,
        )
    ).parsed
